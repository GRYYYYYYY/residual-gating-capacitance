"""Stage-1 (residual warm-start) trainer, run inside this workspace.

`pdkcap/train.py` is the frozen stage-1 trainer, but running it in formal mode
takes a slot in the frozen archive's compute ledger, and this workspace is
required to leave that archive byte-identical.  The training loop below is that
file's `execute()` verbatim -- same model, same optimizer, same GroupDRO
schedule, same episode sampling, same 2000 steps -- with the artifacts written
under this workspace's `runs/` and no ledger entry.

Everything else is imported read-only from the frozen package, so the algorithm
cannot drift: only the output location and the accounting differ.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pdkcap.common import FAMILIES, read_tables, write_json, file_hash  # noqa: E402
from pdkcap.sampling import mask  # noqa: E402
from pdkcap.model import ConditionalModel, GroupDRO, encode, fit_scales  # noqa: E402
from pdkcap.train import unique_tables, validate  # noqa: E402
from unified.workspace import new_run  # noqa: E402

FROZEN_SOURCE = 'pdkcap/train.py::execute'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--steps', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--variant', choices=['direct', 'residual'], default='residual')
    parser.add_argument('--eta', type=float, default=0.)
    args = parser.parse_args()

    torch.set_num_threads(1)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    tables = read_tables(args.data)
    training = unique_tables([t for t in tables
                              if t['partition'] == 'train' and len(t['coordinates']) >= 2])
    validation = unique_tables([t for t in tables
                                if t['partition'] == 'val' and len(t['coordinates']) >= 2])
    scales = fit_scales(training)
    targets = len(training[0]['target_names'])
    model = ConditionalModel(args.variant, targets=targets)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    dro = GroupDRO(args.eta)
    groups = {g: [t for t in training if t['family'] == family]
              for g, family in enumerate(FAMILIES)}

    output = new_run(args.output)
    write_json(output / 'config.json', dict(
        arguments={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        data_sha256=file_hash(args.data), scales=scales,
        training_tables=len(training), validation_tables=len(validation),
        label_access='training + validation only; no test evaluation',
        endpoint='last step', reimplements=FROZEN_SOURCE,
        divergence_from_frozen='output location and compute accounting only'))

    started = time.perf_counter()
    history = []
    for step in range(args.steps):
        model.train()
        optimizer.zero_grad()
        losses = {}
        for g, ts in groups.items():
            processes = sorted({t['process_id'] for t in ts})
            process = processes[int(rng.integers(len(processes)))]
            pool = [t for t in ts if t['process_id'] == process]
            t = pool[int(rng.integers(len(pool)))]
            protocol = ('mcar', 'block', 'extrapolation')[int(rng.integers(3))]
            ratio = (.1, .3, .5, .7)[int(rng.integers(4))]
            o, q = mask(t['coordinates'], protocol, ratio, int(rng.integers(2 ** 31)))
            y = np.asarray(t['labels'])
            f, b, s = encode(t, o, y[o], scales)
            pred = model(f[None], b[None])[0, q]
            target = torch.tensor(y[q] / s, dtype=torch.float32)
            losses[g] = torch.nn.functional.huber_loss(pred, target, delta=1.)
        loss = dro.loss(losses)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        optimizer.step()
        if step % 20 == 0 or step == args.steps - 1:
            history.append(dict(step=step + 1, loss=float(loss.detach()),
                                group_weights=dro.weights.tolist()))

    elapsed = time.perf_counter() - started
    validation_result = validate(model, validation, scales)
    torch.save(dict(state_dict=model.state_dict(), variant=args.variant,
                    targets=targets, scales=scales), output / 'checkpoint.pt')
    write_json(output / 'result.json', dict(
        status='completed', purpose='formal', steps=args.steps, wall_seconds=elapsed,
        steps_per_second=args.steps / elapsed, validation_nrmse=validation_result,
        history=history, checkpoint_sha256=file_hash(output / 'checkpoint.pt'),
        reimplements=FROZEN_SOURCE))
    print(json.dumps(dict(output=str(output), seconds=elapsed,
                          validation=validation_result)))


if __name__ == '__main__':
    main()
