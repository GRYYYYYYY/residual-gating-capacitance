from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from .io import read_jsonl


def _score(seed: int, value: str) -> float:
    digest = hashlib.sha256(f"{seed}:{value}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _assert_disjoint(split: dict[str, list[str]]) -> None:
    names = list(split)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            overlap = set(split[left]) & set(split[right])
            if overlap:
                raise ValueError(f"Split leakage between {left}/{right}: {len(overlap)} tables")


def _content_key(table) -> str:
    """Hash all predictive fields so exact duplicate tables stay in one partition."""

    value = {
        "process_id": table.process_id,
        "corner_id": table.corner_id,
        "family": table.family,
        "metal": table.metal,
        "context_below": table.context_below,
        "context_above": table.context_above,
        "width": table.width,
        "rows": table.rows,
    }
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _grouped_partition(tables: list, seed: int, ratios: tuple[float, ...]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for table in tables:
        groups[_content_key(table)].append(table.table_id)
    if len(groups) < len(ratios):
        raise ValueError(
            f"Need at least {len(ratios)} distinct content groups, found {len(groups)}"
        )
    ordered = sorted(groups.items(), key=lambda item: _score(seed, item[0]))
    targets = [ratio * len(tables) for ratio in ratios]
    partitions: list[list[str]] = [[] for _ in ratios]
    for _key, ids in ordered:
        # Put the next complete duplicate group into the most under-filled
        # partition relative to its target size.
        choice = min(
            range(len(ratios)),
            key=lambda index: (len(partitions[index]) / max(targets[index], 1e-12), index),
        )
        partitions[choice].extend(sorted(ids))
    return partitions


def create_splits(dataset: str | Path, output_dir: str | Path, seed: int = 2027) -> dict:
    tables = list(read_jsonl(dataset))
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    in_domain = {"train": [], "val": [], "test": []}
    by_process: dict[str, list] = defaultdict(list)
    for table in tables:
        by_process[table.process_id].append(table)
    for process_id, process_tables in sorted(by_process.items()):
        train_ids, val_ids, test_ids = _grouped_partition(
            process_tables, seed, (0.7, 0.1, 0.2)
        )
        in_domain["train"].extend(train_ids)
        in_domain["val"].extend(val_ids)
        in_domain["test"].extend(test_ids)
    _assert_disjoint(in_domain)

    processes = sorted(by_process)
    lopo = {}
    source_partitions = {}
    for held_out in processes:
        source = [t for t in tables if t.process_id != held_out]
        target = [t for t in tables if t.process_id == held_out]
        target_ids = sorted((t.table_id for t in target), key=lambda x: _score(seed, x))
        source_train, source_val = _grouped_partition(source, seed, (0.9, 0.1))
        fold = {
            "train": source_train,
            "val": source_val,
            "test": target_ids,
        }
        _assert_disjoint(fold)
        lopo[held_out] = fold
        source_partitions[held_out] = (fold["train"], fold["val"], target_ids)

    few_shot = {}
    few_shot_ratios = (0.01, 0.05, 0.10)
    for held_out in processes:
        source_train, source_val, target_ids = source_partitions[held_out]
        # A single stable target ordering makes the 1%, 5%, and 10% supports
        # nested, which removes sampling noise from adaptation-size curves.
        target_by_id = {table.table_id: table for table in tables if table.process_id == held_out}
        target_groups: dict[str, list[str]] = defaultdict(list)
        for table_id in target_ids:
            target_groups[_content_key(target_by_id[table_id])].append(table_id)
        target_group_order = sorted(
            target_groups, key=lambda key: _score(seed + 1, key)
        )
        for ratio in few_shot_ratios:
            desired = min(len(target_ids) - 1, max(1, round(ratio * len(target_ids))))
            support_groups = []
            support_count = 0
            for key in target_group_order:
                if support_count >= desired:
                    break
                support_groups.append(key)
                support_count += len(target_groups[key])
            support = sorted(
                table_id for key in support_groups for table_id in target_groups[key]
            )
            support_set = set(support)
            fold_name = f"{held_out}_{int(ratio * 100)}pct"
            fold = {
                "train": list(source_train) + support,
                "val": list(source_val),
                "test": sorted(set(target_ids) - support_set),
            }
            _assert_disjoint(fold)
            few_shot[fold_name] = fold

    gf_tables = [t for t in tables if t.process_id == "gf180"]
    corner_folds = {}
    for corner in sorted({t.corner_id for t in gf_tables}):
        test = [t.table_id for t in gf_tables if t.corner_id == corner]
        pool = [t for t in gf_tables if t.corner_id != corner]
        pool_train, pool_val = _grouped_partition(pool, seed, (0.9, 0.1))
        fold = {"train": pool_train, "val": pool_val, "test": sorted(test)}
        _assert_disjoint(fold)
        corner_folds[corner] = fold

    payloads = {
        "in_domain.json": {"seed": seed, "protocol": "in_domain_70_10_20", **in_domain},
        "leave_one_process_out.json": {"seed": seed, "protocol": "lopo", "folds": lopo},
        "few_shot_transfer.json": {
            "seed": seed,
            "protocol": "few_shot_target_table_adaptation",
            "ratios": list(few_shot_ratios),
            "folds": few_shot,
        },
        "gf180_leave_one_corner_out.json": {
            "seed": seed,
            "protocol": "gf180_loco",
            "folds": corner_folds,
        },
    }
    for name, payload in payloads.items():
        (root / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    summary = {
        "tables": len(tables),
        "processes": {key: len(value) for key, value in sorted(by_process.items())},
        "in_domain": {key: len(value) for key, value in in_domain.items()},
        "lopo_folds": len(lopo),
        "few_shot_folds": len(few_shot),
        "gf180_corner_folds": len(corner_folds),
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
