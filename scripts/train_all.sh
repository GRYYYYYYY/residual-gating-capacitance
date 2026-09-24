#!/usr/bin/env bash
# Launch the stage-2 (gate / joint) training matrix for one stage.
#
# Usage: scripts/train_all.sh <tag>
# Each row initialises the corrective branch from the frozen residual ensemble
# that the DATE-v3 deployment itself uses, so the learned correction starts at
# the archived "Residual" expert instead of being refitted from scratch.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$ROOT"
PY=${PYTHON:-python3}
STAGE=${1:?stage tag required}
STEPS=${STEPS:-1000}
LR=${LR:-0.0005}
TEMP=${TEMP:-0.25}
SCOPES=${SCOPES:-"gate all"}
EXTRA=${EXTRA:-}
cd "$ROOT"

launch () {
  local name=$1 data=$2 init=$3 scales=$4 seed=$5 scope=$6
  if [ -e "runs/$name" ]; then echo "skip existing runs/$name"; return; fi
  PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 nohup "$PY" -m unified.train \
    --data "$data" --output "$name" --scales-from "$scales" --init-from "$init" \
    --train-scope "$scope" --steps "$STEPS" --seed "$seed" --learning-rate "$LR" \
    --temperature "$TEMP" $EXTRA \
    --torch-threads 1 > "logs/train_${name}.log" 2>&1 &
}

for seed in 0 1 2; do
  for scope in $SCOPES; do
    launch "${STAGE}_public_${scope}_s${seed}" \
      "$P/runs/public_inventory_v1/tables.jsonl" \
      "$P/runs/public_study_v1/residual_eta0.01_seed${seed}/checkpoint.pt" \
      "$P/runs/public_study_v1/residual_eta0.01_seed${seed}/checkpoint.pt" "$seed" "$scope"

    launch "${STAGE}_reference_${scope}_s${seed}" \
      "$P/runs/reference_dataset_v2/tables.jsonl" \
      "$P/runs/reference_study_v1/residual_eta0_seed${seed}/checkpoint.pt" \
      "$P/runs/reference_study_v1/residual_eta0_seed${seed}/checkpoint.pt" "$seed" "$scope"

    launch "${STAGE}_to_asap7_${scope}_s${seed}" \
      "$P/runs/reference_transfer_v1/folds/to_asap7.jsonl" \
      "$P/runs/reference_transfer_v1/study_to_asap7/residual_eta0.05_seed${seed}/checkpoint.pt" \
      "$P/runs/reference_transfer_v1/study_to_asap7/residual_eta0.05_seed${seed}/checkpoint.pt" "$seed" "$scope"

    launch "${STAGE}_to_freepdk15_${scope}_s${seed}" \
      "$P/runs/reference_transfer_v1/folds/to_freepdk15.jsonl" \
      "$P/runs/reference_transfer_v1/study_to_freepdk15/residual_eta0.05_seed${seed}/checkpoint.pt" \
      "$P/runs/reference_transfer_v1/study_to_freepdk15/residual_eta0.05_seed${seed}/checkpoint.pt" "$seed" "$scope"
  done
done
wait
echo "training matrix ${STAGE} complete"
