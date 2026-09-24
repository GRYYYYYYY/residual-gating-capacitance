from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .schema import RCTable, validate_table


HEADER_RE = re.compile(
    r"^Metal\s+(?P<metal>\d+)\s+(?P<family>RESOVER|OVER|UNDER|OVERUNDER|DIAGUNDER)"
    r"(?:\s+(?P<context1>\d+))?(?:\s+UNDER\s+(?P<context2>\d+))?\s*$"
)
DIST_RE = re.compile(
    r"^DIST\s+count\s+(?P<count>\d+)\s+width\s+(?P<width>[-+0-9.eE]+)"
)


def _table_id(parts: list[str]) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def parse_openrcx(
    path: str | Path,
    *,
    source_id: str,
    process_id: str,
    corner_id: str,
    process_features: dict[str, float | None] | None = None,
) -> list[RCTable]:
    """Parse the public OpenRCX v1 model format.

    Per the OpenROAD format note, ordinary rows are
    `<spacing> <coupling fF/nm> <ground fF/nm> <resistance ohm/nm>`;
    RESOVER rows use left/right spacing followed by two zeros and resistance.
    """

    lines = Path(path).read_text(encoding="utf-8", errors="strict").splitlines()
    tables: list[RCTable] = []
    header: dict[str, int | str] | None = None
    widths: list[float] = []
    i = 0
    while i < len(lines):
        text = lines[i].strip()
        match = HEADER_RE.match(text)
        if match:
            family = match.group("family")
            metal = int(match.group("metal"))
            c1 = int(match.group("context1") or 0)
            c2 = int(match.group("context2") or 0)
            if family == "OVER" and match.group("context2") is not None:
                family = "OVERUNDER"
            if family == "OVER":
                below, above = c1, 0
            elif family in {"UNDER", "DIAGUNDER"}:
                below, above = 0, c1
            elif family == "OVERUNDER":
                below, above = c1, c2
            else:
                below, above = c1, 0
            header = {
                "family": family,
                "metal": metal,
                "context_below": below,
                "context_above": above,
            }
            i += 1
            continue
        if text.startswith("WIDTH Table"):
            _, _, values = text.partition("entries:")
            widths = [float(x) for x in values.split()]
            i += 1
            continue
        dist = DIST_RE.match(text)
        if dist and header is not None:
            expected = int(dist.group("count"))
            width = float(dist.group("width"))
            rows: list[dict[str, float]] = []
            row_line_numbers: list[int] = []
            dist_header_line = i + 1
            i += 1
            row_start_line = i + 1
            while i < len(lines) and lines[i].strip() != "END DIST":
                row_text = lines[i].strip()
                if row_text and not row_text.startswith("#"):
                    row_line_numbers.append(i + 1)
                    values = [float(x) for x in row_text.split()]
                    if len(values) != 4:
                        raise ValueError(f"{path}:{i + 1}: expected 4 numeric columns")
                    if header["family"] == "RESOVER":
                        left, right, _unused, resistance = values
                        coupling = ground = 0.0
                    else:
                        left, coupling, ground, resistance = values
                        right = left
                    rows.append(
                        {
                            "spacing_left": left,
                            "spacing_right": right,
                            "coupling_cap": coupling,
                            "ground_cap": ground,
                            "resistance": resistance,
                        }
                    )
                i += 1
            if len(rows) != expected:
                raise ValueError(
                    f"{path}:{i + 1}: DIST declares {expected} rows, parsed {len(rows)}"
                )
            # OpenRCX files may retain explicit zero-entry sections for model
            # families that are unavailable at a given layer/context.
            if expected == 0:
                i += 1
                continue
            parts = [
                source_id,
                process_id,
                corner_id,
                str(header["family"]),
                str(header["metal"]),
                str(header["context_below"]),
                str(header["context_above"]),
                f"{width:.12g}",
            ]
            table = RCTable(
                table_id=_table_id(parts),
                source_id=source_id,
                process_id=process_id,
                corner_id=corner_id,
                family=str(header["family"]),
                metal=int(header["metal"]),
                context_below=int(header["context_below"]),
                context_above=int(header["context_above"]),
                width=width,
                rows=rows,
                process_features=dict(process_features or {}),
                metadata={
                    "declared_widths": widths,
                    "dist_header_line": dist_header_line,
                    "row_start_line": row_start_line,
                    "row_line_numbers": row_line_numbers,
                    "source_table_index": len(tables),
                },
            )
            validate_table(table)
            tables.append(table)
        i += 1
    if not tables:
        raise ValueError(f"No OpenRCX DIST tables found in {path}")
    return tables
