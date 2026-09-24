from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

from .schema import RCTable, validate_table


def read_jsonl(path: str | Path) -> Iterator[RCTable]:
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                table = RCTable.from_dict(json.loads(line))
                validate_table(table)
                yield table
            except Exception as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc


def write_jsonl(path: str | Path, tables: Iterable[RCTable]) -> int:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with destination.open("w", encoding="utf-8") as handle:
        for table in tables:
            validate_table(table)
            handle.write(json.dumps(table.to_dict(), sort_keys=True) + "\n")
            count += 1
    return count

