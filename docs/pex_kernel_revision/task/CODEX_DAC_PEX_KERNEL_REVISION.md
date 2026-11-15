# Codex 任务书：面向生产 PEX 插值内核的论文重构与计算表回填验证

## 0. 任务目标与接续位置

仓库：`GRYYYYYYY/residual-gating-capacitance`
研究分支：`research/dac-capacitance-characterization-20261114`
本任务核对的参考提交：`a519539fee8a763c74e1db61427fdd02d85511ca`
服务器项目目录：
`/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114`
论文目录：`paper/dac_layout_query_revision/`，包括 `main.tex/main.pdf` 与 `extended.tex/extended.pdf`。

先核对实际 HEAD、工作区和后续成果；若已更新，保留并检查差异，不 reset。遵守现有项目指令。不要改动 main 分支、原始数据、已完成结果和原模型权重。使用独立 worktree 或研究分支上的新提交，避免与正在执行的任务冲突。

本轮目标是把论文明确组织为：

> 在相同预表征样本、相同模式和物理定义下，改进 PEX 的非表征节点求值；将学习预测放在计算表准备阶段，保持原生查询与寄生网络装配路径，联合评价精度和整个提取流程开销。

这里的“点”是几何查询，不是 FEM 网格节点。`off-grid` 指未命中原始表征节点，不自动等于超出表征范围。主工作不再描述为修复损坏的 PDK 文件。

必须交付正式英文论文及可编译 PDF，不以研究审计或停止决定代替论文。main 与研究分支上的有效实验均属于同一项工作，按实验设置命名，不使用 historical/legacy/closeout 等版本性标签描述科学结果。

本次明确授权的执行范围：文稿与图表重构；两类生产插值内核核验/实现；已有数据的必要重评分；有限的内部计算表回填和原生 PEX/STA 验证；对应运行时间测量。不自动开展新架构大搜索、商业工具整套逆向或大规模场求解。

## 1. 用户六点建议的落实原则

### 1.1 主比较采用两类生产相关插值内核

- OpenRCX 固定版本的实际有限距离求值内核，或经过原生逐点验证的复现。
- 按用户提供的 xRC 核心公式实现的多线性插值；具备相应验证证据后命名为 `xRC-derived interpolation kernel (reimplementation)`。
- 这不是 Calibre xRC 商业二进制与 OpenRCX 全流程的直接产品对比。基线名称、表注、计时定义均须反映实际执行对象。

### 1.2 通用数值方法不再挤占生产主对照表

将 Anchor、GP、局部仿射、PCHIP、IDW 等归入“组件贡献与数值候选分析”，但保留它们已经完成的有效结果。正文保留一个紧凑的 numerical-only 对照，至少包括实际 anchor 和验证集确定的强数值候选；完整结果放扩展稿。

不能因某方法优于 Full 而删除。对已经进入融合字典的 PCHIP、GP，可以自然作为组件控制；没有实际纳入算法的局部仿射/IDW 不得直接改名成消融结果。

### 1.3 保留学习模型的任务适配比较

保留 adapted AttentionCap、MLP、CNP 等，说明在本文的输入接口、表征支持和训练机会下的表现。不要从适配实验推出“原方法不能用于插值”或“不能同时替代求解器与插值”。CNP 本身就是条件回归对照，不应归类为场求解替代器。

### 1.4 运行时间结论由实际部署测量支撑

复用本提交已有 runtime 结果。固定节点规则回填与直接 computeTable 回填要区分，不能将已测前者直接写成后者已经实现。

### 1.5 将真实查询分布前移到 Section II

移动 `fig: census`（实际标签 `fig:census`）及简洁统计到 II. Problem and Related Work，作为应用动机的实测证据。使用 LaTeX label/ref，不硬编码“Fig.5”。详细插桩范围、验证日志与完整按布局结果放实验设置或扩展稿。

### 1.6 全部留出率完整呈现

保留 10%、30%、50%、70%。不按效果好坏选删 10%。若篇幅需要，使用相同规则将某类细节全部移至扩展稿；不得根据胜负决定去留。

真实查询的 off-grid 比例与表征样本留出率是不同统计量。前者证明研究环节频繁被使用；后者是覆盖敏感性实验，不能用 55.77%/67.16% 直接校准 30%/50%/70%。

## 2. 既有证据：本轮必须接续，不重复或改名

在参考提交中核对到：

1. 两个 getter 共记录 9,888,586 次调用、19,562 个唯一规则/几何键；on-grid 2,696,515，off-grid in-support 4,547,424，off-grid out-of-support 967,755，fringe/special 1,676,892。
2. raw off-grid 占全部上述调用 55.77%，占有限距离调用 67.16%；849,663 次 raw off-grid 在映射/量化后落到有效表征节点。
3. 查询统计不覆盖全部提取操作、所有对角 getter、电阻及后续网络装配。其权重为调用次数，不是线长、电容贡献或运行时间。
4. 71 个布局参数化模板、每个上下文完整 153 个支持样本的独立 FEM 比较中，Anchor/Full/Binary NRMSE 约为 0.00451/0.01675/0.02218。该结果必须保留，并与覆盖不足的受控子采样结果区分。
5. 当前原生校准数据与 FEM 模板的物理定义并未完成整体对齐。因此 `native agreement` 不等于独立物理精度。
6. 最新 runtime 实验已经完成：20 个随机顺序计时块、三次预热、Q 上限 1/8/32 分别评价精度；Full/Binary/Anchor 的 warm 摊销值约 3.706/2.110/0.788 ms/query；Full 单请求均值约 40.97 ms。
7. 96 次 release 原生运行（8 布局×4 规则变体×3 次），Full 固定节点导出后的 extraction/original 比值 0.983–1.047。四库 B8、seed11 的 CMI/Binary/Full 预测导出约 0.70/0.67/0.91 s，另有约 0.88 s 共同准备。使用未舍入原记录重新生成表。
8. 适配模型应在固定支持上拟合一次后复用；已有 runtime 已处理这一点，不重新把拟合计入每次 warm 查询。

入口优先检查：
- `paper/dac_layout_query_revision/main.tex`
- `paper/dac_layout_query_revision/extended.tex`
- `paper/dac_layout_query_revision/tables/offgrid_runtime.tex`
- `docs/layout_offgrid_20261115/NATIVE_CALLMAP.md`
- `experiments/layout_offgrid_20261115/native_kernel.py`
- `experiments/layout_offgrid_20261115/evaluate.py`
- `results/layout_offgrid_20261115/query_census.csv`
- `results/layout_offgrid_20261115/census_summary.json`
- `unified/cmi.py`, `unified/basis.py`, `unified/queries.py`
- 从当前稿件的运行时图表生成脚本与证据映射定位最新 runtime 原始 CSV；不要猜测路径后制造新文件替代。

## 3. P0：冻结基线合同与科学命名

首先交付一个简短、可机器读取的 `baseline_contracts.json`，明确：
- 方法 ID 与论文名；
- 版本/源码提交/核验依据；
- 实际执行是原生、提取的开源内核，还是数学重实现；
- 输入轴、单位、rank、输出分量和单位；
- 支持值来源、表结构、角点缺失策略；
- 宽度选择、边界、特殊值、量化、精确节点处理；
- 能评价的数据域和排除原因；
- 原生一致性验证范围。

基线建议固定为：

| ID | 建议名称 | 条件 |
|---|---|---|
| `openrcx_native` | OpenRCX native evaluator | 真正调用固定版本代码，说明已含的上下文/宽度步骤 |
| `openrcx_kernel` | OpenRCX kernel / native-validated reproduction | 逐点核验；说明有限距离、特殊尾部等范围 |
| `xrc_mli` | xRC-derived multilinear kernel (reimplementation) | 用户提供的核心规范，加可用的来源与单元测试 |
| `mli` | Multilinear interpolation (specified kernel) | 只有公式，尚不足以完成产品来源或边界核验时的默认公开名 |
| `full` / `binary` | Full / Binary | 原始算法身份固定 |
| `numerical_only` | Numerical-only control | 验证集冻结的候选或选择规则，不按测试真值挑最佳 |

不要求对所有商业产品做比较。范围表述为“两个可明确规定/验证的生产相关插值内核”。不要用“xACT 与 StarRC 都是纯场求解器”作为排除理由：xACT 有混合路径，StarRC 有规则/模式路径和 Rapid3D 路径。本轮可以不测试它们，但应准确说明只研究已指定内核。

对于 Calibre 来源：用户已给出其核对源码后的数学规范。可据此实现，不要求公开或复制专有源码；只在项目中使用用户有权使用的信息。若本地存在授权可检查的版本、函数说明和测试样例，记录其适用范围。没有商业执行结果就不写“Calibre xRC 实测耗时/精度”。

## 4. P1：实现与验证两个插值内核

### 4.1 xRC-derived 多线性内核

使用用户提供的数学定义：

1D：`v=(1-t)*v0+t*v1`，`t=(x-x0)/(x1-x0)`。

2D：令 v00、v10、v11、v01 分别对应 (x0,y0)、(x1,y0)、(x1,y1)、(x0,y1)，则
`v=(1-t)*(1-u)*v00+t*(1-u)*v10+t*u*v11+(1-t)*u*v01`。

一般 d 维：
`v(x)=sum_{epsilon in {0,1}^d} v_epsilon * product_j [t_j if epsilon_j else (1-t_j)]`。
4D 使用 16 顶点。记录每一轴物理语义和有效维度，不将重复/常量坐标算作独立维度。

测试必须覆盖：
- 节点精确值、端点、常数函数、仿射函数；
- 多线性混合项如 x*y、x1*x2*x3*x4，不只测试纯仿射；
- 非均匀轴、顶点顺序、各向异性尺度、组件向量；
- 重复/退化轴、越界与缺角点：分别按照已核实规范或显式扩展处理；
- 不同浮点精度与单位换算；记录容差及误差分布。

重要：当前 `unified/cmi.py` 在掩码网格上还包含跨节点括区、缺角点轴向插值及最近节点回退。这不是由上述 1D/2D/4D 核心公式自动确定的产品语义。因此：
- 不把当前所有 CMI 分数直接改名为 Calibre xRC；
- 将完整角点的标准算子和稀疏支持扩展策略分开记录；
- 不知道原生边界策略时不猜测；范围外结果按“显式边界规则扩展”命名；
- 重新命名之前用实际执行结果验证同值。

当前物理数据的 rank 为 1/2，4D 只交付实现一致性测试；没有真实四维数据就不加虚构 4D 提取结果。

### 4.2 OpenRCX 内核

固定 OpenROAD `0b54bb3203e0895f87940ff982358a6e4d406e28` 或明确记录更新后的版本。检查：
- `extDistRC::interpolate` / `lineSegment`；
- `extDistRCTable::mapInterpolate`、computeTable 构建；
- `getWidthIndex`、`getComputeRC`、边界和特殊尾部；
- 单位缩放与 coupling/fringe 等字段。

保留三个层次：
1. 纯浮点线性距离核；
2. 含离散 compute-grid 和边界行为的求值核；
3. 含模式/宽度匹配及后续装配的原生提取。

核 1 的公式相同不代表核 2 或整个流程相同。已有 `OpenRCX-style LI` 可能执行额外的宽度线性混合，不得直接改名为 native。

利用现有 trace 验证，继续保留不同特殊值路径的适用范围。内核匹配成功说明实现等价，不证明其物理准确。

### 4.3 物理精度比较：用同一批 FEM 支持值驱动两种内核

本轮的建设性重点是“抽出求值算法”，而不是强迫将不同 PDK 规则与 FEM 混成同一真值：

- 在能够表达的规则结构中，把相同 FEM 表征几何和组件数值送给 MLI 与 OpenRCX 求值核。
- Full/Binary 读取同一支持集；查询标签由独立参考给出。
- OpenRCX 的宽度映射和量化保留为算法的一部分；同时报告未量化理想线性核作为实现分解。
- 明确命名 `OpenRCX kernel with FEM-characterized rules`，而不是“原生 ASAP7 PDK 对场求解器的精度”。
- 若只能映射部分几何或组件，先按几何/语义条件冻结共同集合，再评分；所有方法使用相同集合，完整覆盖统计保留。
- 不能把两侧耦合之和与单侧耦合、ground 与 fringe、F/m 与 fF/um 混用。若线性内核只是对标量投影求值，应明确该投影及规则封装，不假称完整商业物理语义一致。

此方式能建立“同样的物理参考、不同生产插值算法”的公平比较，同时保留原实际 PDK 的原生部署证据。

## 5. P2：两条实验线与全部留出率

### 5.1 真实非网格查询（生产场景主证据）

输入实际布局查询、未修改的表征支持、固定上下文。主比较为两个生产相关内核与固定版本 Full/Binary；独立 FEM/可信参考只作真值，不作为主插值竞争算法。

区分：
- 原始支持节点命中；
- 未命中节点但在支持内部；
- 支持外、仍有兼容模式；
- 特殊/不兼容查询；
- raw off-grid 经原生量化后命中节点。

不得把现有 480 个 native-return 一致性样本当独立物理真值。保留 71 个模板样本的真实精度结果，不将其说成完整真实截面。

### 5.2 受控表征覆盖敏感性（全部四档）

恢复并重新生成 `10/30/50/70%` 的有效全部数据。优先读取已有预测/累积量，不重训。缺少新生产基线的分数时，仅补必要推理或内核运行。

- 同一 (表、协议、留出率、seed) 的所有方法必须使用相同 S/Q。
- 记录请求比例、实际保留数量、实际 Q 数量、有效 rank 与 inside/outside 分类。
- 小表四舍五入导致不同比例/协议得到同一 S/Q 时，标记重复，不作为独立证据。
- 不同留出率若 Q 不同，不把曲线误差变化直接解释为“增加观测点的因果收益”；固定 Q 的预算实验继续单独保留。
- 主图四档全部出现；支持完整结果的扩展表同时输出。

### 5.3 处理多维随机遮蔽导致缺角点的问题

工业多线性算子要求所用 cell 的顶点值。对于原随机/块状 mask：
- 共同完整 cell 上可直接比较原生核心公式，报告覆盖率。
- 对不完整 cell，使用显式的共享支持补全/回退协议，并将结果称为 sparse-support extension；不能把扩展部分归因于 xRC。
- 不允许某方法靠跳过困难查询改善分数。若采用共同可行子集，选择规则在看误差前冻结，并同时报告全量覆盖及 fallback 结果。
- 可增加一个小型张量积子网格 coarsening 检查，保证每个被查询的内部 cell 都有完整角点。各轴保留规则只由坐标决定，报告实际实现的留出率，不凑成虚假的精确 10/30/50/70%。这是补充协议，不覆盖或删除已有 mask 实验。

## 6. P3：落实内部计算表回填，而不是只更改论文用语

用户希望的部署是：

`表征样本 → 更准确的内部计算表生成 → 原有 getter 查表 → 原有 RC 装配 → SPEF/STA`。

这与“把隐藏的原始表征节点写回规则文件”有关但不同。优先复用现有原生 build 和 tracing 代码，新增明确、可关闭的 computeTable 注入路径。

### 6.1 冻结注入契约

- 明确插入位置位于原生 computeTable 的构建/加载之后、生产 getter 使用之前。
- 先仅覆盖已核对的有限距离路径；其他特殊/不适用路径保留原值并计数。
- 每个缓存项键包含工艺角、pattern family、上下层索引、映射宽度、实际有效 separation/index、输出组件、单位和配置哈希。
- 不能只按 raw spacing 当键。不同请求可能映射同一 slot；按该 slot 实际表示的坐标预测一个确定值。
- 保留源表征节点、原始 measureTable、resistance、特殊哨兵、原生返回位置和装配逻辑。
- 审查原生在边界处直接返回 measureTable 的路径，不能宣称只替换 computeTable 就影响了所有 out-of-support 查询。
- 若一个 slot 与必须保留的表征点发生量化冲突，按预先确定的规则保留原值或排除该 slot，报告数量，不能覆盖真值来迎合预测。

### 6.2 查询批次与缓存生成

模型有 query–query 依赖。为整表生成定义一个规范化、确定性的 Q 集合和分块策略，保存哈希。

- 不假设支持隐藏状态可缓存；已有验证说明其依赖 Q。
- 改变分块、canonicalization、精度或加速实现后重新测相应预测精度。
- 同一次准备中 S 固定为真实表征值；不能把已预测值继续当真实支持喂回模型。
- 优先按规则的有限 compute-grid 整体准备，使缓存不依赖当前设计。
- 如果实际只准备布局将访问的 slots，则称 design-specific preparation，计入查询发现/追踪成本；不能假称同一工艺全设计通用缓存。
- 不使用测试参考值决定缓存中选 Full、GP 还是 Anchor。任何选择规则仅由源验证数据决定。

### 6.3 必须实施的三类版本

A. 未修改原生版本。
B. 通过相同注入接口回填原生数值结果的 pass-through 版本。
C. 相同覆盖的学习计算表版本，Full 与 Binary 身份固定。

先比较 A/B：实际 getters、相关 RC 电气结果和 SPEF 内容应一致（忽略明确定义的时间戳/非电气元信息）。这是验证注入不改变查询语义。

然后评价 C：不要求与 A 完全相同；应检验返回值确实来自所注入 slots，R 与不覆盖字段保持不变，没有 NaN/Inf/非法指针/量纲改变，并保存变化来源与覆盖。

如果用户只要求算法级比较而本轮不能完成 C，仍交付已经完成的论文/内核结果，明确 computeTable integration 尚未完成。不要把此前固定节点导出改名为 C。

### 6.4 实际精度目标

- 在相同物理参考支持下先验证生成的 compute-table 值和取回值，分别报告插值/量化/组件映射效应。
- 基于原生 full-rule reference 的 PEX/STA 只能称 fidelity，不自动称对真实电场更准确。
- 实际全支持模板上 Anchor 胜过 Full 是必须保留的适用条件证据。不能通过只保留人工稀疏设置规避它。

## 7. P4：运行时间与整个流程

本提交已有固定节点导出结果，直接整合，除非新部署改变执行路径才重测。

### 7.1 分阶段计时

统一分解：
- shared input/model/support load；
- baseline compute-table build 或 learned compute-table build（包括必要数据转换、推理与回填）；
- 原生 extract_parasitics；
- SPEF 输出；
- STA（单列）。

用 wall time 与 wall time 比；CPU core-time 单列。trace 只用于独立计数，正式运行时关闭逐查询日志。比较双方使用相同硬件、线程、优化构建、布局、SDC、Liberty、处理范围和输出格式。

### 7.2 正确的开销公式

无复用首个设计：
`overhead_cold = (T_prep_ours + T_extract_ours - T_prep_base - T_extract_base) / (T_prep_base + T_extract_base)`。

已准备规则的提取：
`overhead_warm = (T_extract_ours - T_extract_base) / T_extract_base`。

D 次真实复用：
`T_total = T_prep + sum_d T_extract[d]`。

共同源模型训练成本单列，不伪装为免费；摊销只对已声明复用次数计算。首次准备费用不可藏在“共同费用”里；共同费用的内容必须对所有方法相同。

不要把很长的布局布线或 STA 纳入分母来稀释 PEX 开销。若报告整个设计流程，也必须同时报告 PEX-only。

### 7.3 结论强度

可以写已有实测：固定节点规则导出的提取比值 0.983–1.047、准备时间及其范围。不能直接写“新内部计算表部署额外开销不超过4.7%”，除非新路径重测也支持。

不能把小于1的计时比自动当稳定加速；报告重复测量和变动范围。需要“很小/可忽略”时给出数值和任务范围，不预设该结论。

不要从1.72 ns 的纯 getter 对照推导整个提取查询只需1.72 ns；该数字不包括模式/宽度解析和装配。

## 8. P5：数值候选的算法整合与必要性分析

先盘点哪些候选已经在 Full 中：PCHIP、aligned-width、六组 GP、raw/clipped neural 与 anchor；它们不是本轮新贡献。

本轮默认不增加大量分支。若确实要加入 affine 或其他快速候选：
- 必须产生明确的新算法版本，不覆盖 Full 的已有数据；
- 选择和调参使用源训练/验证，而非已看过的71个模板或确认集；
- 至少比较 native/multilinear、numeric-only、neural-only/binary、完整组合；
- 同源数据、相同表征支持、明确训练机会和计时范围；
- 若拟提出新的可信选择/回退规则，不能用测试误差决定何时回退；说明在何处选择规则及独立验证范围；
- 添加候选后不能仅展示最佳融合而移除对应纯数值控制。

“将简单方法融入最终算法”是可行的方法开发，但不自动证明融合比单独使用该简单方法更好。组件控制用于给出这个答案。

## 9. P6：论文结构与正面叙述

### 标题（按实际完成度选择）

完成 computeTable 注入：
`Learning to Populate Capacitance Evaluation Tables for Rule-Based Parasitic Extraction`

尚仅验证求值内核与固定节点规则导出：
`Characterization-Conditioned Capacitance Estimation for Rule-Based Parasitic Extraction`

不要在标题中暗示已完成尚未实现的直接商业工具替换。

### Section II 推荐结构

II-A. Rule-based capacitance evaluation：预表征样本、模式/上下文、计算表准备、运行时求值。
II-B. Measured off-grid demand：前移 query census 图；给出所有明确分母；raw/effective区分。
II-C. Problem formulation and scope：相同S，Q，c；已知点保持；生产求值核比较。
II-D. Related work：数值求值、学习电容模型、条件回归；说明互补接口，不作不可行性判断。

查询统计可用英文：

> Across two instrumented capacitance getters on eight fixed routed layouts, 55.77% of logged calls—and 67.16% of finite-distance calls—request geometries absent from the original characterization nodes. These measurements motivate accurate non-node rule evaluation. Native width mapping and compute-grid quantization are retained in the evaluator analysis.

若要写“每个布局都超过30%”，必须从 CSV 逐布局重算并报告对应分母；合计值不能代替每个布局结论。

### 实验设置中的留出说明

> The native census quantifies the frequency of non-node requests, whereas controlled characterization holdout varies the information available to the predictor. We therefore evaluate 10%, 30%, 50%, and 70% holdout as a coverage-sensitivity sweep and report actual layout-derived off-grid queries separately.

不要写“67.16%查询是off-grid，因此70%留出与真实场景一致”。

### 主表/图安排

- 生产主对照：OpenRCX 内核、xRC-derived MLI（证据不足时标准MLI）、本文固定算法。
- 原 Table II：升级为全部四留出率的图/分面表；主结果用生产相关核，明确不同rank、协议和参考。新基线未运行的格子标记未评价，不复用近似基线分数。
- 不必在一张表挤入15条件×4比例×全部方法。可以用每个数据域一个面板，横轴四比例，协议分面；正文保留关键绝对值，扩展稿给完整矩阵。
- 组件表：Anchor-only、强数值候选/numerical-only、Ungated、Binary、Full；完整GP/PCHIP/IDW/affine结果放扩展稿。
- Table III：学习适配比较；名称保留 component-supervised adapted AttentionCap，列出训练/适配设置；不要把CNP归类为物理求解器。
- 部署主表：每设计准确性/fidelity与总准备、原生PEX、输出耗时；旧固定节点与新computeTable路径分开。
- 全支持真实尺寸模板结果保留，不能用漂亮的mask表替代。

### 文体

积极写任务、方法、条件性发现与工程用途。来源/范围用一个明确的定义或表注交代；不要每段都重复免责声明。不出现内部判定码、修复次数、行政扣账、提交时间线和“投稿价值不足”等项目管理语言。

AttentionCap比较的推荐句：

> Under the component-supervised adaptation and observation budget evaluated here, the task-specific estimator achieves lower error than the adapted capacitance-matrix model.

只有相应单元确实支持时使用；不写普遍不可用。原 AttentionCap §4.2 已展示对矩阵单行的监督，不能把组件监督本身说成其无法承受的任务。

## 10. 数据完整性、预算和结束条件

- 四档比例、全部预定工艺/布局、失败和不适用情况均保留；不要“10%好就要、不好就删”。
- 新选型/候选不得使用确认集真值；已看过的数据如用于诊断需明确，不重命名为全新盲测。
- 验证已有所有图表的基线身份、S/Q、误差分母和是否三成员ensemble，不能混加不同聚合口径。
- 常规工程修复允许；不要因为一次NaN比较或路径错误就结束整个任务。
- 默认先交付编辑和可复用结果；随后pilot估计重评分/构建/集成成本。新计算默认上限16 CPU core-hours、最多4个并发进程；这是新任务预算，与已结束任务账本分开。若项目已有更严格授权则遵守。
- 不自动新增GPU训练、大规模场求解或调用商业工具批处理。需要新增物理参考时先记录具体缺口，完成其余独立任务。
- 上限不足时交付实做的完整部分和精确状态，不为了凑正结论改实验；不无限追加研究。

## 11. 最终交付

建议新目录 `docs/pex_kernel_revision/`、`experiments/pex_kernel_revision/`、`results/pex_kernel_revision/`；若已存在等价后续目录则复用并说明。

最低交付：
1. `REVIEW_AND_CHANGES.md`：六点建议落实及修正，每项对应具体稿件位置。
2. `baseline_contracts.json` + 单元测试/原生等价验证记录。
3. `support_coverage_results.csv`：全部四比例、支持/查询/适用统计和新基线身份。
4. `query_census_by_layout.csv`：每布局raw/effective统计；正文图源数据。
5. `compute_table_integration.md`：具体插入位置、键、覆盖、pass-through测试、实际执行状态。
6. 新部署的prepare/PEX/SPEF/STA测量和精度表；若未完成则保留既有部署结果并准确命名。
7. numerical-only 与架构控制的紧凑表，完整数值/学习对照放扩展稿。
8. 更新后的 `main.tex/main.pdf` 与 `extended.tex/extended.pdf`，必要的同步Markdown、图源、CSV和BibTeX。
9. 轻量审阅归档、文件清单、哈希、复现命令和最终完整SHA。

使用现有正式模板。编译并逐页渲染检查正文/参考文献分页、所有图中文字、浮动位置和引用。不要依靠压缩到难读字号来塞入所有记录。

完成本轮可交付内容后停止，不自动发布论文或合并main。是否推送遵循项目现有明确授权；没有授权则保留本地提交并汇报。

## 12. 开始执行

先读实际论文、源码与结果，完成P0，然后并行推进文稿重构与必要的内核核验；复用当前运行时证据。不要仅返回计划，不要把普通工程阻塞变成新的研究否定结论。最终结论由已实现的生产接口、同物理参考精度和完整成本共同决定。
