from __future__ import annotations

import json
from pathlib import Path

from .io import write_jsonl
from .openrcx import parse_openrcx
from .sources import expand_sources, load_manifest


def build_dataset(
    manifest_path: str | Path,
    process_path: str | Path,
    raw_dir: str | Path,
    output: str | Path,
) -> dict[str, int]:
    manifest = load_manifest(manifest_path)
    processes = json.loads(Path(process_path).read_text(encoding="utf-8"))["processes"]
    tables = []
    source_count = 0
    for source in expand_sources(manifest):
        if source["format"] != "openrcx":
            continue
        path = Path(raw_dir) / source["path"]
        if not path.exists():
            raise FileNotFoundError(f"Run download first; missing {path}")
        features = processes[source["process_id"]]
        parsed = parse_openrcx(
            path,
            source_id=source["source_id"],
            process_id=source["process_id"],
            corner_id=source["corner_id"],
            process_features=features,
        )
        tables.extend(parsed)
        source_count += 1
    table_ids = [table.table_id for table in tables]
    if len(table_ids) != len(set(table_ids)):
        raise ValueError("Duplicate table_id detected; sources are not independent")
    write_jsonl(output, tables)
    return {
        "sources": source_count,
        "tables": len(tables),
        "rows": sum(len(table.rows) for table in tables),
    }
