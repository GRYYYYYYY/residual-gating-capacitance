# Executed entry commands and archived logs

The following entry commands were actually executed from the requested repository,
using `source experiments/dac_characterization_20261114/env.sh` and `$DAC_PYTHON`.
They are an entry-point record, not a suggestion to rerun completed training.
The native and training queues ran concurrently; post-native evaluation waited
for the required completed artifacts. Failed trace parsing was archived and
repaired; successful extraction was reused. Each queue archives its child logs.

```bash
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/coverage_audit.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/supporting_audit.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/budget_paired.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/train_controls.py --queue
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/native_sparse.py all
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/post_native_queue.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/score_candidates.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/final_contract_checks.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/check_candidate_contract.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/summarize_new.py --native --mechanism
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/additional_summaries.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/mechanism_interpretation.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/write_control_findings.py
TEXINPUTS=.:..: latexmk -cd -pdf -interaction=nonstopmode -halt-on-error -recorder paper/dac_layout_query_revision/main.tex
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/validate_paper.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/render_reports.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/verify_originals.py
"$DAC_PYTHON" scripts/dac_main13_integrated_revision/finalize_manifest.py
```

Finalization outcome is in manifest.json, not inferred from this command list.
Top-level stdout/stderr logs are copied to raw/driver_logs. Per-job command/config,
versions, source hashes and final-step checkpoint receipts are retained beneath
native/, controls/ and mechanism/. `reproduce.sh` is the consolidated entry for
summary regeneration, contract rechecking or exclusive-create clean experiments.
PDF review rendered all pages at650px and inspected selected pages at1700px;
the new native figure's repeated axis labels were replaced with one shared label.
Human PDF review is tied to its SHA256 and is not recreated by automatic scripts.
