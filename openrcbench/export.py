from __future__ import annotations

import json
import math
import re
from pathlib import Path

from .io import read_jsonl
from .openrcx import parse_openrcx


def export_openrcx(
    original: str | Path,
    dataset: str | Path,
    predictions: str | Path,
    output: str | Path,
    *,
    source_id: str,
) -> dict[str, int]:
    """Write selected predictions into an OpenRCX model without touching context rows.

    Prediction JSON shape: `{"tables": {table_id: {row_index: {target: value}}}}`.
    Only listed targets and rows are changed.
    """

    payload = json.loads(Path(predictions).read_text(encoding="utf-8"))["tables"]
    tables = {table.table_id: table for table in read_jsonl(dataset) if table.source_id == source_id}
    if not tables:
        raise ValueError(f"No dataset tables for source {source_id}")
    exemplar = next(iter(tables.values()))
    parsed = {table.table_id: table for table in parse_openrcx(
        original, source_id=source_id, process_id=exemplar.process_id,
        corner_id=exemplar.corner_id)}
    if parsed.keys() != tables.keys() or any(parsed[k].rows != tables[k].rows for k in tables):
        raise ValueError("Original rules do not match frozen dataset truth")
    # Reparse line locations: historical datasets need not carry this metadata.
    original_lines = Path(original).read_bytes().decode("utf-8").splitlines(keepends=True)
    lines = list(original_lines)
    changed_lines = set()
    changed = 0
    for table_id, row_predictions in payload.items():
        if table_id not in tables:
            continue
        table = tables[table_id]
        for index_text, values in row_predictions.items():
            index = int(index_text)
            if not 0 <= index < len(table.rows):
                raise IndexError(f"Prediction row {index} outside {table_id}")
            line_index = parsed[table_id].metadata["row_line_numbers"][index] - 1
            old = lines[line_index]
            tokens = list(re.finditer(r"\S+", old))
            replacements = {}
            for target, value in values.items():
                if target not in {"coupling_cap", "ground_cap", "resistance"}:
                    raise ValueError(f"Unknown target {target}")
                if not math.isfinite(float(value)) or float(value) < 0:
                    raise ValueError(f"Prediction must be finite and nonnegative: {table_id}:{index}:{target}")
                if table.family == "RESOVER" and target != "resistance":
                    if float(value) != 0:
                        raise ValueError("RESOVER cannot encode capacitance predictions")
                    continue
                column = {"coupling_cap": 1, "ground_cap": 2, "resistance": 3}[target]
                replacements[column] = f"{float(value):.12g}"
            for column in sorted(replacements, reverse=True):
                token = tokens[column]
                old = old[:token.start()] + replacements[column] + old[token.end():]
            lines[line_index] = old
            changed_lines.add(line_index)
            changed += 1
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes("".join(lines).encode("utf-8"))
    reparsed = parse_openrcx(destination, source_id=source_id,
                            process_id=exemplar.process_id, corner_id=exemplar.corner_id)
    if {t.table_id for t in reparsed} != tables.keys():
        raise ValueError("Export changed table identities")
    reparsed_by_id = {t.table_id: t for t in reparsed}
    for table_id, row_predictions in payload.items():
        if table_id not in tables:
            continue
        for index, values in row_predictions.items():
            for target, value in values.items():
                if not math.isclose(reparsed_by_id[table_id].rows[int(index)][target],
                                    float(value), rel_tol=1e-10, abs_tol=1e-15):
                    raise ValueError("Exported value failed round-trip verification")
    written = destination.read_bytes().decode("utf-8").splitlines(keepends=True)
    if len(written) != len(original_lines) or any(
        written[i] != line for i, line in enumerate(original_lines) if i not in changed_lines
    ):
        raise ValueError("Export changed an unmasked line")
    return {"changed_rows": changed, "source_tables": len(tables)}
