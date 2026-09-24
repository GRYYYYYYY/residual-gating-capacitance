#!/usr/bin/env bash
# Score a checkpoint set on one validation cohort and print it by regime.
#
# Usage: scripts/eval_val.sh <tag> <domain> <checkpoint...>
# The validation cohort is the only cohort any configuration decision may read,
# so this is the screen every training stage is judged on before the
# confirmation cohorts are opened.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$ROOT"
PY=${PYTHON:-python3}
TAG=${1:?tag required}; DOMAIN=${2:?domain required}; shift 2
cd "$ROOT"
export PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

RUN="val_${TAG}_${DOMAIN}"
if [ ! -f "runs/$RUN/records.jsonl.gz" ]; then
  "$PY" -m unified.score \
    --cohort "$P/runs/round3_validation_inputs_v1/${DOMAIN}_val.jsonl" \
    --checkpoint "$@" --output "$RUN" --method "$TAG" --workers "${WORKERS:-6}" > /dev/null
fi
"$PY" scripts/report_regimes.py --domain "$DOMAIN" --cohort validation \
  --baseline-records "runs/frozen_val_records_${DOMAIN}_v1/records.jsonl.gz" \
  --unified-records "runs/$RUN/records.jsonl.gz" --unified-method "$TAG" \
  --unified-label "$TAG" --ratio "${RATIO:-.3}" ${BOOTSTRAP:+--bootstrap}
