# Sole manuscript source

DAC_REWRITE.md is the authoritative editable body. Run `python3 render.py` in this directory to regenerate main.tex; compile main.tex with pdflatex twice. Do not edit TeX independently. build.py reconstructs derived CSVs/figure and the initial editorial manuscript from pinned existing inputs; rerunning it replaces local editorial edits, so render.py is the normal workflow after editing Markdown.

From the repository root, source experiments/dac_characterization_20261114/env.sh and use $DAC_PYTHON for build.py (pandas, NumPy and Matplotlib required). No torch/model/solver/native tools are imported or invoked. Native full-layout data are in native_all_layouts_all_metrics.csv; the much larger prior archives remain in their original locations. INPUT_SHA256.json records original sources and CHECKS.json records deterministic numerical checks. The external completeness of referenced checkpoints/datasets is not asserted.
