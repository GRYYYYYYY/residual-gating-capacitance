from __future__ import annotations

import hashlib
import random

from .schema import RCTable


def mask_indices(
    table: RCTable,
    protocol: str,
    ratio: float,
    seed: int,
) -> set[int]:
    if not 0 < ratio < 1:
        raise ValueError("Mask ratio must be between zero and one")
    count = len(table.rows)
    target = min(count - 1, max(1, round(count * ratio)))
    stable = int.from_bytes(
        hashlib.sha256(f"{seed}:{table.table_id}:{protocol}:{ratio}".encode()).digest()[:8],
        "big",
    )
    rng = random.Random(stable)
    if protocol == "mcar":
        return set(rng.sample(range(count), target))
    order = sorted(
        range(count),
        key=lambda i: (table.rows[i]["spacing_left"] + table.rows[i]["spacing_right"], i),
    )
    if protocol == "block":
        start = rng.randrange(0, count - target + 1)
        return set(order[start : start + target])
    if protocol == "extrapolation":
        return set(order[-target:])
    raise ValueError(f"Unknown mask protocol: {protocol}")

