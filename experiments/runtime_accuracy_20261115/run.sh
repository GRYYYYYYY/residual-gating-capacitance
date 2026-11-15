#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
source experiments/dac_characterization_20261114/env.sh
export RUNTIME_CPU=${RUNTIME_CPU:-24}
out=results/runtime_accuracy_20261115
mkdir -p "$out"
for packed in "$out"/*.csv.gz "$out"/*.jsonl.gz; do
  [[ ! -f "$packed" || -f "${packed%.gz}" ]] || gzip -dk "$packed"
done
if [[ ${1:---analysis} == --full ]]; then
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/freeze.py
  # Intentionally sequential: do not overlap benchmarks with each other.
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/benchmark.py fem > "$out/fem.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/verify_attention.py > "$out/attention.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/benchmark.py native > "$out/native.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/cached_query.py > "$out/cached_query.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/native_kernel.py > "$out/kernel.log" 2>&1
  env LD_LIBRARY_PATH=/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/process-adapt-v3/local/sysroot/usr/lib/x86_64-linux-gnu \
    /inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/pdkcap-v0/local/venv/bin/python \
    experiments/runtime_accuracy_20261115/solver.py > "$out/solver.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/native_flow.py prepare > "$out/rule_prepare.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/native_flow.py native > "$out/native_flow.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/cold_load.py > "$out/cold_load.log" 2>&1
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/complete_metadata.py
  "$DAC_PYTHON" experiments/runtime_accuracy_20261115/source_costs.py
fi
"$DAC_PYTHON" experiments/runtime_accuracy_20261115/parse_sta.py
"$DAC_PYTHON" experiments/runtime_accuracy_20261115/summarize.py
"$DAC_PYTHON" experiments/runtime_accuracy_20261115/final_checks.py
"$DAC_PYTHON" experiments/runtime_accuracy_20261115/update_paper.py
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd paper/dac_layout_query_revision/main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd paper/dac_layout_query_revision/extended.tex
python3 paper/dac_layout_query_revision/sync_markdown.py
"$DAC_PYTHON" experiments/runtime_accuracy_20261115/report.py
