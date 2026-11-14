# DAC 引言素材与文献支持：离散表征下的真实几何查询

核对日期：2026-11-15。本文档供 Codex 改稿使用；文献摘要均为概括，不是原文摘抄。

## 1. 应建立的论证

本文关注的是一个正常提取流程中的数值求值问题：预表征只在有限几何配置处提供参考电容，而实际模式实例不一定命中这些节点。传统求值采用查表、插值或拟合；本文在同一可用表征信息上学习修正。

因此，“离散表存在”不是异常，“读取已有电容”也不是本文独有能力。文章的重点是给定相同表征数据时，怎样估计非采样几何，是否改善直接参考精度，以及怎样进入既有规则提取流程。

文献支持这一问题的重要性；本文自己的布局查询普查负责证明它在所选基准中的实际出现频度。不要让文献代替本工作的运行数据。

## 2. 可直接引用的来源及准确支持位置

### [S1] OpenROAD / OpenRCX 官方运行文档

- BibTeX key：`orcx_runtime`
- 标题：Parasitics Extraction — OpenROAD documentation。
- URL：https://openroad.readthedocs.io/en/latest/main/src/rcx/README.html
- 支持位置：开头的模块说明。
- 已核对内容：OpenRCX 从 routed LEF/DEF/OpenDB 提取 R/C，求值依赖耦合距离和上下层环境；校准规则包含用于求值的测量数据，按工艺与 corner 生成。
- 适合引用在：引言第一段、系统流程图、native baseline 身份说明。
- 边界：这是 OpenRCX 的公开实现依据，不能据此宣称所有商业工具都采用同一种线性插值。文档 latest 的命令与本地固定版本可能不同，实施需检查实际源码。

### [S2] OpenRCX 规则生成官方文档

- BibTeX key：`orcx_calibration`
- 标题：Extraction Rules Generation Flow for OpenRCX。
- URL：https://openroad.readthedocs.io/en/latest/main/src/rcx/doc/calibration.html
- 支持位置：A–D 步骤。
- 已核对内容：生成代表性布局模式，使用参考提取器得到 SPEF，再转换为 RC tech file，并对模式提取结果验证。
- 适合引用在：解释表征样本/规则库的来源，说明规则由校准流程产生，而不统一称“晶圆厂直接交付电容 LUT”。
- 边界：该流程不是本文执行时间、成本节省或新方法优越性的证据。

### [S3] Tsai, Kim and Lim，ICCAD 2025

- BibTeX key：`tsai2025geometry`
- 标题：Capacitance Extraction via Machine Learning with Application to Interconnect Geometry Exploration。
- DOI：10.1109/ICCAD66269.2025.11240935
- 作者公开 PDF：https://gtcad.gatech.edu/www/papers/Tsai-ICCAD25.pdf
- 已检查正文与第 2 页截图；重点位置是 §II-A、Fig.3；截面生成见 §IV-A。
- 支持内容：预表征与布局提取是两个阶段；未匹配查询通过插值等方式估值。实际布局可通过几何变化处分段、截面化得到模式。
- 适合引用在：真实流程、layout-derived query 构造背景。
- 边界：他们的自适应截面算法、层厚探索以及运行数字属于该文。本文未复现时不要写成自己的算法或结果；其方法可以预测未见厚度，不能将其概括为每次变化都必须重训。

### [S4] CNN-Cap，ACM TODAES 2023

- BibTeX key：`yang2023cnncap`
- 作者：Dingcheng Yang, Haoyuan Li, Wenjian Yu, Yuanbo Guo, Wenjie Liang。
- 标题：CNN-Cap: Effective Convolutional Neural Network-based Capacitance Models for Interconnect Capacitance Extraction。
- 卷期：28(4)，Article 56，22 pages；DOI：10.1145/3564931。
- 作者公开 PDF：https://numbda.cs.tsinghua.edu.cn/papers/todaes232.pdf
- 已检查正文与第 2 页截图；支持位置为 §1、第 2 页和 §2.1。
- 支持内容：模式库以场求解样本构建公式或查找表；精度、储存和表征工作量需要权衡；局部结果汇集为网络电容。
- 适合引用在：为何不能只无限加密表征网格，以及电容模型对完整提取的作用。
- 边界：其图像表示、二维/三维模型与本文规则查询接口不同。不要直接拼接不同任务误差或运行时间排名。

### [S5] RMLP-Cap，Electronics 2026

- BibTeX key：`zhou2026rmlpcap`
- 作者：Xinya Zhou, Jiacheng Zhang, Bin Li, Wenchao Liu, Zhaohui Wu, Bing Lu。
- 标题：RMLP-Cap: An End-to-End Parasitic Capacitance Extraction Flow Based on ResMLP。
- 卷期：15(1)，36；DOI：10.3390/electronics15010036。
- 出版社全文：https://www.mdpi.com/2079-9292/15/1/36
- 支持位置：§2.2/Figs.1–2 和 §2.3。
- 支持内容：宽度、间距等参数用于构建公式/LUT；插值近似与几何—电容非线性有关，模式近似和模式覆盖也会影响总误差。
- 适合引用在：引言第二段，明确本文针对规则求值这一误差来源。
- 边界：不能把其特定工业误差要求推广为普遍 signoff 标准，也不能将所有模式匹配误差归为插值。期刊引用年为 2026，在线发布日期为 2025-12-22，BibTeX 使用期刊年。

### [S6] Li and Shi，ISQED 2020

- BibTeX key：`li2020autoprechar`
- 作者：Zhixing Li, Weiping Shi。
- 标题：Layout Capacitance Extraction Using Automatic Pre-Characterization and Machine Learning。
- 页码：457–464；DOI：10.1109/ISQED48828.2020.9136970。
- 出版社：https://ieeexplore.ieee.org/document/9136970/
- 官方议程：https://isqed.org/English/Archives/2020/Technical_Sessions/accepted.html
- 核对程度：出版社摘要可检索，官方议程核对作者；本次未取得完整正文。出版社直接页面可能触发访问验证。
- 摘要支持内容：用样本几何和场求解结果自动形成模式/公式，再训练分类器辅助提取时的模式选择。
- 适合引用在：相关工作中承认预表征自动化与 ML 已有先例。
- 边界：不能凭摘要虚构其损失函数、精细实现或复现实验。

## 3. 英文引言核心段落

下列文字是供本文使用的原创改写。引用 key 与同包 BibTeX 对应。将实验结果段落接在这些动机/方法段落之后，使用已完成证据。

### Paragraph A — Existing workflow

Rule-based parasitic extraction separates process characterization from layout evaluation. Reference capacitances for representative interconnect geometries are encoded in empirical models or lookup tables, and layout extraction evaluates the corresponding models for encountered structures [S3, S4]. OpenRCX provides a concrete example: its extraction rules are calibrated from reference parasitics and are evaluated using coupling distance and surrounding routing context [S1, S2].

### Paragraph B — The numerical problem

A finite set of characterization points does not coincide with every geometric configuration encountered in a routed layout. Between sampled points, the extractor must estimate capacitance using the available rule data. Model-library accuracy therefore depends not only on pattern coverage but also on how the nonlinear geometry–capacitance response is represented between characterization points [S5]. Increasing characterization density can improve that representation, but also increases the amount of reference data that must be generated and stored [S4]. This motivates improving rule evaluation while holding the available characterization samples fixed.

### Paragraph C — Relation to prior modeling

Prior work has automated pattern and formula construction from field-solver samples [S6], developed neural capacitance models [S4, S5], and studied geometry and layer-thickness exploration [S3]. We focus on the complementary problem of estimating uncharacterized queries from a supplied set of process-specific characterization samples. The samples are numerical evidence shared by the interpolators and learned predictors; their use alone is not the distinguishing contribution.

### Paragraph D — This method

We formulate the task as characterization-conditioned capacitance estimation. For a query geometry, a numerical anchor summarizes the available samples, while a shared Transformer predicts residual corrections from geometry, material context, and observed capacitances. Component-wise fusion combines numerical and neural corrections, and a lightweight binary variant retains the same conditioning interface. Learned parameters remain fixed during conditional inference, while changes in the supplied characterization data alter the predictions. The estimator can supply additional rule values for an otherwise unchanged extraction flow.

### Evaluation paragraph — use the version matching completed work

**已有实验可直接支持的版本：**

We evaluate the estimator using controlled characterization subsampling, fixed-support-budget comparisons, cross-process prediction, and native extraction with the generated rule data. Controlled subsampling retains a set of characterized samples and reserves the remaining reference points for evaluation, separating scattered, contiguous, and boundary-directed coverage conditions. Native extraction and timing analysis quantify agreement with the full-rule reference on fixed routed designs.

**只有完成本任务真实查询实验后，才用下列段落替换或补充：**

We additionally collect rule-evaluation queries from routed layouts and distinguish exact-node lookups from in-range off-grid and out-of-support queries. For the physically matched query cohorts, direct field solves provide evaluation references, and every compared predictor uses the same characterization samples and output definitions. This experiment tests the numerical estimator at the geometry queries arising in the extraction workflow, complementing the controlled coverage studies.

若仅完成布局参数模板实验，将第二版中的 physically matched query cohorts 具体写为 layout-parameterized template cohorts，并在设置中说明投影。不能使用未执行实验的结果性语气。

## 4. 文章中建议出现的一段实验解释

“Characterization subsampling is used to control the density and spatial coverage of available rule samples. A 30% holdout reserves 30% of the reference samples as evaluation queries and provides the other 70% to all predictors. These controlled queries are reported separately from the layout-derived off-grid queries, whose coordinates are absent from the original characterization node set.”

这段中的最后一句只在新实验完成时使用。其作用是解释协议，不是暗示工业数据丢失。

## 5. 结果如何支持必要性，而不靠措辞夸大

用布局普查给出 off-grid 查询的真实发生频度和作用范围；用同物理、同 S/Q 的 paired errors 证明精度变化；用实际编码/预测/集成开销说明使用代价。发现与预期相反时仍交付完整结果：少量 off-grid、native 已足够准确、模型适用覆盖不足，都应影响最终主张范围。

引言不需要反复声明“不签核”“不全面”“不首次”。在问题定义中准确限定比较对象，在结果中完整展示方法排名，在讨论中用简短段落说明几何和部署范围即可。

## 6. 引用使用检查

- 参考文献出现在支撑其事实的句子，而非统一堆到引言末尾。
- 不抄录文献段落或照搬图；流程图按本文实际接口重新绘制并引用背景来源。
- 原生插值行为以固定工具版本源码/日志验证，latest 文档负责背景而非版本不变的 API 保证。
- 任何 off-grid 发生率、误差、成本、加速与收益必须来自本文对应实验。
- 不将只确认摘要的文献称为已完整复现。
