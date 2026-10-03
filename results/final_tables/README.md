# Final-paper result tables

CSV exports of the tables presented in the final paper. Values and row order are retained; typographic bold/underline and LaTeX layout commands are omitted. Group headings retain their column spans using empty cells. These are result data, not manuscript sources.

`main_completion.csv`, `main_transfer.csv`, and `main_downstream_compact.csv` correspond to Tables 1–3. `supp_*` contains the presented supplementary results, including negative findings. Raw prediction/error records and validation-selected control configurations are in `experiments/paper_controls/` and the release packages.

Run `python scripts/verify_final_paper.py` to recompute headline/control aggregates and check the Table 1–2 values. `python scripts/reproduce_reports.py --output results/my_reports` exports these CSVs after verification. Add `--sta` to redraw the horizontal spatial figure from recorded data.
