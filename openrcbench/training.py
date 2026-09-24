from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

from .io import read_jsonl
from .masking import mask_indices
from .schema import RCTable, TARGET_NAMES
from .metrics import AGGREGATION_POLICY, grouped_regression_metrics, regression_metrics, physical_metrics
from .physics import active_targets, monotonic_rules


FAMILIES = ("RESOVER", "OVER", "UNDER", "OVERUNDER", "DIAGUNDER")


def _require_torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Training requires `pip install -e .[train]`") from exc
    return torch


def _load_split(path: str | Path, fold: str | None) -> dict[str, list[str]]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if "folds" in value:
        if not fold:
            raise ValueError("This split has folds; pass --fold")
        return value["folds"][fold]
    return {key: value[key] for key in ("train", "val", "test")}


def _target_scales(tables: list[RCTable]) -> list[float]:
    scales = []
    for target in TARGET_NAMES:
        values = sorted(row[target] for table in tables for row in table.rows if row[target] > 0)
        scales.append(values[len(values) // 2] if values else 1.0)
    return scales


def _base_features(
    table: RCTable,
    row: dict[str, float],
    *,
    use_process_descriptors: bool = True,
) -> list[float]:
    if use_process_descriptors:
        layer_count = float(table.process_features.get("layer_count") or max(table.metal, 1))
        node_nm = float(table.process_features.get("node_nm") or 0.0)
    else:
        # Fixed scaling retains layer/context geometry without revealing a
        # process-specific layer count or technology-node descriptor.
        layer_count = 20.0
        node_nm = 0.0
    continuous = [
        math.log1p(row["spacing_left"]),
        math.log1p(row["spacing_right"]),
        math.log1p(table.width),
        table.metal / layer_count,
        table.context_below / layer_count,
        table.context_above / layer_count,
        math.log1p(node_nm) / math.log(1001.0),
    ]
    categorical = [float(table.family == family) for family in FAMILIES]
    return continuous + categorical


def _encode_table(
    table: RCTable,
    hidden: set[int],
    scales: list[float],
    *,
    use_observed_context: bool = True,
    use_process_descriptors: bool = True,
) -> list[list[float]]:
    encoded = []
    for index, row in enumerate(table.rows):
        observed = index not in hidden
        expose = observed and use_observed_context
        values = [
            math.log1p(row[target] / scale) if expose else 0.0
            for target, scale in zip(TARGET_NAMES, scales)
        ]
        encoded.append(
            _base_features(
                table, row, use_process_descriptors=use_process_descriptors
            )
            + values
            + [float(expose)]
        )
    return encoded


def _collate(
    torch,
    tables: list[RCTable],
    masks: list[set[int]],
    scales: list[float],
    device,
    *,
    use_observed_context: bool = True,
    use_process_descriptors: bool = True,
):
    max_len = max(len(table.rows) for table in tables)
    feature_dim = 16
    x = torch.zeros((len(tables), max_len, feature_dim), dtype=torch.float32)
    y = torch.zeros((len(tables), max_len, 3), dtype=torch.float32)
    padding = torch.ones((len(tables), max_len), dtype=torch.bool)
    hidden_tensor = torch.zeros((len(tables), max_len), dtype=torch.bool)
    active_tensor = torch.zeros((len(tables), max_len, 3), dtype=torch.bool)
    coords = torch.zeros((len(tables), max_len, 2), dtype=torch.float32)
    for batch_index, (table, hidden) in enumerate(zip(tables, masks)):
        features = _encode_table(
            table,
            hidden,
            scales,
            use_observed_context=use_observed_context,
            use_process_descriptors=use_process_descriptors,
        )
        length = len(features)
        x[batch_index, :length] = torch.tensor(features)
        y[batch_index, :length] = torch.tensor(
            [[math.log1p(row[target] / scale) for target, scale in zip(TARGET_NAMES, scales)] for row in table.rows]
        )
        padding[batch_index, :length] = False
        hidden_tensor[batch_index, list(hidden)] = True
        for target_index, target in enumerate(TARGET_NAMES):
            if any(abs(row[target]) > 0 for row in table.rows):
                active_tensor[batch_index, :length, target_index] = True
        coords[batch_index, :length] = torch.tensor(
            [[row["spacing_left"], row["spacing_right"]] for row in table.rows]
        )
    return tuple(
        value.to(device) for value in (x, y, padding, hidden_tensor, active_tensor, coords)
    )


def _physics_loss(torch, prediction, truth, hidden, padding, coords, tables: list[RCTable]):
    # Evaluation completes a table by preserving every observed row and using
    # the model only at masked rows.  Apply the physical objective to that same
    # completed table.  Penalizing unconstrained model outputs at observed rows
    # would optimize a surface that is never used by the completion protocol.
    completed = torch.where(hidden.unsqueeze(-1), prediction, truth)
    monotonic = prediction.new_tensor(0.0)
    smooth = prediction.new_tensor(0.0)
    symmetry = prediction.new_tensor(0.0)
    monotonic_terms = 0
    smooth_terms = 0
    symmetry_terms_used = 0
    for batch_index, table in enumerate(tables):
        valid = ~padding[batch_index]
        count = int(valid.sum())
        if count < 2:
            continue
        valid_coords = coords[batch_index, valid]
        valid_prediction = completed[batch_index, valid]
        active = set(active_targets(table.rows, TARGET_NAMES))
        for rule in monotonic_rules(table.family):
            if rule.target not in active:
                continue
            axis_index = {"spacing_left": 0, "spacing_right": 1}[rule.axis]
            order = torch.argsort(valid_coords[:, axis_index])
            values = valid_prediction[:, TARGET_NAMES.index(rule.target)][order]
            deltas = values[1:] - values[:-1]
            if rule.direction == "nonincreasing":
                monotonic = monotonic + torch.relu(deltas).mean()
            else:
                monotonic = monotonic + torch.relu(-deltas).mean()
            monotonic_terms += 1
            if count >= 3:
                smooth = smooth + (values[2:] - 2 * values[1:-1] + values[:-2]).abs().mean()
                smooth_terms += 1
        if not active:
            continue
        coordinate_pairs = {
            (round(float(pair[0]), 12), round(float(pair[1]), 12)): index
            for index, pair in enumerate(valid_coords)
        }
        symmetry_terms = []
        for (left, right), index in coordinate_pairs.items():
            swapped = coordinate_pairs.get((right, left))
            if swapped is not None and index < swapped:
                active_indices = [TARGET_NAMES.index(target) for target in active]
                symmetry_terms.append(
                    (valid_prediction[index, active_indices] - valid_prediction[swapped, active_indices])
                    .abs()
                    .mean()
                )
        if symmetry_terms:
            symmetry = symmetry + torch.stack(symmetry_terms).mean()
            symmetry_terms_used += 1
    zero = prediction.new_tensor(0.0)
    return (
        monotonic / monotonic_terms if monotonic_terms else zero,
        smooth / smooth_terms if smooth_terms else zero,
        symmetry / symmetry_terms_used if symmetry_terms_used else zero,
    )


def _balanced_epoch_tables(tables: list[RCTable], seed: int) -> list[RCTable]:
    by_process = defaultdict(list)
    for table in tables:
        by_process[table.process_id].append(table)
    target = max(len(values) for values in by_process.values())
    rng = random.Random(seed)
    balanced = []
    for values in by_process.values():
        local = list(values)
        rng.shuffle(local)
        balanced.extend(local[i % len(local)] for i in range(target))
    rng.shuffle(balanced)
    return balanced


def train_model(
    dataset: str | Path,
    split_path: str | Path,
    output_dir: str | Path,
    *,
    fold: str | None = None,
    seed: int = 0,
    epochs: int = 100,
    batch_size: int = 16,
    mask_ratio: float = 0.3,
    learning_rate: float = 2e-4,
    physics_lambda: float = 0.05,
    monotonic_weight: float = 1.0,
    symmetry_weight: float = 1.0,
    smoothness_weight: float = 0.1,
    use_observed_context: bool = True,
    use_process_descriptors: bool = True,
    all_row_training: bool = False,
) -> dict:
    torch = _require_torch()
    from .model import MaskedRCTransformer

    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    split = _load_split(split_path, fold)
    all_tables = {table.table_id: table for table in read_jsonl(dataset)}
    groups = {name: [all_tables[x] for x in ids] for name, ids in split.items()}
    scales = _target_scales(groups["train"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MaskedRCTransformer().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    history = []
    best = float("inf")

    for epoch in range(1, epochs + 1):
        model.train()
        shuffled = _balanced_epoch_tables(groups["train"], seed * 100000 + epoch)
        train_sum = 0.0
        train_batches = 0
        for start in range(0, len(shuffled), batch_size):
            tables = shuffled[start : start + batch_size]
            masks = (
                [set(range(len(table.rows))) for table in tables]
                if all_row_training
                else [mask_indices(t, "mcar", mask_ratio, seed * 100000 + epoch) for t in tables]
            )
            x, y, padding, hidden, active, coords = _collate(
                torch,
                tables,
                masks,
                scales,
                device,
                use_observed_context=use_observed_context and not all_row_training,
                use_process_descriptors=use_process_descriptors,
            )
            prediction = model(x, padding)
            supervised = hidden.unsqueeze(-1) & active
            if not bool(supervised.any()):
                continue
            data_loss = torch.nn.functional.mse_loss(prediction[supervised], y[supervised])
            monotonic, smooth, symmetry = _physics_loss(
                torch, prediction, y, hidden, padding, coords, tables
            )
            loss = data_loss + physics_lambda * (
                monotonic_weight * monotonic
                + symmetry_weight * symmetry
                + smoothness_weight * smooth
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_sum += float(data_loss.detach())
            train_batches += 1

        model.eval()
        val_sum = 0.0
        val_batches = 0
        with torch.no_grad():
            for start in range(0, len(groups["val"]), batch_size):
                tables = groups["val"][start : start + batch_size]
                masks = (
                    [set(range(len(table.rows))) for table in tables]
                    if all_row_training
                    else [mask_indices(t, "mcar", mask_ratio, seed) for t in tables]
                )
                x, y, padding, hidden, active, _coords = _collate(
                    torch,
                    tables,
                    masks,
                    scales,
                    device,
                    use_observed_context=use_observed_context and not all_row_training,
                    use_process_descriptors=use_process_descriptors,
                )
                supervised = hidden.unsqueeze(-1) & active
                if not bool(supervised.any()):
                    continue
                val_sum += float(
                    torch.nn.functional.mse_loss(model(x, padding)[supervised], y[supervised])
                )
                val_batches += 1
        record = {
            "epoch": epoch,
            "train_mse": train_sum / max(1, train_batches),
            "val_mse": val_sum / max(1, val_batches),
        }
        history.append(record)
        if record["val_mse"] < best:
            best = record["val_mse"]
            torch.save(model.state_dict(), destination / "best.pt")

    config = {
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "mask_ratio": mask_ratio,
        "learning_rate": learning_rate,
        "physics_lambda": physics_lambda,
        "monotonic_weight": monotonic_weight,
        "symmetry_weight": symmetry_weight,
        "smoothness_weight": smoothness_weight,
        "use_observed_context": use_observed_context,
        "use_process_descriptors": use_process_descriptors,
        "all_row_training": all_row_training,
        "target_scales": dict(zip(TARGET_NAMES, scales)),
        "split": str(split_path),
        "fold": fold,
        "device": str(device),
        "best_val_mse": best,
    }
    (destination / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (destination / "history.jsonl").write_text(
        "\n".join(json.dumps(x) for x in history) + "\n", encoding="utf-8"
    )
    return config


def evaluate_model(
    dataset: str | Path,
    split_path: str | Path,
    checkpoint_dir: str | Path,
    output: str | Path,
    *,
    fold: str | None = None,
    protocol: str = "mcar",
    ratio: float = 0.3,
    seed: int = 0,
    partition: str = "test",
) -> dict:
    if partition not in {"test", "val"}:
        raise ValueError("Evaluation partition must be 'test' or 'val'")
    torch = _require_torch()
    from .model import MaskedRCTransformer

    split = _load_split(split_path, fold)
    evaluation_ids = set(split[partition])
    tables = [table for table in read_jsonl(dataset) if table.table_id in evaluation_ids]
    if not tables:
        raise ValueError(f"No tables found for evaluation partition {partition!r}")
    root = Path(checkpoint_dir)
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    scales = [config["target_scales"][name] for name in TARGET_NAMES]
    use_observed_context = config.get("use_observed_context", True) and not config.get(
        "all_row_training", False
    )
    use_process_descriptors = config.get("use_process_descriptors", True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MaskedRCTransformer().to(device)
    model.load_state_dict(torch.load(root / "best.pt", map_location=device, weights_only=True))
    model.eval()
    grouped = {}
    records = []
    table_physical_records = []
    export_payload = {"tables": {}}
    with torch.no_grad():
        for table in tables:
            hidden = mask_indices(table, protocol, ratio, seed)
            x, _y, padding, _hidden_tensor, _active, _coords = _collate(
                torch,
                [table],
                [hidden],
                scales,
                device,
                use_observed_context=use_observed_context,
                use_process_descriptors=use_process_descriptors,
            )
            encoded = model(x, padding)[0, : len(table.rows)]
            decoded = torch.expm1(encoded).cpu()
            predictions = []
            for row_index in range(len(table.rows)):
                predictions.append(
                    {
                        target: max(0.0, float(decoded[row_index, target_index]) * scales[target_index])
                        for target_index, target in enumerate(TARGET_NAMES)
                    }
                )
            export_payload["tables"][table.table_id] = {
                str(index): predictions[index] for index in sorted(hidden)
            }
            for target in TARGET_NAMES:
                if not any(abs(row[target]) > 0 for row in table.rows):
                    continue
                truth = [table.rows[i][target] for i in sorted(hidden)]
                pred = [predictions[i][target] for i in sorted(hidden)]
                records.append(
                    {
                        "table_id": table.table_id,
                        "process_id": table.process_id,
                        "family": table.family,
                        "target": target,
                        "metrics": regression_metrics(truth, pred),
                    }
                )
                key = (table.process_id, target)
                group = grouped.setdefault(key, {"truth": [], "prediction": []})
                group["truth"].extend(truth)
                group["prediction"].extend(pred)
            completed = [dict(row) for row in table.rows]
            for index in hidden:
                completed[index].update(predictions[index])
            table_physical_records.append(
                {
                    "table_id": table.table_id,
                    "process_id": table.process_id,
                    "family": table.family,
                    "metrics": physical_metrics(table, completed),
                }
            )
    macro, zero_truth_groups = grouped_regression_metrics(grouped)
    physical_macro = {}
    for metric in ("negative_rate", "monotonic_violation_rate", "symmetry_mae", "local_total_variation"):
        values = [
            record["metrics"][metric]
            for record in table_physical_records
            if record["metrics"][metric] is not None
        ]
        physical_macro[metric] = sum(values) / len(values) if values else None
    result = {
        "method": "rc-mtm",
        "partition": partition,
        "protocol": protocol,
        "ratio": ratio,
        "seed": seed,
        "fold": fold,
        "macro_average": macro,
        "aggregation_policy": AGGREGATION_POLICY,
        "zero_truth_groups": zero_truth_groups,
        "physical_macro_average": physical_macro,
        "records": records,
        "table_physical_records": table_physical_records,
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    (destination.parent / f"{destination.stem}_predictions.json").write_text(
        json.dumps(export_payload), encoding="utf-8"
    )
    return {
        key: value
        for key, value in result.items()
        if key not in {"records", "table_physical_records"}
    }
