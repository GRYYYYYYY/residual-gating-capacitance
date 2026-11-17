# Fixed-budget grouped bars

The archived `source_table.tex` contains the complete former Table II.
The plot uses its exact four-decimal values for CNP, Adapted AC and Full,
excluding Binary and Ungated from this figure only. No experiments are rerun.
`plotted_values.csv` retains all 34 plotted values and two explicitly unavailable
Public/AC entries. Public B=16/32/64 are infeasible/unavailable and not plotted.
The three panels share a labeled logarithmic NRMSE axis; bars start at the visible
0.01 floor. Missing values are never represented as zero-height bars.

From the repository root:

```bash
source experiments/dac_characterization_20261114/env.sh
"$DAC_PYTHON" paper/dac_layout_query_revision/plot_fixed_budget_controls.py
```

This writes the editable-data CSV, verification receipt, and vector PDF/PNG figure.
LaTeX references number the new chart automatically; the downstream spatial plot
retains its single-column 2-by-4 layout and follows the new chart.
