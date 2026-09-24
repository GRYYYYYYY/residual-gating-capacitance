from __future__ import annotations

import argparse
import json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="openrcbench")
    parser.add_argument("--sources", default="configs/sources.json")
    parser.add_argument("--processes", default="configs/processes.json")
    commands = parser.add_subparsers(dest="command", required=True)

    download = commands.add_parser("download")
    download.add_argument("--raw-dir", default="data/raw")

    build = commands.add_parser("build")
    build.add_argument("--raw-dir", default="data/raw")
    build.add_argument("--output", default="data/processed/dataset.jsonl")

    split = commands.add_parser("split")
    split.add_argument("--dataset", required=True)
    split.add_argument("--output", required=True)
    split.add_argument("--seed", type=int, default=2027)

    baseline = commands.add_parser("baseline")
    baseline.add_argument("--dataset", required=True)
    baseline.add_argument("--split", required=True)
    baseline.add_argument("--output", required=True)
    baseline.add_argument(
        "--method", choices=("mean", "nearest", "linear", "rbf"), default="linear"
    )
    baseline.add_argument("--protocol", choices=("mcar", "block", "extrapolation"), default="mcar")
    baseline.add_argument("--ratio", type=float, default=0.3)
    baseline.add_argument("--seed", type=int, default=0)
    baseline.add_argument("--fold")

    train = commands.add_parser("train")
    train.add_argument("--dataset", required=True)
    train.add_argument("--split", required=True)
    train.add_argument("--output", required=True)
    train.add_argument("--fold")
    train.add_argument("--seed", type=int, default=0)
    train.add_argument("--epochs", type=int, default=100)
    train.add_argument("--batch-size", type=int, default=16)
    train.add_argument("--mask-ratio", type=float, default=0.3)
    train.add_argument("--lr", type=float, default=2e-4)
    train.add_argument("--physics-lambda", type=float, default=0.05)
    train.add_argument("--monotonic-weight", type=float, default=1.0)
    train.add_argument("--symmetry-weight", type=float, default=1.0)
    train.add_argument("--smoothness-weight", type=float, default=0.1)
    train.add_argument("--no-observed-context", action="store_true")
    train.add_argument("--no-process-descriptors", action="store_true")
    train.add_argument("--all-row-training", action="store_true")

    export = commands.add_parser("export-openrcx")
    export.add_argument("--original", required=True)
    export.add_argument("--dataset", required=True)
    export.add_argument("--predictions", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--source-id", required=True)

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--dataset", required=True)
    evaluate.add_argument("--split", required=True)
    evaluate.add_argument("--checkpoint", required=True)
    evaluate.add_argument("--output", required=True)
    evaluate.add_argument("--fold")
    evaluate.add_argument("--partition", choices=("test", "val"), default="test")
    evaluate.add_argument("--protocol", choices=("mcar", "block", "extrapolation"), default="mcar")
    evaluate.add_argument("--ratio", type=float, default=0.3)
    evaluate.add_argument("--seed", type=int, default=0)

    summarize = commands.add_parser("summarize")
    summarize.add_argument("--input", required=True)
    summarize.add_argument("--output-prefix", required=True)

    spef = commands.add_parser("compare-spef")
    spef.add_argument("--golden", required=True)
    spef.add_argument("--candidate", required=True)
    spef.add_argument("--output", required=True)

    tabular = commands.add_parser("tabular-baseline")
    tabular.add_argument("--dataset", required=True)
    tabular.add_argument("--split", required=True)
    tabular.add_argument("--output", required=True)
    tabular.add_argument("--method", choices=("xgboost", "mlp"), required=True)
    tabular.add_argument("--fold")
    tabular.add_argument("--protocol", choices=("mcar", "block", "extrapolation"), default="mcar")
    tabular.add_argument("--ratio", type=float, default=0.3)
    tabular.add_argument("--seed", type=int, default=0)

    args = parser.parse_args(argv)
    if args.command == "download":
        from .sources import download_sources

        result = {"downloaded": len(download_sources(args.sources, args.raw_dir))}
    elif args.command == "build":
        from .dataset import build_dataset

        result = build_dataset(args.sources, args.processes, args.raw_dir, args.output)
    elif args.command == "split":
        from .splits import create_splits

        result = create_splits(args.dataset, args.output, args.seed)
    elif args.command == "baseline":
        from .baselines import evaluate_baseline

        result = evaluate_baseline(
            args.dataset,
            args.split,
            args.output,
            method=args.method,
            protocol=args.protocol,
            ratio=args.ratio,
            seed=args.seed,
            fold=args.fold,
        )
        result = {
            key: value
            for key, value in result.items()
            if key not in {"records", "table_physical_records"}
        }
    elif args.command == "train":
        from .training import train_model

        result = train_model(
            args.dataset,
            args.split,
            args.output,
            fold=args.fold,
            seed=args.seed,
            epochs=args.epochs,
            batch_size=args.batch_size,
            mask_ratio=args.mask_ratio,
            learning_rate=args.lr,
            physics_lambda=args.physics_lambda,
            monotonic_weight=args.monotonic_weight,
            symmetry_weight=args.symmetry_weight,
            smoothness_weight=args.smoothness_weight,
            use_observed_context=not args.no_observed_context,
            use_process_descriptors=not args.no_process_descriptors,
            all_row_training=args.all_row_training,
        )
    elif args.command == "export-openrcx":
        from .export import export_openrcx

        result = export_openrcx(
            args.original,
            args.dataset,
            args.predictions,
            args.output,
            source_id=args.source_id,
        )
    elif args.command == "evaluate":
        from .training import evaluate_model

        result = evaluate_model(
            args.dataset,
            args.split,
            args.checkpoint,
            args.output,
            partition=args.partition,
            fold=args.fold,
            protocol=args.protocol,
            ratio=args.ratio,
            seed=args.seed,
        )
    elif args.command == "summarize":
        from .report import summarize_runs

        result = summarize_runs(args.input, args.output_prefix)
    elif args.command == "compare-spef":
        from .spef import compare_spef

        result = compare_spef(args.golden, args.candidate, args.output)
    else:
        from .tabular import evaluate_tabular_baseline

        result = evaluate_tabular_baseline(
            args.dataset,
            args.split,
            args.output,
            method=args.method,
            protocol=args.protocol,
            ratio=args.ratio,
            seed=args.seed,
            fold=args.fold,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
