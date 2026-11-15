# 可供正式论文改写使用的段落

这些是文字模板。只保留实际完成的部署和实验，数字从最终未舍入记录生成。

## A. Introduction：定位生产相关插值，而不是损坏表修复

Rule-based parasitic extraction represents a process-dependent capacitance response using a finite set of characterized geometries. Layout-derived widths, spacings, and contexts need not coincide with those characterization nodes. Extraction engines consequently evaluate intermediate geometries through numerical models and precomputed lookup structures. We study this evaluation step while holding the supplied characterization samples fixed.

Our method uses these samples to construct a numerical reference and predict geometry- and component-dependent corrections. The intended deployment prepares the capacitance evaluation table before high-frequency extraction queries, separating learned computation from native lookup and parasitic-network assembly.

第一段可引用现有OpenRCX、Tsai、CNN-Cap文献。第二段中的 intended deployment 在完成真实注入后改为实际过去时/现在时；未实现就保留为设计，不写成结果。

## B. Section II：查询分布作为实测动机

Across two instrumented capacitance getters on eight fixed routed layouts, we record 9,888,586 calls. Of these, 4,547,424 request non-node geometries within the selected width slice and 967,755 fall beyond that slice's characterized range. Together, these requests represent 55.77% of logged calls and 67.16% of finite-distance calls. These measurements motivate accurate non-node rule evaluation. Native width mapping and compute-grid quantization are retained in the evaluator analysis; 849,663 raw non-node requests map to an effective characterization node.

图注明确这两个getter，不说占全部PEX操作/全部线段/全部计算时间的比例。各布局单独结论从CSV重算，不从合计推断。

## C. 基线范围

Our primary comparison targets two specified interpolation kernels used in, or derived from, rule-based PEX: the pinned OpenRCX evaluator and the multidimensional multilinear kernel described for xRC. We distinguish validated kernel reimplementations from measurements of complete commercial tools. General numerical predictors are evaluated separately as component controls to assess the incremental benefit of learned correction and fusion.

若尚无可核验产品来源，将 “described for xRC” 改为 “specified multilinear interpolation kernel”；不要只为品牌效应保留未经验证的归属。OpenRCX在FEM数据上的执行若是harness，要在方法名中说明以FEM规则驱动。

## D. 留出率：不与runtime off-grid比例混淆

The native census quantifies how frequently extraction requests fail to coincide with characterization nodes. Controlled characterization holdout instead varies the amount and spatial coverage of information supplied to the predictor. We therefore evaluate 10%, 30%, 50%, and 70% holdout as a coverage-sensitivity sweep and report actual layout-derived off-grid queries separately. All methods within a condition share the same support and query sets.

## E. AttentionCap适配结果

Under the component-supervised adaptation and observation budget evaluated here, the task-specific estimator achieves lower error than the adapted capacitance-matrix model. This comparison evaluates the selected adaptation recipe for characterized-rule queries; it complements the original model's capacitance-matrix evaluation.

只在对应结果确实成立时写第一句。训练预算差异和输入映射在setup或表注说明一次即可。不能写“field-solver surrogates cannot interpolate”。

## F. 已有运行时间结果的积极、准确表达

In the fixed-node rule-export configuration, learned inference is performed during rule preparation rather than during native extraction queries. Across eight layouts and three repeated release runs per rule variant, the Full-to-original extraction-time ratio ranges from 0.983 to 1.047. Preparing the Full rules for four process libraries at B=8 requires approximately 0.91 s for prediction and export, plus approximately 0.88 s of shared loading and support preparation. SPEF generation and STA are measured separately.

这段对应已完成的fixed-node配置。新computeTable注入后用其实际数据重新生成同结构段落，不将已有数字直接换名。

## G. 两个独立比例的数学定义

运行时频度：
`p_off = N_logged_offgrid_requests / N_logged_requests`。

表征留出率：
`r_hold = (N_reference_nodes - N_retained_nodes) / N_reference_nodes`。

一个完整的11节点表即便没有删除任何节点，也可能收到全在节点之间的10000次查询：此时r_hold=0而p_off=1。两者可同时存在，不能互相替代。

## H. 建议的论文贡献组织

- A characterization-conditioned correction method for non-node capacitance evaluation under fixed supplied samples.
- A compute-table preparation interface that retains native lookup and downstream parasitic assembly（仅在实现完成后作已完成贡献）.
- A production-kernel evaluation connecting controlled coverage, measured layout queries, and extraction-level accuracy/runtime.

不要把“已经用了表中观测”单独当作首次发明；插值本来使用这些数据。重点是修正方法、生产内核接口和实测增益条件。
