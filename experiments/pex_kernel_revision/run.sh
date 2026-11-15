#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
source experiments/dac_characterization_20261114/env.sh
out=results/pex_kernel_revision
mkdir -p "$out"
case "${1:---analysis}" in
 --full)
  "$DAC_PYTHON" experiments/pex_kernel_revision/freeze_contracts.py
  "$DAC_PYTHON" experiments/pex_kernel_revision/build_native.py > "$out/build_launcher.log" 2>&1
  "$DAC_PYTHON" experiments/pex_kernel_revision/extract_harness.py
  "$DAC_PYTHON" experiments/pex_kernel_revision/test_kernels.py
  "$DAC_PYTHON" experiments/pex_kernel_revision/validate_extracted.py
  for domain in public reference to_asap7; do
   "$DAC_PYTHON" experiments/pex_kernel_revision/coverage.py "$domain" > "$out/coverage_${domain}.log" 2>&1
  done
  "$DAC_PYTHON" experiments/pex_kernel_revision/physical.py > "$out/physical.log" 2>&1
  for phase in inventory prepare validate benchmark; do
   "$DAC_PYTHON" experiments/pex_kernel_revision/native_flow.py "$phase" > "$out/${phase}.log" 2>&1
  done
 ;;
 --analysis) ;;
 *) echo 'usage: run.sh [--analysis|--full]' >&2;exit 2;;
esac
"$DAC_PYTHON" experiments/pex_kernel_revision/census.py
"$DAC_PYTHON" experiments/pex_kernel_revision/draw_interface.py
"$DAC_PYTHON" experiments/pex_kernel_revision/component_analysis.py
"$DAC_PYTHON" experiments/pex_kernel_revision/summarize.py
"$DAC_PYTHON" experiments/pex_kernel_revision/check_coverage.py
if [[ -x "$out/pinned_kernel" ]]; then "$DAC_PYTHON" experiments/pex_kernel_revision/check_harness_retrieval.py; fi
"$DAC_PYTHON" experiments/pex_kernel_revision/update_paper.py
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd paper/dac_layout_query_revision/main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd paper/dac_layout_query_revision/extended.tex
python3 paper/dac_layout_query_revision/sync_markdown.py
"$DAC_PYTHON" experiments/pex_kernel_revision/finalize.py
