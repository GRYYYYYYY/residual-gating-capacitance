#!/usr/bin/env bash
# Score one frozen configuration on every domain: validation first, then the
# confirmation and boundary cohorts of that domain.
#
# Usage: scripts/score_domains.sh <stage> <scope> <cohorts>
#   stage    training-run prefix, e.g. v4  -> runs/v4_public_all_s0/checkpoint.pt
#   scope    gate | all | gate_head
#   cohorts  val | confirm | all
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$ROOT"
PY=${PYTHON:-python3}
STAGE=${1:?stage required}
SCOPE=${2:?scope required}
COHORTS=${3:-all}
WORKERS=${WORKERS:-40}
cd "$ROOT"

checkpoints () {
  local domain=$1
  echo "runs/${STAGE}_${domain}_${SCOPE}_s0/checkpoint.pt runs/${STAGE}_${domain}_${SCOPE}_s1/checkpoint.pt runs/${STAGE}_${domain}_${SCOPE}_s2/checkpoint.pt"
}

score_one () {
  local domain=$1 cohort=$2 source=$3
  local name="${domain}_${cohort}_${STAGE}_${SCOPE}"
  if [ -e "runs/$name" ]; then echo "skip existing runs/$name"; return; fi
  PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 "$PY" -m unified.score \
    --cohort "$source" --checkpoint $(checkpoints "$domain") \
    --output "$name" --method "sace_r_${STAGE}_${SCOPE}" --workers "$WORKERS" \
    > "logs/score_${name}.log" 2>&1
  echo "scored $name"
}

for domain in public reference to_asap7; do
  if [ "$COHORTS" = val ] || [ "$COHORTS" = all ]; then
    score_one "$domain" val "$P/runs/round3_validation_inputs_v1/${domain}_val.jsonl"
  fi
  if [ "$COHORTS" = confirm ] || [ "$COHORTS" = all ]; then
    # The public domain has no boundary cohort; its only registered cohort is
    # the retrospective test split.
    if [ "$domain" = public ]; then
      score_one "$domain" confirmation "$P/runs/round3_evaluation_inputs_v1/public_retrospective_original.jsonl"
    else
      score_one "$domain" confirmation "$P/runs/round3_evaluation_inputs_v1/${domain}_confirmation_round3_main.jsonl"
      score_one "$domain" boundary "$P/runs/round3_evaluation_inputs_v1/${domain}_boundary_round3_edge.jsonl"
    fi
  fi
done
echo "scoring ${STAGE}/${SCOPE} complete"
