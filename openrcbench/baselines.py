from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from .io import read_jsonl
from .masking import mask_indices
from .metrics import AGGREGATION_POLICY, grouped_regression_metrics, regression_metrics
from .metrics import physical_metrics
from .schema import TARGET_NAMES
from .training import _load_split


def _distance(a: dict[str, float], b: dict[str, float]) -> float:
    return math.hypot(a["spacing_left"] - b["spacing_left"], a["spacing_right"] - b["spacing_right"])


def _solve_rbf(matrix: list[list[float]], values: list[list[float]]) -> list[list[float]]:
    """Solve a small dense system with partial pivoting and multiple RHS."""

    size = len(matrix)
    rhs_count = len(values[0])
    augmented = [list(row) + list(rhs) for row, rhs in zip(matrix, values)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-14:
            raise ValueError("Singular RBF interpolation matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        for index in range(column, size + rhs_count):
            augmented[column][index] /= divisor
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if abs(factor) < 1e-18:
                continue
            for index in range(column, size + rhs_count):
                augmented[row][index] -= factor * augmented[column][index]
    return [row[size:] for row in augmented]


def _rbf_interpolate(
    rows: list[dict[str, float]], observed: list[int], hidden: set[int]
) -> dict[int, dict[str, float]]:
    """Gaussian radial-basis interpolation without an optional SciPy dependency."""

    pair_distances = sorted(
        _distance(rows[left], rows[right])
        for offset, left in enumerate(observed)
        for right in observed[offset + 1 :]
        if _distance(rows[left], rows[right]) > 1e-15
    )
    if not pair_distances:
        raise ValueError("RBF needs distinct observed coordinates")
    length_scale = pair_distances[len(pair_distances) // 2]

    def kernel(left: dict[str, float], right: dict[str, float]) -> float:
        scaled = _distance(left, right) / length_scale
        return math.exp(-(scaled * scaled))

    matrix = []
    for row_index, left in enumerate(observed):
        matrix.append(
            [
                # Fixed Tikhonov smoothing prevents the severe ill-conditioning
                # of broad Gaussian kernels on densely sampled 1-D tables.
                kernel(rows[left], rows[right]) + (1e-3 if row_index == column else 0.0)
                for column, right in enumerate(observed)
            ]
        )
    rhs = [[rows[index][target] for target in TARGET_NAMES] for index in observed]
    weights = _solve_rbf(matrix, rhs)
    result = {}
    for index in hidden:
        values = [kernel(rows[index], rows[observed_index]) for observed_index in observed]
        result[index] = {
            target: max(0.0, sum(value * weights[row][target_index] for row, value in enumerate(values)))
            for target_index, target in enumerate(TARGET_NAMES)
        }
    return result


def interpolate_table(rows: list[dict[str, float]], hidden: set[int], method: str) -> list[dict[str, float]]:
    observed = [i for i in range(len(rows)) if i not in hidden]
    if not observed:
        raise ValueError("At least one observed row is required")
    result = [{key: row[key] for key in TARGET_NAMES} for row in rows]
    means = {key: sum(rows[i][key] for i in observed) / len(observed) for key in TARGET_NAMES}
    if method == "rbf":
        try:
            for index, prediction in _rbf_interpolate(rows, observed, hidden).items():
                result[index] = prediction
            return result
        except ValueError:
            # Duplicate/degenerate coordinates occur in a few public tables;
            # deterministic IDW is the documented fallback for those tables.
            method = "linear"
    for index in hidden:
        if method == "mean":
            result[index] = dict(means)
            continue
        neighbors = sorted(observed, key=lambda i: _distance(rows[index], rows[i]))[:2]
        if method == "nearest" or len(neighbors) == 1:
            result[index] = {key: rows[neighbors[0]][key] for key in TARGET_NAMES}
            continue
        distances = [_distance(rows[index], rows[i]) for i in neighbors]
        if distances[0] < 1e-15:
            result[index] = {key: rows[neighbors[0]][key] for key in TARGET_NAMES}
        else:
            if method == "linear" and rows[neighbors[0]]["spacing_left"] == rows[neighbors[0]]["spacing_right"]:
                x = rows[index]["spacing_left"]
                points = sorted((rows[i]["spacing_left"], i) for i in observed)
                lower = max((point for point in points if point[0] <= x), default=points[0])
                upper = min((point for point in points if point[0] >= x), default=points[-1])
                if abs(upper[0] - lower[0]) < 1e-15:
                    result[index] = {key: rows[lower[1]][key] for key in TARGET_NAMES}
                else:
                    alpha = (x - lower[0]) / (upper[0] - lower[0])
                    result[index] = {
                        key: (1 - alpha) * rows[lower[1]][key] + alpha * rows[upper[1]][key]
                        for key in TARGET_NAMES
                    }
            elif method == "linear":
                weights = [1 / (value + 1e-12) for value in distances]
                result[index] = {
                    key: sum(w * rows[i][key] for w, i in zip(weights, neighbors)) / sum(weights)
                    for key in TARGET_NAMES
                }
            else:
                raise ValueError(f"Unknown interpolation method {method}")
    return result


def evaluate_baseline(
    dataset: str | Path,
    split_path: str | Path,
    output: str | Path,
    *,
    method: str,
    protocol: str,
    ratio: float,
    seed: int,
    fold: str | None = None,
) -> dict:
    split = _load_split(split_path, fold)
    test_ids = set(split["test"])
    records = []
    table_physical_records = []
    grouped = defaultdict(lambda: {"truth": [], "prediction": []})
    for table in read_jsonl(dataset):
        if table.table_id not in test_ids:
            continue
        hidden = mask_indices(table, protocol, ratio, seed)
        predictions = interpolate_table(table.rows, hidden, method)
        table_physical_records.append(
            {
                "table_id": table.table_id,
                "process_id": table.process_id,
                "family": table.family,
                "metrics": physical_metrics(table, predictions),
            }
        )
        for target in TARGET_NAMES:
            if not any(abs(row[target]) > 0 for row in table.rows):
                continue
            metrics = regression_metrics(
                [table.rows[i][target] for i in sorted(hidden)],
                [predictions[i][target] for i in sorted(hidden)],
            )
            records.append(
                {
                    "table_id": table.table_id,
                    "process_id": table.process_id,
                    "family": table.family,
                    "target": target,
                    "metrics": metrics,
                }
            )
            group = grouped[(table.process_id, target)]
            group["truth"].extend(table.rows[i][target] for i in sorted(hidden))
            group["prediction"].extend(predictions[i][target] for i in sorted(hidden))
    if not records:
        raise ValueError("No test tables matched the split")
    macro, zero_truth_groups = grouped_regression_metrics(grouped)
    physical_macro = {}
    for metric in (
        "negative_rate",
        "monotonic_violation_rate",
        "symmetry_mae",
        "local_total_variation",
    ):
        values = [
            record["metrics"][metric]
            for record in table_physical_records
            if record["metrics"][metric] is not None
        ]
        physical_macro[metric] = sum(values) / len(values) if values else None
    payload = {
        "method": method,
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
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
