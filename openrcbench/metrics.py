from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

from .physics import active_targets, monotonic_rules
from .schema import RCTable, TARGET_NAMES


def regression_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    truth = list(y_true)
    pred = list(y_pred)
    if len(truth) != len(pred) or not truth:
        raise ValueError("Metric inputs must have equal non-zero length")
    errors = [p - y for y, p in zip(truth, pred)]
    mae = sum(abs(x) for x in errors) / len(errors)
    rmse = math.sqrt(sum(x * x for x in errors) / len(errors))
    mean = sum(truth) / len(truth)
    variance = sum((x - mean) ** 2 for x in truth) / len(truth)
    # RMS normalization remains defined for physically constant tables, unlike
    # standard-deviation normalization. Structurally absent all-zero targets
    # are filtered by the evaluator.
    rms_truth = math.sqrt(sum(x * x for x in truth) / len(truth))
    nrmse = rmse / (rms_truth + 1e-12)
    smape = sum(2 * abs(p - y) / (abs(p) + abs(y) + 1e-12) for y, p in zip(truth, pred)) / len(truth)
    denominator = sum((x - mean) ** 2 for x in truth)
    r2 = (1.0 if rmse < 1e-15 else 0.0) if denominator < 1e-24 else 1 - sum(x * x for x in errors) / denominator
    return {"mae": mae, "rmse": rmse, "nrmse": nrmse, "smape": smape, "r2": r2}


def physical_metrics(table: RCTable, completed_rows: list[dict[str, float]]) -> dict[str, float | None]:
    """Measure physical behavior of a completed table.

    ``completed_rows`` must contain observed rows unchanged and predictions at
    missing rows.  Metrics that do not apply to a family are reported as null
    rather than as artificial zeros.
    """

    rows = table.rows
    if len(rows) != len(completed_rows):
        raise ValueError("Physical metric length mismatch")
    active = active_targets(rows, TARGET_NAMES)
    values = [prediction[target] for prediction in completed_rows for target in active]
    negative_rate = sum(v < 0 for v in values) / max(1, len(values))

    violations = 0
    comparisons = 0
    variation_terms = []
    for rule in monotonic_rules(table.family):
        if rule.target not in active:
            continue
        ordered = sorted(range(len(rows)), key=lambda i: (rows[i][rule.axis], i))
        for left, right in zip(ordered, ordered[1:]):
            delta = completed_rows[right][rule.target] - completed_rows[left][rule.target]
            if rule.direction == "nonincreasing":
                violations += delta > 1e-12
            else:  # Kept explicit so future registry additions cannot silently invert a rule.
                violations += delta < -1e-12
            comparisons += 1
            variation_terms.append(abs(delta))

    coordinate_pairs = {
        (round(row["spacing_left"], 12), round(row["spacing_right"], 12)): index
        for index, row in enumerate(rows)
    }
    symmetry_terms = []
    for (left, right), index in coordinate_pairs.items():
        swapped = coordinate_pairs.get((right, left))
        if swapped is None or index >= swapped:
            continue
        symmetry_terms.extend(
            abs(completed_rows[index][target] - completed_rows[swapped][target])
            for target in active
        )
    monotonic_violation_rate = violations / max(1, comparisons)
    return {
        "negative_rate": negative_rate,
        "monotonic_violation_rate": monotonic_violation_rate if comparisons else None,
        "symmetry_mae": sum(symmetry_terms) / len(symmetry_terms) if symmetry_terms else None,
        "local_total_variation": (
            sum(variation_terms) / len(variation_terms) if variation_terms else None
        ),
    }


def macro_average(records: Iterable[dict]) -> dict[str, float]:
    groups: dict[str, list[dict[str, float]]] = defaultdict(list)
    for record in records:
        groups[record["process_id"]].append(record["metrics"])
    process_means = []
    for metrics in groups.values():
        process_means.append({k: sum(x[k] for x in metrics) / len(metrics) for k in metrics[0]})
    return {k: sum(x[k] for x in process_means) / len(process_means) for k in process_means[0]}


AGGREGATION_POLICY = "nonzero-truth-groups-v2"


def grouped_regression_metrics(grouped):
    """Macro over nonzero-truth groups; preserve zero-truth absolute errors."""
    eligible, zeros = [], []
    for (process, target), values in sorted(grouped.items()):
        metrics = regression_metrics(values["truth"], values["prediction"])
        if any(y != 0 for y in values["truth"]):
            eligible.append(metrics)
        else:
            zeros.append({"process": process, "target": target,
                          "masked_rows": len(values["truth"]),
                          "mae": metrics["mae"], "rmse": metrics["rmse"]})
    if not eligible:
        raise ValueError("No nonzero-truth groups available for macro averaging")
    return ({key: sum(m[key] for m in eligible) / len(eligible)
             for key in eligible[0]}, zeros)
