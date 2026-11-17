# GitHub delivery scope

Target repository: https://github.com/GRYYYYYYY/residual-gating-capacitance
Delivery branch: revision/dac-cap-main13-integrated
Revision base: b97f90b7d2acd2f06dd7dd9a5f8032001faea422

The commit integrates the completed main13 revision and the existing manuscript
changes/dependencies it builds upon. The single formal manuscript remains
paper/dac_layout_query_revision/main.tex, with its compiled main.pdf, figures,
tables and bibliography. Experiment scripts, frozen protocol, completed run
receipts, per-condition summaries, compact scored records, endpoint tables and
hash manifests are included. Existing Fig.4 Ungated raw evidence is included.

Consistent with the repository's existing artifact policy, large regenerated
SPEFs, getter traces, slot inventories/payloads, neural checkpoints, raw candidate
outputs, generated rule files and detailed layout/path dumps remain on the original
server. Historical manuscript snapshots and temporary build output remain local.
No files were deleted to prepare this delivery. Exact exclusions are in .gitignore;
the integrated experiment manifest retains hashes of the full local outputs,
including files intentionally omitted from Git. A Git clone alone does not supply
all historical datasets, frozen models, OpenROAD builds or physical-design inputs.
See reproduce.md for required dependencies and reproduction modes.

The experimental manifest and final report were sealed before this Git commit.
Their HEAD, committed=false and pushed=false fields describe that historical
experiment-sealing event, not the subsequent delivery status. They are preserved
without rewriting validated hashes. Git history and the remote branch provide the
publication commit identity. The manuscript PDF is unchanged from the checked
final artifact (SHA256 d52fbf3140f287adbd850d0ec8c47ae1d81ec035a88d84f182dfb803667a55a9).
