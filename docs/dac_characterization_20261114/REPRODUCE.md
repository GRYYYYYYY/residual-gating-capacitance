# Reproduction and recovery

For the delivered local worktree, the runnable entry is:

```bash
bash experiments/dac_characterization_20261114/reproduce.sh verify
# Rebuild derived tables, plots, decision, editable manuscript and PDF from raw records:
bash experiments/dac_characterization_20261114/reproduce.sh report
```

These commands use retained local artifacts. A fresh, bounded prediction replay can reuse verified weights and frozen choices while writing to a new destination:

```bash
source experiments/dac_characterization_20261114/env.sh
"$DAC_PYTHON" experiments/dac_characterization_20261114/evaluate.py \
  --setting public --workers 1 --pilot --out results/dac_replay_unique_name
```

The output directory must not already exist. Omit `--pilot` for the full declared setting. `reference` and `to_asap7` use the same entry. The full source-training sequence below is for a fresh isolated experiment tree with input assets linked, existing delivered results archived elsewhere, and generated MANIFEST/selected JSON files moved into that archive. Do not execute that sequence over the delivered immutable receipts. It is not needed to verify or rebuild the existing study.

Worktree: ../dac-capacitance-20261114 relative to the original repository. Branch: research/dac-capacitance-characterization-20261114. Start with `source experiments/dac_characterization_20261114/env.sh`. This selects local CPU Python with read-only shared dependencies and current-worktree imports. External local paths are explicit in paths.json; change them for another installation and regenerate provenance, without relabeling the result as byte-identical.

For a clean machine use Python 3.10, PyTorch 2.4.0+cpu, NumPy 1.26.4, SciPy 1.14.1, scikit-learn 1.5.2 and repository dependencies. Fetch released database/models/experiment-records/sta-layouts and numerical evidence as in docs/REPRODUCING.md. Local control weights are NOT in the public release: obtain the exact hashed local artifacts or reproduce all 18 using experiments/paper_controls/run_controls.py at the original settings, never reuse scores as predictions. FROZEN/COMPLETED receipts must match. AttentionCap is cloned into .cache/AttentionCap and checked out at 59a48fd1f90e668c061fa27fb22b53ddad3db499.

All new scientific outputs use exclusive creation. Do not delete or overwrite a completed run to rerun a command: choose a new output root and update configuration bindings, or reuse the verified existing receipt. The original runs/ symlink is input-only; every new file belongs under results/dac_characterization_20261114.

Execution order:

```bash
source experiments/dac_characterization_20261114/env.sh
"$DAC_PYTHON" scripts/verify_final_paper.py
# Fresh destination only; audit writes MANIFEST.json exclusively.
"$DAC_PYTHON" experiments/dac_characterization_20261114/audit.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/check_boundary.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/run_registered.py validation
for setting in public reference to_asap7; do
  "$DAC_PYTHON" experiments/dac_characterization_20261114/select_numerical.py "$setting"
done
"$DAC_PYTHON" experiments/dac_characterization_20261114/run_registered.py learning
"$DAC_PYTHON" experiments/dac_characterization_20261114/check_learned.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/run_registered.py confirmation
"$DAC_PYTHON" experiments/dac_characterization_20261114/attention.py --setting reference
"$DAC_PYTHON" experiments/dac_characterization_20261114/attention.py --setting to_asap7
"$DAC_PYTHON" experiments/dac_characterization_20261114/reverse_transfer.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/cost_index.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/downstream.py --export
"$DAC_PYTHON" experiments/dac_characterization_20261114/downstream.py --pilot --case ihp-sg13g2/aes
"$DAC_PYTHON" experiments/dac_characterization_20261114/downstream.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/check_export_alignment.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/member_check.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/summarize.py
"$DAC_PYTHON" experiments/dac_characterization_20261114/summarize_downstream.py
```

The sequence is intentionally serial as written; do not start multiple queue scripts simultaneously without respecting the global four-job CPU ceiling. Each queue has one owner and job timeout. Native extraction uses existing OpenROAD 26Q3-1860-g0b54bb3203, the same connected ODB/SDC/Liberty set as the released replay, and the original extract_parasitics arguments. Each native invocation has a 300-second timeout. A full-rule replay must reproduce both C and R exactly before that layout's budget results are accepted. New endpoint times are converted from reported native units to ns; SPEF net capacitance units remain explicitly reported.

Analysis scripts are deterministic and may regenerate their derived summary/figure directory. Raw records, code hashes, checkpoints, original solver receipts, failed diagnostics and input hashes are immutable. The paired bootstrap groups all repeated seeds/points within the same dependency group; FEM layers cross families, so groups are sampled within process, preserving their families together. This clarification avoids breaking the physical dependency group to enforce family stratification. It does not quantify uncertainty over new process technologies.

Costs: geometry_cost_index.csv links every FEM row to fine/coarse/wide ledger entries, original CPU seconds and excitation counts. cost_ledger.csv joins support purchases to these records; cached charged_wall_seconds is never used as characterization time. Fine-only and validated costs are not interchangeable. Prediction/adaptation timings include all work within that call; incremental selection is measured, initial population setup and one-time model loading are separately excluded and not silently treated as a measured end-to-end total. Source-only controls consume zero labels for Q prediction even when displayed against the common evaluation-support budget; their effective query charge is zero in the final cost ledger. They are not used as equal-information superiority baselines.

For native parallel replay, `native_parallel.py` owns up to two disjoint cases and reuses existing complete receipts. Never run it concurrently with the serial all-case owner. The one historical administrative handoff is fully recorded; do not run finalize_handoff.py again (its process IDs are historical). Public confirmation uses direct calls for workers=1 after a retained fork-execution failure. Stack inspection was host-denied, so the exact runtime cause remains unverified; no numeric model changes were made.

After fresh experiments, run `charge_ledger.py`, `profile_components.py`, `plot_threshold_cost.py`, `plot_extra.py`, `native_manifest.py`, `resource_summary.py`, `build_report.py`, then compile `paper/dac_revision_20261114/main.tex` with latexmk and run `final_verify.py`. Analysis plots and manuscripts can be rebuilt without rerunning any learning or native extraction. The complete native local files (SPEF, endpoints, paths, inputs, logs, receipts) are indexed by `summary/native_artifact_manifest.json`; they and new model weights are preserved locally but excluded from Git. Raw compressed evaluation records, cost CSVs, compact native summaries, frozen configurations, scientific figures and the editable paper are versioned. `DELIVERY_MANIFEST.json` also indexes local binaries and export rules. Local absolute paths must be rebound for another installation; no remote upload is implicit.
