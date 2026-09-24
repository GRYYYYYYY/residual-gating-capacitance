from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "openrcbench-1.0"
TARGET_NAMES = ("coupling_cap", "ground_cap", "resistance")


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    process_id: str
    corner_id: str
    path: str
    url: str
    sha256: str
    license: str
    commit: str
    redistributable: bool = False


@dataclass
class RCTable:
    """One complete OpenRCX distance table.

    Rows remain grouped as a table throughout splitting.  `context_below` and
    `context_above` use OpenRCX's one-based metal indices; zero denotes the
    substrate.  Each row stores left/right spacing and three physical targets.
    """

    table_id: str
    source_id: str
    process_id: str
    corner_id: str
    family: str
    metal: int
    context_below: int
    context_above: int
    width: float
    rows: list[dict[str, float]]
    process_features: dict[str, float | None] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RCTable":
        return cls(**value)


def validate_table(table: RCTable) -> None:
    if table.family not in {"RESOVER", "OVER", "UNDER", "OVERUNDER", "DIAGUNDER"}:
        raise ValueError(f"Unsupported family: {table.family}")
    if table.metal < 1 or table.width <= 0:
        raise ValueError(f"Invalid metal/width in {table.table_id}")
    if not table.rows:
        raise ValueError(f"Empty table: {table.table_id}")
    for row in table.rows:
        for key in ("spacing_left", "spacing_right", *TARGET_NAMES):
            if key not in row:
                raise ValueError(f"Missing {key} in {table.table_id}")
        if row["spacing_left"] < 0 or row["spacing_right"] < 0:
            raise ValueError(f"Negative spacing in {table.table_id}")

