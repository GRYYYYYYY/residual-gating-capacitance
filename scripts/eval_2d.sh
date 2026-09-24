#!/usr/bin/env bash
# Score a candidate on a small 2-D cohort and print its cells next to the ones
# already recorded for the current best configuration.
#
# Usage: scripts/eval_2d.sh <tag> <domain> <cohort:val|conf> <checkpoint dir prefix>
# The checkpoint prefix names the stage tag; the three seed directories under it
# are the ensemble.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$ROOT"
PY=${PYTHON:-python3}
cd "$ROOT"
export PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

TAG=${1:?tag}; DOMAIN=${2:?domain}; KIND=${3:?val or conf}; STAGE=${4:?stage prefix}
if [ "$KIND" = val ]; then
  COHORT="$P/runs/round3_validation_inputs_v1/${DOMAIN}_val.jsonl"
else
  COHORT="$P/runs/round3_evaluation_inputs_v1/${DOMAIN}_confirmation_round3_main.jsonl"
fi
OUT="${KIND}_${TAG}_${DOMAIN}"
if [ ! -f "runs/$OUT/records.jsonl.gz" ]; then
  "$PY" -m unified.score --cohort "$COHORT" \
    --checkpoint "runs/${STAGE}_s0/checkpoint.pt" "runs/${STAGE}_s1/checkpoint.pt" \
                 "runs/${STAGE}_s2/checkpoint.pt" \
    --output "$OUT" --method "$TAG" --workers "${WORKERS:-10}"
fi
"$PY" scripts/cell_report.py --records "runs/$OUT/records.jsonl.gz" --method "$TAG" --label "$TAG"
