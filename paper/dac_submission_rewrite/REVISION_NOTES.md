# Revision notes

The manuscript is rewritten as an English method paper, **Observation-Conditioned Capacitance Rule Completion for Parasitic Extraction**, from a fresh IEEE conference structure.

- Restored the same study's fixed-missingness results and method from main. All 15 public/FEM/transfer conditions appear in the main table, with matched Ungated/Binary, source-selected local affine, Anchor, and GP. FEM Full/Binary reduction percentages come from unrounded records.
- Defined the predictor's geometry, context, support and query interface; explained why observed capacitances complement source training, how the anchor and correction bank work, full-grid attention, component gating, exact observation preservation, and native export.
- Kept Full as the complete fusion realization and Binary as a fixed lightweight variant. No result-dependent “Ours” label changes. Fixed-budget MLP, GP, CNP and adapted AttentionCap are visible; native Binary appears in the main figure with all layout conditions and P99 errors.
- Separated mean-mask, pooled-replicate and mean-member/group-balanced aggregation. Fixed-missingness native net-C is seed-mean; WS/TNS are seed-max absolute error. Fixed-budget native values are seed-means. Continued models do not replace source-trained native models.
- Replaced generic chip-flow/waveform drawings with the actual rule-completion/PEX/STA interface and a real table's recorded coverage order. All figures are vector PDFs with regeneration code and CSV/JSON inputs; an additional family/component diagnostic is available outside the self-contained main text.
- Removed branch chronology, internal decision codes, budget administration, closeout language, publication verdicts and stop decisions from the scientific narrative. Important qualification is expressed through experimental definitions and a compact discussion.
- TeX is authoritative. `DAC_REWRITE.md` is generated for synchronized reading. The previous manuscript versions, raw evidence, failure records and scientific conclusions are preserved. This editorial rewrite does not change the global evidence classification or authorize experiments/submission.

## Conference status

Official DAC 2027 requirements were checked on November 14, 2026: IEEE double column, 9/10 pt, at most six body pages and one references-only page, anonymous text and metadata. The source reserves anonymous author-block space and leaves PDF Author empty. Recommended topic: EDA3.6 Parasitic extraction.

Abstract registration closed November 11 at 17:00 PST. Registered abstracts have a full-manuscript deadline of November 18 at 17:00 PST (November 19, 09:00 Beijing). Registration status is unknown here; this draft does not imply that a new abstract can still be registered. No submission was attempted. Official rules: https://dac.com/2027/program/research-manuscript-submissions .

## Final checks

The delivered PDF has six scientific-content pages plus one references-only page, with a 97-word abstract and IEEEtran 10 pt body. All seven pages were rendered and inspected; the method-figure spacing and logarithmic-axis tick labels were corrected. Source synchronization, original fixed-missingness scores, 164 fixed-budget rows, 16 paired native conditions, PDF metadata, embedded font types, references and overfull boxes are checked in `VERIFICATION.json`. Scientific figures and tables use existing measurements only.
