"""Fit the residual-gating estimator on masked-characterization episodes.

The objective is the evaluation metric itself.  For every deployment condition
-- a (process family, missingness protocol, interpolation regime) cell -- the
loss is the macro over capacitance components of the normalized mean squared
error of the *final* estimate, pooled over the queries of that cell:

    L_g = mean_k  ( sum_q (y_hat - y)^2 / sum_q y^2 )

and the cells are combined by a group-DRO weight that puts the worst-performing
deployment condition first.  Two things follow that a pointwise mean squared
error does not give.  A cell whose relative error is small is not drowned out by
a cell whose relative error is large, so no regime is sacrificed to the
average; and the quantity being minimized per cell is the quantity being
reported per cell.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from .episodes import RATIOS, encode, stack
from .estimator import CHANNELS, ResidualGatingEstimator
from .workspace import (FAMILIES, file_hash, input_hashes, new_run, source_hashes,
                        write_json)
from .workspace import archive_on_path

archive_on_path()

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.sampling import mask  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

PROTOCOLS = ('mcar', 'block', 'extrapolation', 'width')
REGIMES = ('inside', 'outside')
#: Deployment conditions the DRO balances over: family x protocol x regime.
CONDITIONS = len(FAMILIES) * len(PROTOCOLS) * len(REGIMES)


def condition_index(family, protocol, regime):
    return ((int(family) * len(PROTOCOLS) + PROTOCOLS.index(protocol)) * len(REGIMES)
            + REGIMES.index(regime))


class ConditionDRO:
    """Exponentiated-gradient weights over deployment conditions.

    Unlike a fixed-size group-DRO it tolerates conditions that the current
    episode does not realize (a table with a single width has no width fold):
    absent conditions keep their weight and are excluded from the update and
    from the renormalization, so the batch does not have to be balanced by
    construction.
    """

    def __init__(self, eta=0., groups=CONDITIONS):
        if eta < 0:
            raise ValueError('eta must be non-negative')
        self.eta = float(eta)
        self.groups = int(groups)
        self.weights = np.ones(self.groups) / self.groups

    def loss(self, losses):
        if not losses:
            raise ValueError('no deployment condition realized in this episode')
        present = sorted(losses)
        detached = np.array([float(losses[index].detach()) for index in present])
        logits = np.log(np.maximum(self.weights[present], 1e-30)) + self.eta * detached
        logits -= logits.max()
        updated = np.exp(logits)
        updated /= updated.sum()
        self.weights[present] = updated
        return sum(float(self.weights[index]) * losses[index] for index in present)


def load_scales(path):
    state = torch.load(path, map_location='cpu', weights_only=True)
    if 'scales' not in state:
        raise ValueError('checkpoint does not carry training scales')
    return state['scales']


def transfer_trunk(model, path, strict_shapes=True):
    """Initialise input/encoder/residual from a pre-trained residual checkpoint."""
    state = torch.load(path, map_location='cpu', weights_only=True)['state_dict']
    renamed = {}
    for key, value in state.items():
        target = None
        if key.startswith('input.') or key.startswith('encoder.'):
            target = key
        elif key.startswith('output.'):
            target = 'residual.' + key.split('.', 1)[1]
        if target is None:
            continue
        renamed[target] = value
    own = model.state_dict()
    for key, value in renamed.items():
        if key in own and own[key].shape == value.shape:
            own[key] = value
        elif strict_shapes:
            raise ValueError(f'trunk transfer mismatch on {key}')
    model.load_state_dict(own)
    return sorted(renamed)


TRAIN_SCOPES = ('all', 'gate_head', 'gate')


def apply_scope(model, scope):
    """Freeze everything the scope excludes.

    ``gate``      only the gate (query, key, prior, temperature) moves.
    ``gate_head`` additionally fine-tunes the residual head.
    ``all``       joint training of the whole network.
    """
    if scope not in TRAIN_SCOPES:
        raise ValueError(f'unknown training scope {scope}')
    gate_prefixes = ('query.', 'key', 'gate_bias', 'log_temperature', 'temperature_head.')
    for name, parameter in model.named_parameters():
        if scope == 'all':
            parameter.requires_grad = True
        elif scope == 'gate_head':
            parameter.requires_grad = name.startswith((*gate_prefixes, 'residual.'))
        else:
            parameter.requires_grad = name.startswith(gate_prefixes)
        if scope != 'all' and name.startswith(gate_prefixes) and not parameter.requires_grad:
            raise ValueError('the gate must always be trainable')
    return [name for name, parameter in model.named_parameters() if parameter.requires_grad]


def build_model(config, features_in, gate_in, experts, targets):
    model = ResidualGatingEstimator(
        targets=targets, features_in=features_in, gate_in=gate_in, experts=experts,
        width=config['width'], layers=config['layers'], gate_hidden=config['gate_hidden'],
        head_dim=config['head_dim'], dropout=config['dropout'],
        anchor_logit_gap=config['anchor_logit_gap'], agreement=config['agreement'],
        gate_init=config['gate_init'], temperature=config['temperature'])
    if config.get('init_from'):
        transfer_trunk(model, config['init_from'])
    apply_scope(model, config['train_scope'])
    return model


def sample_episode(rng, groups, scales):
    """One balanced family episode: process, table, protocol, ratio, mask seed."""
    episodes = []
    for family_index, pool in groups.items():
        processes = sorted({t['process_id'] for t in pool})
        process = processes[int(rng.integers(len(processes)))]
        candidates = [t for t in pool if t['process_id'] == process]
        table = candidates[int(rng.integers(len(candidates)))]
        protocols = ['mcar', 'block', 'extrapolation'] + (['width'] if table['width_count'] > 1 else [])
        protocol = protocols[int(rng.integers(len(protocols)))]
        ratio = RATIOS[int(rng.integers(len(RATIOS)))]
        observed, query = mask(table['coordinates'], protocol, ratio, int(rng.integers(2 ** 31)))
        y = np.asarray(table['labels'], float)
        encoded = encode(table, observed, y[observed], scales)
        episodes.append((family_index, protocol, encoded, query, y))
    return episodes


def episode_losses(model, encoded, query, truth, protocol, family_index, metric, huber_delta):
    """One loss per realized (family, protocol, regime) deployment condition.

    ``metric='nrmse'`` scores each condition by the reported quantity -- the
    macro over components of the normalized squared error pooled over the
    queries of that condition.  ``metric='mse'`` is the pointwise mean squared
    error of the episode, i.e. the objective that ignores which regime and how
    many observations a query has; it is kept for the objective ablation.
    """
    batch = stack([encoded])
    prediction = model(batch['features'], batch['anchor'], batch['gate'], batch['delta'],
                       batch['valid'], padding=batch['padding'], clamp_lower=batch['lower'],
                       clamp_upper=batch['upper'], inside=batch['inside'])
    scales = np.asarray(encoded['scales'], float)
    target = torch.as_tensor(truth[query] / scales, dtype=torch.float32)
    estimate = prediction[0, query]
    if metric == 'mse':
        return {condition_index(family_index, protocol, 'inside'):
                (estimate - target).pow(2).mean()}
    if metric != 'nrmse':
        raise ValueError(f'unknown metric {metric}')
    inside = np.asarray(encoded['inside'])[query]
    losses = {}
    for regime in REGIMES:
        take = torch.as_tensor(inside if regime == 'inside' else ~inside)
        if not bool(take.any()):
            continue
        error = estimate[take] - target[take]
        energy = (target[take] ** 2).sum(dim=0)
        live = energy > 1e-12
        if not bool(live.any()):
            continue
        losses[condition_index(family_index, protocol, regime)] = \
            ((error ** 2).sum(dim=0)[live] / energy[live]).mean()
    return losses


def train(config, output):
    torch.set_num_threads(config['torch_threads'])
    torch.manual_seed(config['seed'])
    rng = np.random.default_rng(config['seed'])
    tables = read_tables(config['data'])
    if set(config['partitions']) != {'train'}:
        raise PermissionError('this runner fits on the training partition only')
    training = unique_tables([t for t in tables
                              if t['partition'] == 'train' and len(t['coordinates']) >= 2])
    if not training:
        raise ValueError('no training tables')
    if any(t['partition'] != 'train' for t in training):
        raise PermissionError('non-training table reached the fitting pool')
    scales = load_scales(config['scales_from'])
    groups = {index: [t for t in training if t['family'] == family]
              for index, family in enumerate(FAMILIES)}
    if any(not pool for pool in groups.values()):
        raise ValueError('every family needs a training pool')

    probe = training[0]
    probe_observed, _ = mask(probe['coordinates'], 'mcar', .3, 11)
    probe_y = np.asarray(probe['labels'], float)
    first = encode(probe, probe_observed, probe_y[probe_observed], scales)
    experts = first['delta'].shape[0] + 2
    model = build_model(config, first['features'].shape[1], first['gate'].shape[1],
                        experts, first['targets'])
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable:
        raise ValueError('nothing to train under this scope')
    optimizer = torch.optim.AdamW(trainable, lr=config['learning_rate'],
                                  weight_decay=config['weight_decay'])
    dro = ConditionDRO(config['eta'])
    history = []
    started = time.perf_counter()
    for step in range(config['steps']):
        model.train()
        optimizer.zero_grad()
        losses = {}
        for family_index, protocol, encoded, query, truth in sample_episode(rng, groups, scales):
            losses.update(episode_losses(model, encoded, query, truth, protocol, family_index,
                                         config['metric'], config['huber_delta']))
        loss = dro.loss(losses)
        if not torch.isfinite(loss):
            raise ValueError('nonfinite training loss')
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), config['gradient_clip'])
        optimizer.step()
        if step % 100 == 0 or step == config['steps'] - 1:
            row = dict(step=step + 1, loss=float(loss.detach()), seconds=time.perf_counter() - started)
            if step % 1000 == 0 or step == config['steps'] - 1:
                row['dro_weights'] = {str(index): float(dro.weights[index])
                                      for index in np.argsort(-dro.weights)[:6]}
            history.append(row)
            print(json.dumps(row), flush=True)
    payload = dict(state_dict=model.state_dict(), version=ResidualGatingEstimator.version,
                   targets=first['targets'], features_in=first['features'].shape[1],
                   gate_in=first['gate'].shape[1], experts=experts, scales=scales,
                   width=config['width'], layers=config['layers'],
                   gate_hidden=config['gate_hidden'], head_dim=config['head_dim'],
                   channels=CHANNELS,
                   anchor_logit_gap=config['anchor_logit_gap'], agreement=config['agreement'],
                   temperature_init=config['temperature'], train_scope=config['train_scope'],
                   gate_basis=[*first['basis_names'], 'neural', 'neural_clamp'])
    torch.save(payload, output / 'checkpoint.pt')
    write_json(output / 'COMPLETED.json', dict(
        status='trained; configuration selection pending', steps=config['steps'],
        seed=config['seed'], wall_seconds=time.perf_counter() - started, history=history,
        checkpoint_sha256=file_hash(output / 'checkpoint.pt'), training_tables=len(training)))
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--scales-from', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--steps', type=int, default=3000)
    parser.add_argument('--eta', type=float, default=.5)
    parser.add_argument('--learning-rate', type=float, default=.0002)
    parser.add_argument('--weight-decay', type=float, default=1e-4)
    parser.add_argument('--anchor-logit-gap', type=float, default=2.)
    parser.add_argument('--gate-hidden', type=int, default=32)
    parser.add_argument('--head-dim', type=int, default=16)
    parser.add_argument('--width', type=int, default=64)
    parser.add_argument('--layers', type=int, default=2)
    parser.add_argument('--dropout', type=float, default=.1)
    parser.add_argument('--gate-init', type=float, default=.01)
    parser.add_argument('--metric', choices=('nrmse', 'mse'), default='nrmse')
    parser.add_argument('--huber-delta', type=float, default=1.)
    parser.add_argument('--gradient-clip', type=float, default=1.)
    parser.add_argument('--torch-threads', type=int, default=1)
    parser.add_argument('--partitions', nargs='+', default=['train'])
    parser.add_argument('--init-from', type=Path, default=None)
    parser.add_argument('--train-scope', choices=TRAIN_SCOPES, default='all')
    parser.add_argument('--temperature', type=float, default=1.)
    parser.add_argument('--no-agreement', dest='agreement', action='store_false')
    parser.add_argument('--tag', type=str, default='')
    args = parser.parse_args()

    output = new_run(args.output)
    config = dict(seed=args.seed, steps=args.steps, eta=args.eta, learning_rate=args.learning_rate,
                  weight_decay=args.weight_decay, anchor_logit_gap=args.anchor_logit_gap,
                  gate_hidden=args.gate_hidden, head_dim=args.head_dim, width=args.width,
                  layers=args.layers, dropout=args.dropout, gate_init=args.gate_init,
                  metric=args.metric, huber_delta=args.huber_delta,
                  temperature=args.temperature, agreement=args.agreement,
                  gradient_clip=args.gradient_clip, torch_threads=args.torch_threads,
                  partitions=args.partitions, data=str(args.data),
                  scales_from=str(args.scales_from),
                  init_from=str(args.init_from) if args.init_from else None,
                  train_scope=args.train_scope, tag=args.tag)
    write_json(output / 'FROZEN.json', dict(
        config=config, inputs=input_hashes(), sources=source_hashes(),
        data_sha256=file_hash(args.data), scales_sha256=file_hash(args.scales_from),
        label_access='train partition only; no validation, test or confirmation labels'))
    train(config, output)


if __name__ == '__main__':
    main()
