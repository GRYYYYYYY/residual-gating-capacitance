from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonotonicRule:
    """A physically justified one-dimensional trend within an RC table."""

    target: str
    axis: str
    direction: str


# OpenRCX ordinary capacitance tables use one lateral/diagonal distance in
# both spacing columns.  RESOVER is a two-dimensional spacing grid and is not
# assigned a monotonic trend: resistance in the public files is commonly
# constant and ordering arbitrary 2-D points by their coordinate sum would
# create a false physical constraint.
MONOTONIC_REGISTRY: dict[str, tuple[MonotonicRule, ...]] = {
    "RESOVER": (),
    "OVER": (MonotonicRule("coupling_cap", "spacing_left", "nonincreasing"),),
    "UNDER": (MonotonicRule("coupling_cap", "spacing_left", "nonincreasing"),),
    "OVERUNDER": (MonotonicRule("coupling_cap", "spacing_left", "nonincreasing"),),
    # OpenRCX stores diagonal coupling in the ordinary row's ground-cap field.
    "DIAGUNDER": (MonotonicRule("ground_cap", "spacing_left", "nonincreasing"),),
}


def monotonic_rules(family: str) -> tuple[MonotonicRule, ...]:
    try:
        return MONOTONIC_REGISTRY[family]
    except KeyError as exc:
        raise ValueError(f"No physics registry entry for family {family}") from exc


def active_targets(rows: list[dict[str, float]], target_names: tuple[str, ...]) -> tuple[str, ...]:
    """Return targets represented by a table, excluding structural zero columns."""

    return tuple(target for target in target_names if any(abs(row[target]) > 0 for row in rows))
