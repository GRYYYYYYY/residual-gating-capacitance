from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path


def _bootstrap_ci(values: list[float], key: str, samples: int = 10000) -> tuple[float, float]:
    """Deterministic percentile bootstrap confidence interval over run seeds."""

    if len(values) == 1:
        return values[0], values[0]
    digest = hashlib.sha256(key.encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    means = sorted(
        sum(rng.choice(values) for _ in values) / len(values) for _ in range(samples)
    )
    return means[int(0.025 * samples)], means[min(samples - 1, int(0.975 * samples))]


def summarize_runs(input_dir: str | Path, output_prefix: str | Path) -> dict:
    grouped = defaultdict(list)
    for path in sorted(Path(input_dir).glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if "macro_average" not in value:
            continue
        key = (
            value["method"],
            value["protocol"],
            float(value["ratio"]),
            value.get("fold"),
        )
        grouped[key].append(value)
    rows = []
    for (method, protocol, ratio, fold), runs in sorted(
        grouped.items(), key=lambda item: tuple(str(value) for value in item[0])
    ):
        values = [run["macro_average"] for run in runs]
        row = {
            "method": method,
            "protocol": protocol,
            "ratio": ratio,
            "fold": fold or "",
            "seeds": len(values),
        }
        for metric in ("mae", "rmse", "nrmse", "smape", "r2"):
            observations = [value[metric] for value in values]
            mean = sum(observations) / len(observations)
            std = math.sqrt(sum((x - mean) ** 2 for x in observations) / max(1, len(observations) - 1))
            low, high = _bootstrap_ci(observations, f"{method}:{protocol}:{ratio}:{fold}:{metric}")
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95_low"] = low
            row[f"{metric}_ci95_high"] = high
        for metric in (
            "negative_rate",
            "monotonic_violation_rate",
            "symmetry_mae",
            "local_total_variation",
        ):
            observations = [
                run.get("physical_macro_average", {}).get(metric)
                for run in runs
            ]
            observations = [value for value in observations if value is not None]
            row[f"physical_{metric}_mean"] = (
                sum(observations) / len(observations) if observations else ""
            )
        rows.append(row)
    if not rows:
        raise ValueError(f"No result JSON files in {input_dir}")
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    (prefix.with_suffix(".json")).write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    with prefix.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "| Method | Protocol | Fold | Ratio | Seeds | NRMSE (95% CI) | sMAPE | R2 |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method']} | {row['protocol']} | {row['fold'] or '—'} | "
            f"{row['ratio']:.1f} | {row['seeds']} | "
            f"{row['nrmse_mean']:.4f} "
            f"[{row['nrmse_ci95_low']:.4f}, {row['nrmse_ci95_high']:.4f}] | "
            f"{row['smape_mean']:.4f}±{row['smape_std']:.4f} | "
            f"{row['r2_mean']:.4f}±{row['r2_std']:.4f} |"
        )
    prefix.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    selected = [
        row
        for row in rows
        if row["protocol"] == "mcar" and abs(row["ratio"] - 0.3) < 1e-12 and not row["fold"]
    ]
    classical = all(row["method"] in {"mean", "nearest", "linear", "rbf"} for row in rows)
    caption = "Dependency-free baselines" if classical else "Tabular baselines"
    label = "classical-baselines" if classical else "tabular-baselines"
    latex = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{" + caption + r" for 30\% MCAR completion. Intervals are deterministic 95\% bootstrap CIs over three seeds.}",
        r"\label{tab:" + label + "}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Method & NRMSE $\downarrow$ & sMAPE $\downarrow$ & $R^2$ $\uparrow$ \\",
        r"\midrule",
    ]
    for row in selected:
        latex.append(
            f"{row['method'].upper()} & {row['nrmse_mean']:.4f} "
            f"[{row['nrmse_ci95_low']:.4f}, {row['nrmse_ci95_high']:.4f}] & "
            f"{row['smape_mean']:.4f} & {row['r2_mean']:.4f} \\\\" 
        )
    latex.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    prefix.with_suffix(".tex").write_text("\n".join(latex) + "\n", encoding="utf-8")
    return {"groups": len(rows), "result_files": sum(len(x) for x in grouped.values())}
