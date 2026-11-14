#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source experiments/dac_characterization_20261114/env.sh
if [[ ! -f results/layout_offgrid_20261115/query_manifest.jsonl ]]; then
 gzip -dk results/layout_offgrid_20261115/query_manifest.jsonl.gz
fi
mode=${1:---analysis}
case "$mode" in
 --analysis)
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/smoke.py
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/final_checks.py
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/summarize.py
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/plot_workflow.py
  ;;
 --full)
  test -f results/layout_offgrid_20261115/build/receipt.json || python3 experiments/layout_offgrid_20261115/build_trace.py
  python3 experiments/layout_offgrid_20261115/run_native.py
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/census.py
  python3 experiments/layout_offgrid_20261115/contracts.py
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/plan_reference.py
  python3 experiments/layout_offgrid_20261115/reference.py pilot
  python3 experiments/layout_offgrid_20261115/reference.py formal
  python3 experiments/layout_offgrid_20261115/reference.py control
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/native_kernel.py
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/check_api.py
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/evaluate.py native
  "$DAC_PYTHON" experiments/layout_offgrid_20261115/evaluate.py fem
  exec bash experiments/layout_offgrid_20261115/reproduce.sh --analysis
  ;;
 *) echo 'usage: reproduce.sh [--analysis|--full]' >&2; exit 2;;
esac
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd paper/dac_layout_query_revision/main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd paper/dac_layout_query_revision/extended.tex
python3 paper/dac_layout_query_revision/sync_markdown.py
