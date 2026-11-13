#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source experiments/dac_characterization_20261114/env.sh
case "${1:-verify}" in
  verify)
    "$DAC_PYTHON" experiments/dac_characterization_20261114/final_verify.py
    ;;
  report)
    for script in summarize summarize_downstream plot_architecture plot_gating plot_threshold_cost plot_extra build_report resource_summary; do
      "$DAC_PYTHON" "experiments/dac_characterization_20261114/$script.py"
    done
    (cd paper/dac_revision_20261114 && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex)
    "$DAC_PYTHON" experiments/dac_characterization_20261114/final_verify.py
    ;;
  *)
    echo 'Usage: bash experiments/dac_characterization_20261114/reproduce.sh [verify|report]' >&2
    exit 2
    ;;
esac
