# Decision

Global: **COMPLETION_ACCURACY_ONLY** (unchanged).
Mechanism: **LIMITED_OR_INCONSISTENT_PROTOCOL_EFFECT**.
Local architecture: **LOCAL_FULL_ADVANTAGE_OBSERVED**.

All12 fixed2000-update endpoints and all256 evaluation cells completed. Mean D Full=0.005066, D binary=0.015766, I=-0.010701, G=0.002939. See all three seeds, conditional group intervals, forgetting and tail tradeoffs in MECHANISM_REPORT.md. No new transfer/solver/native STA evidence. Stop the bounded study; no automatic follow-up.

The aggregate local Full-L advantage must not be read as a B4 advantage: G(B4) is negative in all three seeds. Full D is negative in one seed; I is negative in all three. Low-support training worsens Full at B16/B32 and binary at B32, relative to matched H. The original-support checks also expose retention costs. This does not establish a Full-specific mismatch remedy or justify continuing Full expansion. End this bounded study.
