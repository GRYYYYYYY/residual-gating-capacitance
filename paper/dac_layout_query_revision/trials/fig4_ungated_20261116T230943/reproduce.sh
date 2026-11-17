#!/usr/bin/env bash
set -euo pipefail
trial_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd "$trial_dir/../../../.." && pwd)
cd "$repo_dir"
source experiments/dac_characterization_20261114/env.sh
for domain in public reference to_asap7; do
  "$DAC_PYTHON" "$trial_dir/build_trial.py" --domain "$domain" > "$trial_dir/evaluate_${domain}.log" 2>&1
done
"$DAC_PYTHON" "$trial_dir/build_trial.py" --plot > "$trial_dir/plot.log" 2>&1
cd "$repo_dir/paper/dac_layout_query_revision"
for pass in 1 2; do
  TEXINPUTS="$trial_dir:.:..:" pdflatex -interaction=nonstopmode -halt-on-error -recorder -output-directory="$trial_dir" "$trial_dir/main_ungated.tex" > "$trial_dir/compile_${pass}.log" 2>&1
done
