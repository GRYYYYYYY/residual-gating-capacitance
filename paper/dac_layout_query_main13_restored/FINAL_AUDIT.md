# Final manuscript verification

| Deliverable | Verification |
|---|---|
| Baseline and branch | The revision starts at b98f41aa12e06d6c7ce80ed7eb3db6c1f3630a4b on a dedicated worktree and branch revision/capfill-dac-academic. The committed version of this report belongs to the same revision as both PDFs. |
| Scientific definitions | S1–S10 resolved. SCIENTIFIC_CONSISTENCY_REPORT.md maps each issue to code or records. The MLI coverage correction changes the complete-cell fraction from 20.7% to 20.64%. Scores, population and ranking remain those in the archived experiment. |
| Editorial findings | E1–E10 addressed. ACADEMIC_EDITING_REPORT.md records the six-section revision, bibliography and remaining optional metadata update. |
| Main edition | main.tex with method.tex and evaluation.tex. Six figures, two tables, one algorithm and fourteen numbered equations. Six body pages followed by references on page seven. |
| Extended edition | extended.tex selects the shared manuscript, descriptor_detail.tex and extended_evidence.tex. Fifteen pages with absolute results, independent controls and separated timing boundaries. |
| Source package | CapFill-Overleaf.zip contains 36 build inputs. Each entry point was rebuilt in its own empty directory with pdfLaTeX and BibTeX via latexmk. Both extracted texts and all 22 rasterized pages match the delivered PDFs at 100 dpi. |
| Citation, font and page checks | All 17 references are cited. Each key and label resolves. Both PDFs embed all fonts. Both use US Letter and have empty author metadata. Page one contains the anonymous artifact URL. Text bounding boxes are within the page. |
| Visual inspection | The main and extended PDFs were rendered page by page. The workflow diagram, query census, gating equations and algorithm remain legible. The two groups in Table II have distinct headers and units in the note. Dense rows have larger absolute-value counterparts in the technical edition. Review included all supporting tables, spatial maps, the last body page and bibliography. |
| TeX diagnostics | No overfull boxes or undefined citations/references. The technical edition logs one underfull vertical box. TeX substitutes small math sizes in the compact table. Hyperref skips the empty anchor of the unnumbered footnote. Its artifact URL is present as a working PDF link annotation. |
| Empirical scope | Reaggregated coverage, census, endpoint records and release timings. Reused the recorded trained models, FEM references, STA and native validation. The 60 dependent cells support a descriptive default. The smallest margin includes zero in its paired interval. Binary wins on ten fixed-node P99 cells, Anchor wins on full physical support, and the sparse-native comparison against Native-sparse is mixed. |

## Protected inputs

SHA-256 values of the original files were compared with Git blobs at the starting commit.

| Original artifact | SHA-256 |
|---|---|
| Restored main.tex | 10449aa7978d6186d83576645a0b25f5fc9032fa41f86b281caa329a9130a571 |
| Restored main.pdf | 9e8bd2790e1b7613df4f318b08bc5e20a6d68ec4641fddc96e780d1c7e243096 |
| Restored references.bib | 3cbbb2fa749209cc21643c80bf045b101950e4058e0534be1b3d84e1a3844d49 |
| Original Overleaf ZIP | a13a3b1384d65e3db75bcedc6792777fbc7dee2c401225be679142f0f8327842 |
| Legacy extended.tex | e5394f899a3b5ca6e8ae5d02987a911e111c571421819ec026299edcbb4b3cb8 |

## Delivered artifact hashes

| Artifact | SHA-256 |
|---|---|
| main.pdf | c4fca12e4f869d16605edf8bdc6fad8f4e06042579d73a9e0ebb0e288722d313 |
| extended.pdf | b43da80da7448b311ffe1d4c8f8c6ffe1cf2b3dad37c8b03080c0d69adcf8ed6 |
| CapFill-Overleaf.zip | 9c8fc2fdc30d357cde1fb7fcf1048516a87592cdba5515b4091da63f05f797f4 |

Only files under the restored paper directory are included in the revision. Author decisions are limited to the optional future addition of a verified Flash-CNNCap proceedings DOI.
