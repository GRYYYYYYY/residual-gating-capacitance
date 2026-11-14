# Paper delta: evidence-limited editable wording

The original manuscript remains at paper/dac_revision_20261114. A separate version is generated at paper/dac_support_revision_20261114. No experimental result, model ranking, cost threshold or global decision is changed.

## Abstract addition

“Training-support mismatch remains an unresolved explanation rather than an established source of the observed performance differences.”

Evidence: existing REVIEW_PACKET §5 establishes the setting mismatch; EXECUTION_STATUS.json and EFFECTS_BY_SEED.csv show no completed matched continuation. This sentence expresses an evidentiary limit, not a mechanism finding.

## Contribution / protocol paragraph

“The FEM models were trained on 153-node tables with 46, 77, 107 or 138 observed nodes under the missing-point protocols, or 136 under whole-width holdout. Thus the four low-budget evaluation conditions lie below the original support-count range. A paired continuation could distinguish extra optimization from a change in support protocol by holding the loss queries and family weights fixed while thinning the original supports. Such thinning also changes coverage, so it would not isolate cardinality alone.”

Sentence 1–2: old REVIEW_PACKET §5, source FROZEN configurations, new CHECKPOINT_LINEAGE and SUPPORT_QUERY_COUNTS. Sentence 3: proposed design only, not completed evidence. Sentence 4: PROTOCOL_DIFF and explicit nested-support definition.

## Limitations paragraph

“A bounded attempt to construct this matched continuation stopped during preflight after exhausting its single permitted implementation repair. No continuation endpoint or matched endpoint evaluation was completed. The failure concerned the new audit harness, including comparison of unavailable analytic-basis entries represented by NaN, and provides no evidence for or against a low-support training effect. We therefore retain the existing completion-accuracy-only conclusion and make no new claim about architectural necessity, characterization efficiency, transfer, or downstream timing fidelity.”

Sentence 1: failed ledger rows and invalid_prepare/DIAGNOSIS. Sentence 2: ENDPOINT_STATUS, header-only EVALUATION_CELLS. Sentence 3: FAILURE_DIAGNOSIS (all first-step finite entries/masks/NaN locations match). Sentence 4: original FINAL_DECISION; no new experimental outcomes. Do not replace this language with “low-budget training had no effect.”

## Claim disposition

Keep the bounded completion and native-interface results. Remove/continue withholding universal Full necessity, whole-process characterization efficiency and signoff claims. The support-count mismatch is established as a configuration fact, not a demonstrated cause. End this run and do not continue Full expansion automatically. No new architecture-value signal was measured, and no new acceptance/submission-readiness claim is warranted.
