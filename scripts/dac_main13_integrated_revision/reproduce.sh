#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd -- "$script_dir/../.." && pwd)
cd "$repo_dir"
source experiments/dac_characterization_20261114/env.sh
case "${1:---summaries}" in
  --summaries)
    "$DAC_PYTHON" "$script_dir/coverage_audit.py"
    "$DAC_PYTHON" "$script_dir/supporting_audit.py"
    "$DAC_PYTHON" "$script_dir/budget_paired.py"
    "$DAC_PYTHON" "$script_dir/trace_accounting.py"
    "$DAC_PYTHON" "$script_dir/summarize_new.py" --native --mechanism
    "$DAC_PYTHON" "$script_dir/write_control_findings.py"
    "$DAC_PYTHON" "$script_dir/additional_summaries.py"
    "$DAC_PYTHON" "$script_dir/mechanism_interpretation.py"
    ;;
  --verify-contracts)
    "$DAC_PYTHON" "$script_dir/final_contract_checks.py"
    "$DAC_PYTHON" "$script_dir/check_candidate_contract.py"
    ;;
  --clean-experiment)
    if [ -e results/dac_main13_integrated_revision/main13_20261117 ]; then
      echo "Refusing to overwrite experiment. Use a separate checkout with an empty output directory." >&2
      exit 2
    fi
    "$DAC_PYTHON" "$script_dir/coverage_audit.py"
    "$DAC_PYTHON" "$script_dir/supporting_audit.py"
    "$DAC_PYTHON" "$script_dir/budget_paired.py"
    "$DAC_PYTHON" "$script_dir/train_controls.py" --queue > main13-training.log 2>&1 &
    training_pid=$!
    "$DAC_PYTHON" "$script_dir/native_sparse.py" all > main13-native.log 2>&1
    "$DAC_PYTHON" "$script_dir/post_native_queue.py" > main13-post.log 2>&1
    wait "$training_pid"
    "$DAC_PYTHON" "$script_dir/score_candidates.py"
    "$DAC_PYTHON" "$script_dir/final_contract_checks.py"
    "$DAC_PYTHON" "$script_dir/check_candidate_contract.py"
    "$DAC_PYTHON" "$script_dir/summarize_new.py" --native --mechanism
    "$DAC_PYTHON" "$script_dir/write_control_findings.py"
    "$DAC_PYTHON" "$script_dir/additional_summaries.py"
    "$DAC_PYTHON" "$script_dir/mechanism_interpretation.py"
    ;;
  *) echo "Usage: $0 [--summaries|--verify-contracts|--clean-experiment]" >&2; exit 2 ;;
esac
cd "$repo_dir/paper/dac_layout_query_revision"
TEXINPUTS=.:..: latexmk -pdf -interaction=nonstopmode -halt-on-error -recorder main.tex
"$DAC_PYTHON" "$script_dir/validate_paper.py"
"$DAC_PYTHON" "$script_dir/render_reports.py"
"$DAC_PYTHON" "$script_dir/finalize_manifest.py"
