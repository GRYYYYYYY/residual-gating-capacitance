from __future__ import annotations

import json
import re
from pathlib import Path

from .metrics import regression_metrics


DNET_RE = re.compile(r"^\*D_NET\s+(\S+)\s+([-+0-9.eE]+)")


def _ranks(values: list[float]) -> list[float]:
    """Average ranks for ties, using zero-based ranks."""

    ordered = sorted(range(len(values)), key=lambda index: values[index])
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + end - 1) / 2
        for offset in range(start, end):
            result[ordered[offset]] = rank
        start = end
    return result


def spearman_correlation(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Correlation inputs must have equal non-zero length")
    left_ranks = _ranks(left)
    right_ranks = _ranks(right)
    left_mean = sum(left_ranks) / len(left_ranks)
    right_mean = sum(right_ranks) / len(right_ranks)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left_ranks, right_ranks)
    )
    left_norm = sum((x - left_mean) ** 2 for x in left_ranks) ** 0.5
    right_norm = sum((y - right_mean) ** 2 for y in right_ranks) ** 0.5
    if left_norm < 1e-15 or right_norm < 1e-15:
        return 1.0 if left_ranks == right_ranks else 0.0
    return numerator / (left_norm * right_norm)


def parse_spef(path: str | Path) -> dict[str, dict[str, float]]:
    nets = {}
    name_map = {}
    current = None
    section = None
    with Path(path).open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            match = DNET_RE.match(line)
            if match:
                current = name_map.get(match.group(1), match.group(1))
                if current in nets:
                    raise ValueError(f"Duplicate SPEF net {current}")
                nets[current] = {"capacitance": float(match.group(2)), "resistance": 0.0}
                section = None
                continue
            if line == "*NAME_MAP":
                section = line
                continue
            if section == "*NAME_MAP":
                parts = line.split(maxsplit=1)
                if len(parts) == 2 and re.fullmatch(r"\*\d+", parts[0]):
                    name_map[parts[0]] = parts[1]
                    continue
                if line.startswith("*"):
                    section = None
            if line in {"*CONN", "*CAP", "*RES"}:
                section = line
                continue
            if line == "*END":
                current = section = None
                continue
            if current and section == "*RES" and line and not line.startswith("*"):
                fields = line.split()
                if len(fields) != 4:
                    raise ValueError(f"Malformed SPEF resistance row: {line}")
                nets[current]["resistance"] += float(fields[-1])
    if not nets:
        raise ValueError(f"No *D_NET sections found in {path}")
    return nets


def compare_spef(golden: str | Path, candidate: str | Path, output: str | Path) -> dict:
    def units(path):
        found = {}
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if fields and fields[0] in {"*C_UNIT", "*R_UNIT"}:
                    found[fields[0]] = (float(fields[1]), fields[2].upper())
                if line.startswith("*D_NET"):
                    break
        return found
    reference_units = units(golden)
    if reference_units != units(candidate):
        raise ValueError("SPEF unit declarations differ; convert units before comparison")
    reference = parse_spef(golden)
    predicted = parse_spef(candidate)
    common = sorted(set(reference) & set(predicted))
    if not common:
        raise ValueError("SPEF files have no common nets")
    metrics = {}
    for target in ("capacitance", "resistance"):
        truth = [reference[net][target] for net in common]
        prediction = [predicted[net][target] for net in common]
        metrics[target] = regression_metrics(truth, prediction)
        metrics[target]["spearman"] = spearman_correlation(truth, prediction)
    payload = {
        "units": reference_units,
        "golden_nets": len(reference),
        "candidate_nets": len(predicted),
        "common_nets": len(common),
        "missing_nets": sorted(set(reference) - set(predicted)),
        "extra_nets": sorted(set(predicted) - set(reference)),
        "metrics": metrics,
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {key: value for key, value in payload.items() if key not in {"missing_nets", "extra_nets"}}
