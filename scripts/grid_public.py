"""Validation-only configuration grid for the unified network (public domain).

Every configuration is trained on the public training partition and scored on
the frozen public validation cohort only.  The test cohort is never touched
here; the winning configuration is frozen afterwards and scored once.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, mask_macro_nrmse  # noqa: E402
from unified.workspace import ARCHIVE, ROOT as WORKSPACE  # noqa: E402

DATA = ARCHIVE / 'runs/public_inventory_v1/tables.jsonl'
VAL = ARCHIVE / 'runs/round3_validation_inputs_v1/public_val.jsonl'
INIT = ARCHIVE / 'runs/public_study_v1/residual_eta0.01_seed{seed}/checkpoint.pt'
PYTHON = str(ARCHIVE / 'local/venv/bin/python')

CONFIGS = {
    'g1': dict(scope='all', temperature=1.0, agreement=True, steps=1000, lr=5e-4),
    'g2': dict(scope='all', temperature=0.25, agreement=True, steps=1000, lr=5e-4),
    'g3': dict(scope='all', temperature=1.0, agreement=False, steps=1000, lr=5e-4),
    'g4': dict(scope='all', temperature=0.25, agreement=True, steps=2000, lr=2e-4),
    'g5': dict(scope='gate', temperature=0.25, agreement=True, steps=2000, lr=2e-3),
    'g6': dict(scope='all', temperature=0.25, agreement=True, steps=1000, lr=5e-4, dropout=.0),
    'g7': dict(scope='all', temperature=0.25, agreement=True, steps=3000, lr=1e-4),
    'g8': dict(scope='all', temperature=0.25, agreement=True, steps=2000, lr=5e-4),
    'g9': dict(scope='all', temperature=0.25, agreement=True, steps=2000, lr=2e-4, dropout=.0),
    'g10': dict(scope='all', temperature=0.25, agreement=True, steps=3000, lr=2e-4, dropout=.0),
    'g11': dict(scope='all', temperature=0.25, agreement=True, steps=4000, lr=2e-4, dropout=.0),
    'g12': dict(scope='all', temperature=0.25, agreement=True, steps=2000, lr=1e-3, dropout=.0),
    'g13': dict(scope='all', temperature=0.25, agreement=True, steps=6000, lr=2e-4, dropout=.0),
    'g14': dict(scope='all', temperature=0.25, agreement=True, steps=6000, lr=5e-4, dropout=.0),
    'g15': dict(scope='all', temperature=0.25, agreement=True, steps=12000, lr=2e-4, dropout=.0),
    'g16': dict(scope='all', temperature=0.25, agreement=True, steps=24000, lr=2e-4, dropout=.0),
}


def env():
    import os
    values = dict(os.environ)
    values['PYTHONDONTWRITEBYTECODE'] = '1'
    values['OMP_NUM_THREADS'] = '1'
    return values


def run(command, log):
    with open(log, 'a') as handle:
        handle.write(' '.join(str(part) for part in command) + '\n')
        handle.flush()
        subprocess.run([str(part) for part in command], stdout=handle, stderr=subprocess.STDOUT,
                       check=True, env=env())


def train_all(tag, config, seeds):
    processes = []
    for seed in seeds:
        output = f'{tag}_s{seed}'
        if (WORKSPACE / 'runs' / output).exists():
            continue
        command = [PYTHON, '-m', 'unified.train', '--data', DATA,
                   '--output', output, '--scales-from', str(INIT).format(seed=seed),
                   '--init-from', str(INIT).format(seed=seed), '--train-scope', config['scope'],
                   '--steps', config['steps'], '--seed', seed, '--learning-rate', config['lr'],
                   '--temperature', config['temperature'], '--torch-threads', 1]
        if not config['agreement']:
            command.append('--no-agreement')
        if 'dropout' in config:
            command += ['--dropout', config['dropout']]
        processes.append(subprocess.Popen([str(part) for part in command],
                                          stdout=open(WORKSPACE / f'logs/train_{output}.log', 'w'),
                                          stderr=subprocess.STDOUT, env=env()))
    for process in processes:
        if process.wait() != 0:
            raise RuntimeError('training failed')


def score(tag, seeds):
    output = f'val_{tag}'
    if (WORKSPACE / 'runs' / output).exists():
        return
    checkpoints = [f'runs/{tag}_s{seed}/checkpoint.pt' for seed in seeds]
    run([PYTHON, '-m', 'unified.score', '--cohort', VAL, '--checkpoint', *checkpoints,
         '--output', output, '--method', f'sace_r_{tag}', '--workers', 40],
        WORKSPACE / f'logs/score_{output}.log')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--configs', nargs='+', default=sorted(CONFIGS))
    parser.add_argument('--seeds', nargs='+', type=int, default=[0, 1, 2])
    args = parser.parse_args()
    accumulator = {}
    for tag in args.configs:
        started = time.perf_counter()
        config = CONFIGS[tag]
        print(f'--- {tag} {config}', flush=True)
        train_all(tag, config, args.seeds)
        score(tag, args.seeds)
        add_records(accumulator, WORKSPACE / f'runs/val_{tag}/records.jsonl.gz')
        row = [mask_macro_nrmse(accumulator, f'sace_r_{tag}', protocol, .3)
               for protocol in ('mcar', 'block', 'extrapolation')]
        print(f'{tag:6s} ' + ' '.join(f'{value:.4f}' if value else '  --  ' for value in row)
              + f'   [{time.perf_counter() - started:.0f}s]', flush=True)
    payload = {tag: [mask_macro_nrmse(accumulator, f'sace_r_{tag}', protocol, .3)
                     for protocol in ('mcar', 'block', 'extrapolation')] for tag in args.configs}
    path = WORKSPACE / 'runs' / 'grid_public_v1'
    if not path.exists():
        path.mkdir(parents=True)
        (path / 'grid.json').write_text(json.dumps(dict(configs=CONFIGS, scores=payload,
                                                        seeds=args.seeds), indent=2) + '\n')
    print(json.dumps(payload, indent=1))


if __name__ == '__main__':
    main()
