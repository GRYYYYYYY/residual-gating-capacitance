"""Train one unified residual-gated network on masked-characterization episodes.

The optimisation target is the deployment objective itself -- normalised Huber
error of the *final* estimate -- not a surrogate risk.  Gradients reach the gate
through the corrective basis and reach the trunk through the residual head and
the gate head, which is what makes this a single trained network rather than a
selection post-process.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from .episodes import RATIOS, encode, stack
from .model import ResidualGateNet, inverse_softplus
from .workspace import (FAMILIES, ROOT, file_hash, input_hashes, new_run,
                        source_hashes, write_json)
from .workspace import archive_on_path

archive_on_path()

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.model import GroupDRO  # noqa: E402
from pdkcap.sampling import mask  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402


def load_scales(path):
    state = torch.load(path, map_location='cpu', weights_only=True)
    if 'scales' not in state:
        raise ValueError('checkpoint does not carry training scales')
    return state['scales']


def transfer_trunk(model, path, strict_shapes=True):
    """Initialise input/encoder/residual from a frozen residual checkpoint."""
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


#: Which parameter groups the stage-2 objective is allowed to move.
TRAIN_SCOPES = ('all', 'gate_head', 'gate')


def apply_scope(model, scope):
    """Freeze everything the scope excludes.

    ``gate``      only the gate head, its prior bias and the temperature move.
    ``gate_head`` additionally fine-tunes the residual head.
    ``all``       joint training of the whole network.
    """
    if scope not in TRAIN_SCOPES:
        raise ValueError(f'unknown training scope {scope}')
    trainable = {'gate', 'gate_head'}
    for name, parameter in model.named_parameters():
        if scope == 'all':
            parameter.requires_grad = True
        elif scope == 'gate_head':
            parameter.requires_grad = name.startswith(('gate.', 'gate_bias', 'log_temperature', 'residual.'))
        else:
            parameter.requires_grad = name.startswith(('gate.', 'gate_bias', 'log_temperature'))
        if not parameter.requires_grad and name.startswith('gate.') and scope not in trainable:
            raise ValueError('gate must always be trainable')
    return [name for name, parameter in model.named_parameters() if parameter.requires_grad]


def build_model(config, features_in, gate_in, experts, targets):
    model = ResidualGateNet(targets=targets, features_in=features_in, gate_in=gate_in,
                            experts=experts, width=config['width'], layers=config['layers'],
                            gate_hidden=config['gate_hidden'], dropout=config['dropout'],
                            anchor_logit_gap=config['anchor_logit_gap'],
                            agreement=config['agreement'])
    with torch.no_grad():
        model.log_temperature.fill_(inverse_softplus(config['temperature']))
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
        episodes.append((family_index, encoded, query, y))
    return episodes


def episode_loss(model, encoded, query, truth, huber_delta, span_weight):
    batch = stack([encoded])
    prediction = model(batch['features'], batch['anchor'], batch['gate'], batch['delta'],
                       batch['valid'], padding=batch['padding'], clamp_lower=batch['lower'],
                       clamp_upper=batch['upper'], inside=batch['inside'])
    scales = np.asarray(encoded['scales'], float)
    target = torch.as_tensor(truth[query] / scales, dtype=torch.float32)
    per_target = torch.nn.functional.huber_loss(prediction[0, query], target,
                                                delta=huber_delta, reduction='none')
    if span_weight:
        # Weight each target by how much of its own scale the query actually spans,
        # so a component that is identically zero cannot dominate the update.
        span = torch.as_tensor(np.maximum(np.ptp(truth[query] / scales, axis=0), 0.), dtype=torch.float32)
        weight = 1. + span
        return (per_target.mean(dim=0) * weight).sum() / weight.sum()
    return per_target.mean()


def train(config, output):
    torch.set_num_threads(config['torch_threads'])
    torch.manual_seed(config['seed'])
    rng = np.random.default_rng(config['seed'])
    tables = read_tables(config['data'])
    allowed = set(config['partitions'])
    if allowed != {'train'}:
        raise PermissionError('this runner fits on the training partition only')
    training = unique_tables([t for t in tables if t['partition'] == 'train' and len(t['coordinates']) >= 2])
    if not training:
        raise ValueError('no training tables')
    if any(t['partition'] != 'train' for t in training):
        raise PermissionError('non-training table reached the fitting pool')
    scales = load_scales(config['scales_from'])
    groups = {index: [t for t in training if t['family'] == family] for index, family in enumerate(FAMILIES)}
    if any(not pool for pool in groups.values()):
        raise ValueError('every family needs a training pool')

    probe = training[0]
    probe_y = np.asarray(probe['labels'], float)
    probe_observed, _ = mask(probe['coordinates'], 'mcar', .3, 11)
    first = encode(probe, probe_observed, probe_y[probe_observed], scales)
    experts = first['delta'].shape[0] + 2
    model = build_model(config, first['features'].shape[1], first['gate'].shape[1], experts, first['targets'])
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable:
        raise ValueError('nothing to train under this scope')
    optimizer = torch.optim.AdamW(trainable, lr=config['learning_rate'],
                                  weight_decay=config['weight_decay'])
    dro = GroupDRO(config['eta'])
    history = []
    started = time.perf_counter()
    for step in range(config['steps']):
        model.train()
        optimizer.zero_grad()
        losses = {}
        for family_index, encoded, query, truth in sample_episode(rng, groups, scales):
            losses[family_index] = episode_loss(model, encoded, query, truth,
                                                config['huber_delta'], config['span_weight'])
        loss = dro.loss(losses)
        if not torch.isfinite(loss):
            raise ValueError('nonfinite training loss')
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), config['gradient_clip'])
        optimizer.step()
        if step % 100 == 0 or step == config['steps'] - 1:
            row = dict(step=step + 1, loss=float(loss.detach()), dro_weights=dro.weights.tolist(),
                       seconds=time.perf_counter() - started)
            history.append(row)
            print(json.dumps(row), flush=True)
    payload = dict(state_dict=model.state_dict(), version=ResidualGateNet.version,
                   targets=first['targets'], features_in=first['features'].shape[1],
                   gate_in=first['gate'].shape[1], experts=experts, scales=scales,
                   width=config['width'], layers=config['layers'], gate_hidden=config['gate_hidden'],
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
    parser.add_argument('--steps', type=int, default=2000)
    parser.add_argument('--eta', type=float, default=0.)
    parser.add_argument('--learning-rate', type=float, default=.002)
    parser.add_argument('--weight-decay', type=float, default=1e-4)
    parser.add_argument('--anchor-logit-gap', type=float, default=8.)
    parser.add_argument('--gate-hidden', type=int, default=32)
    parser.add_argument('--width', type=int, default=64)
    parser.add_argument('--layers', type=int, default=2)
    parser.add_argument('--dropout', type=float, default=.1)
    parser.add_argument('--huber-delta', type=float, default=1.)
    parser.add_argument('--span-weight', action='store_true')
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
                  gate_hidden=args.gate_hidden, width=args.width, layers=args.layers,
                  dropout=args.dropout, huber_delta=args.huber_delta, span_weight=args.span_weight,
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
