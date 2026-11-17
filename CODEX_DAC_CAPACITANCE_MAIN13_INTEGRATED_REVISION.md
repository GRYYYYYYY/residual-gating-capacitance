# DAC 电容规则表论文：从 main (13) 开始的 Codex 完整修订任务书

**性质：首次提交的整合执行指令，不是对已执行任务的续跑补丁。**

## 0. 唯一任务对象、当前状态与执行优先级

### 0.1 用户指定的服务器基线

工作区定位入口：

```text
/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114
```

当前正文主源与编译稿：

```text
/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114/paper/dac_layout_query_revision/main.tex
/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114/paper/dac_layout_query_revision/main.pdf
```

论文题名：**Learning to Populate Capacitance Evaluation Tables for Rule-Based Parasitic Extraction**。

用户确认：服务器仍是附件 `main (13).pdf` 对应版本；此前修订指导尚未交给 Codex 执行。不要假定上一轮指导中的实验、代码、文稿更新已经完成，也不要启动不存在的旧任务或继承其“已通过”状态。先核对实际文件、HEAD 与工作区，保留发现的有效后续改动，不强制回退。

本任务书独立包含需要执行的要求，替代此前 `CODEX_DAC2027_REVISION_GUIDE.md` 中针对本论文的修订指令，以及之后关于 Full/Binary 选型的文字补丁。不要求先执行旧任务书再执行本文件。

### 0.2 本轮核心定位：保留 Full 为统一默认方法

**保留 Full 的主方法定位。选型依据是：在已评估的多种数据域、支持区域、缺失模式和缺失比例中，对 OpenRCX kernel 与 MLI-ext. 保持更一致的改进，而不是要求 Full 在每个条件、每项指标上都优于 Binary/Ungated。**

这是需要用原始数据核实、量化和解释的经验性主张，不是要求实验必须产生某个预定结果。简化变体的局部最优不自动否定 Full 的定位；原始数据若不支持“全部条件”或“只有 Full”，必须修正相应限定，不改数据、筛选条件或无限调参来保住措辞。

本轮不以“Binary 在部分 STA 指标上更好”为由自动将其升级为主方法，也不默认增加 Full/Binary 运行时选择器。Full、Binary、Ungated 均保留，公开它们各自的精度、成本与适用边界。

### 0.3 FPGA 迁移文件的隔离

用户另提到尚未提交 `CODEX_FPGA_BOUNDED_DEVICE_MIGRATION_AFTER_706FEBA1.md`。编写本整合稿时未能取得该文件原文，因此其未知内容没有并入本任务书，也没有被当作已执行工作。

本轮只授权上述电容规则表论文修订。不要根据文件名推断内容，不要将 `706FEBA1` 当作本论文 Git 基点，不要据此 checkout、cherry-pick、切换器件、迁移 RTL、启动 Vivado/VPR/HLS 或改动其他 FPGA 项目。若服务器恰好存在该文件，只记录其存在与归属，涉及其他项目的动作保持未执行。本项不阻塞本论文的独立修订。

### 0.4 范围与基本原则

- 本轮不处理篇幅限制，不先压缩；不因页数超限判定失败。
- 任务仍是：有限预表征样本下，对未采样几何的电容求值与规则计算表准备。人工 holdout 是评价协议，不把真实需求写成修复损坏文件或偶然丢失的数据。
- 不扩展到 GPU/FPGA 加速、大规模架构搜索、新模型家族或商业工具逆向复现。
- 上轮模拟评审中的疑点是待核查事项，不是已经证实的数据泄漏、基线不公平或实现错误。
- 优先复用现有、配置匹配且可追溯的结果。先完成旧结果复核和主线论证，再做有限的缺口实验。
- 交付必须包含实际论文修改与编译产物，不能只输出新计划、审计报告或待办列表。

---

## 1. 工作区保护与单一正文主源

先读取当前项目指令，并检查上述正文目录内是否存在 `SOURCE_OF_TRUTH.md` 或等价说明。没有该文件不构成错误；不要臆造其内容。以用户指定的 `paper/dac_layout_query_revision/main.tex` 为正文入口，追踪实际 `\input`、图表、BibTeX、脚本和数据依赖，不另建一个无人同步的正式主稿。

记录：实际 Git 根目录、分支、HEAD、未提交改动、当前 LaTeX/PDF/图表哈希、OpenROAD 与 Python 环境、模型和结果路径。路径名不是 Git 仓库边界的保证，先核验再操作。

在独立修订分支或 worktree 工作，例如 `revision/dac-cap-main13-integrated`；保护已有未提交改动。若使用 worktree，确保当前主稿和有效未提交依赖被受控带入，不静默回退到旧提交版本。原稿、参考输出、模型、实验归档作不可覆盖快照；新增文件使用独立 experiment ID。

禁止 destructive reset/clean、覆盖旧结果、结束无关进程、默认占满共享机器。未经明确授权不推送远端。允许在本轮修订分支修改 `main.tex`；不要把“保护 Git main 分支”误读为“不能修改论文 main.tex”。

编写本任务书时可核实的本地附件信息仅用于识别来源：

```text
main (13).pdf
bytes: 2144216
sha256: 20b073e049a403093e4a3c89f61f1c1f7fa6d51dee2566da91de3064aa1422e7

旧任务书 CODEX_DAC2027_REVISION_GUIDE.md
sha256: c9407dd938bc15df39bebce43f1e3a02d95d00de304e84783fa286a9a504ddd2
```

这些不是已核验的服务器文件哈希。若服务器 PDF 因编译元数据等导致字节不同，进一步核对内容与源文件；不能仅凭哈希不同覆盖用户当前版本。

---

## 2. 第一阶段：有限证据核验，不重新开启无边界审计

生成 `evidence_audit.md` 和 `claim_evidence.csv`，至少记录：

```text
issue_id,paper_location,claim,protocol,code_path,data_path,
config_hash,checkpoint_hash,reference_type,metric,aggregation,
evidence_status,required_action
```

优先核对下列既有内容。下述数值是当前稿报告值，不是本轮重新实测值，必须映射到原始记录。

| 核查对象 | 当前稿报告或描述 | 核查目的 |
|---|---|---|
| Fig. 4 | Full 分别在 60/60 条件超过两条基线，在 49/60 条件优于 Binary | 重建完整条件表；补充 Binary/Ungated 同时超过两条基线的精确数量 |
| 两条部署协议 | rule-export 使用 B=4/8；native compute-table 实验使用完整表征 | 保留不同协议，不拼接其精度与时间形成联合主张 |
| 下游变体对照 | Full 相对 Binary 的 net-C/WS 优势为 6/16、4/16；Binary 的 P99 在 10/16 更低 | 核对聚合和指标，作为权衡而非自动改换主方法的理由 |
| 数据数量 | Public inventory 1713；fit/select/confirm 1051/246/340；budgeted 338；native holdout 84、eligible 83 | 重建过滤映射，不把数量差异直接判为错误 |
| 训练机会 | Full 的 Public 为 24k updates，FEM/Transfer 为 12k；adapted AC 在 FEM/Transfer 为 3k | 结合数据量、batch、ensemble、适配和调参机会判断，不机械比较更新次数 |
| MLI 协议 | complete-cell coverage 报告为 20.7% | 区分插值核心和 sparse/boundary extension 的贡献 |
| 重复 episode | 稿件记录 21840 个可行 episodes 及 11245 个重复 rounded S/Q episodes | 核验定义、重复身份和统计单位，不把两数简单相减当作独立样本数 |
| 查询与注入 | 9888586 calls、55.77% raw non-node、849663 个映射到有效节点的请求、924647 changed returns | 确认追踪范围一致后再计算覆盖率 |
| 成本 | Table III、first-design overhead、rule-export 与 direct query 成本 | 核对计时边界、重复数、版本及聚合口径 |

每项标记 `CONFIRMED GAP / ALREADY ADDRESSED / NEEDS VERIFICATION / BLOCKED`。相关原始结果已经能回答问题时，直接复用并改稿，不为形成“新日志”重跑。不能仅因某项依赖缺失就停止其他可执行工作。

数据一旦用于本轮选择配置，就不能继续宣称它是本轮 untouched confirmation。基于 Fig. 4 的模型定位与机制解释是事后分析，明确这一点；不得把它写成预注册的前瞻选择结果。

---

## 3. P0-A：用原始数据确立 Full 的跨条件基线改进一致性

### 3.1 固定原 Fig. 4 的评价宇宙

完整保留当前稿的 60 个条件：Public/FEM/Transfer 三个域 × In/random、In/block、Out/random、Out/block、Boundary 五类条件 × 10/30/50/70% 四个 holdout 比例。沿用该覆盖实验的 seeds 11/29/47/71/101，并以实际配置核实；不要混用下文原生预算实验的三个种子。以配置文件核实可行条件，不新增有利条件，不删除简化变体或 Full 的不利条件。

人工 holdout 比例与布局查询统计中的 raw non-node 比例不是同一量，不能用 55.77% 推导或重新设定 holdout。

沿用现有 macro NRMSE、component/group 权重、mask 聚合、ensemble 预测方式。若发现实现错误，输出纠错前后的映射与原因；不能悄悄更换聚合方式以改变胜负。

对每个条件 c 记录：

```text
E_OpenRCX(c), E_MLI_ext(c), E_Ungated(c), E_Binary(c), E_Full(c)
```

定义较强基线参考：

```text
B(c)   = min(E_OpenRCX(c), E_MLI_ext(c))
R_m(c) = E_m(c) / B(c)                [仅在 B(c)>0 时定义]
G_m(c) = 1 - R_m(c)
```

因此 `R_m(c)<1` 表示 m 同时超过两条基线。`B(c)` 仅用于分析，不是可以访问测试真值的运行时 oracle 或新增部署基线。

### 3.2 必须生成的统计

为 Ungated、Binary、Full 分别输出：

- 相对每条基线的严格胜/平/负数量；同时严格超过两条基线的条件数。
- 完整逐条件 `R_m(c)` 与 `G_m(c)`；最差误差比 `max_c R_m(c)` 和最小改进裕量 `min_c G_m(c)`。
- 所有回退和最接近回退的条件；其绝对误差差值、数据域、支持类型、holdout、有效独立组数。
- 一份保留原始未舍入值的统计，以及一份按预先定义数值容差统计的结果；不混用两个计数。

零基线：两者同为零是平局，不记为严格改善；基线为零而方法误差大于零是回退，误差比未定义或正无穷，显式处理。不得任意在分母加 epsilon 来隐藏回退或制造改善。近零分母同时显示绝对误差。

数值容差由实际 dtype、重复计算噪声和指标尺度确定并记录，不能根据目标输赢临时设置。统计显著性另行报告，不把容差内相同写成显著优于。

建议输出：

```text
coverage_cell_metrics.csv
baseline_dominance_summary.csv
baseline_regression_cases.csv
baseline_margin_summary.csv
baseline_consistency_report.md
```

正文增加一张紧凑表：

| Method | Beats OpenRCX | Beats MLI-ext. | Beats both | Worst error ratio | Minimum improvement margin |

保留 Fig. 4 原始比较功能。可增加相对较强基线误差比图或配对差值图；不必将所有对照线挤进原有 15 个小图。

### 3.3 论文主张的条件化规则

- 核验 Full 为 60/60，且其他变体不是 60/60：可以写 Full 是这些匹配变体中唯一在全部已测条件同时改善两条基线的方法。
- 其他变体也是 60/60：删除“唯一”，如实报告裕量、平均误差和成本差异；不得为了维持唯一性重新筛选条件。
- Full 不是 60/60：定位是否为版本/计算错误；无错误则修改数字与主张。保留 Full 为研究对象不等于保留已被证据否定的表述。
- 改进幅度与统计波动不可分：可以报告汇总点估计改善，但不声称显著消除了退化风险。

允许的主张：`consistent improvements over both kernel baselines across the evaluated conditions`、`an empirically motivated default when the favorable simplified variant is not known in advance`。

不允许的扩展：任意未知工艺/拓扑/应用都最安全、具有分布外无回退保证、所有查询/规则/种子均改善、所有 STA 指标更稳健、超过所有数值或学习方法。

**本阶段不需要新训练。首先完成，直接服务于论文主线和消融目标。**

---

## 4. P0-B：解释一致改进的来源，正确对待简化变体局部最优

### 4.1 先从真实代码核对结构

稿件的解释框架为：Ungated 直接加神经残差；Binary 对 Anchor/神经候选进行融合；Full 扩展数值候选并使用支持特征和候选 agreement。

若代码确为单神经候选的二路 Binary，可用以下形式解释：

```text
Ungated: b + r_NN
Binary:  b + alpha * r_NN, 0 <= alpha <= 1
Full:    b + sum_e pi_e * Delta_e
```

以上省略归一化和最终非负截断。分别训练的模型拥有各自的参数与残差，不能把 `r_NN` 当成相同预测，进而把 Full−Binary 或 Binary−Ungated 的全部差异归因于一个门控系数。代码若包含其他分支，以实际实现修正公式。

Full 的最终融合在有效候选上满足权重归一化，但这不保证误差不超过任一候选或两条传统基线。候选有效性不等于准确性；agreement 不是经过校准的不确定性或安全证书，多个相关候选也可能共同偏离真值。

### 4.2 需要检验的机制假设

**H1，Ungated 的局部优势与回退。** 神经残差方向、幅度准确时，不抑制修正可能更好；Anchor 已准确而残差不准确时，直接相加可能过度修正或引入错误方向。

**H2，Binary 的作用与限制。** 门控可减小不可靠修正，保留 Anchor；但若 Anchor 与神经候选具有同方向偏差，仅在二者之间融合可能不足。

**H3，Full 的互补候选。** PCHIP、WidthLinear、GP 等在部分支持形态下提供不同修正，可能弥补简化变体弱点；support descriptors 和 agreement 可能帮助分配权重。是否确实如此必须看候选误差和消融。

**H4，Full 的局部非最优。** 简单修正已充分准确时，融合其他候选或压缩有效残差可能降低精度。这是需要报告的权衡，不是异常点删除理由。

### 4.3 先做无新增训练的诊断

在全部 60 条件保持完整评分，收集所有“简化变体未超过基线、Full 超过”的条件，以及简化变体优于 Full 的条件。案例展示采用预先写明的规则，例如各域最差回退与最小 Full 改进裕量；这些都是事后诊断，不作为新增独立确认。

逐成员、逐分量保存 Anchor、各候选输出、validity、gate weights、加权修正 `pi*Delta`、支持密度/距离/affine rank/hull 等可访问特征。由独立评分程序读取 query reference 计算候选误差、残差方向和融合误差；诊断标签不得流回预测、特征构造、回退或调参。

解释必须同时有成功与失败案例。门控权重较大不自动意味着该候选具有因果贡献；诊断只能产生有证据约束的解释，不能替代机制消融。

### 4.4 三个有界机制对照

**C1：Numerical-only Gating。** 保留 Anchor、PCHIP、WidthLinear、六个 GP、有效性掩码及数值/support 特征，移除 NN、NN-Clip 和 Transformer 的 h。门控仍可学习；明确它不是“完全不学习”的算法。使用现有 source 数据和冻结的选择规则。

**C2：Same-candidate Fixed Fusion。** 冻结 Full 每个 ensemble member 的相同候选输出与掩码，仅将自适应门控替换为源数据确定的固定非负权重，在有效候选间归一化。权重拟合用 source fitting，配置选择用 source selection。先按成员融合再按原协议 ensemble，不混入已融合后的预测。该 post-hoc 对照隔离已学候选上的门控作用，但不能声称等同于重新训练完整固定融合模型；若已有后者的合法结果，另列。

**C3：No-agreement Features。** 保留其余结构、候选集合和训练协议，仅移除均值/标准差/范围等 agreement 特征并重新训练。仅在推理时置零可以作为诊断，不能替代匹配训练的结构消融。

优先复用已有等价对照；新训练仅限明确缺失的对照，沿用现有合理训练预算、ensemble 和 source selection，不默认扩大网络或新增超参网格。报告计算预算；资源不足标记 NOT_RUN/BLOCKED，而不是无限扩展。

这些对照除平均误差外，也必须统计“同时超过两条基线的条件数”和最差相对误差比。某模块不能支持稳定贡献时收缩该模块的论述，不要求所有消融在所有条件都落后于 Full。

### 4.5 Full/Binary 的正文呈现

主表中显示 Full/Binary 的离线误差、下游指标、准备时间和成本差异。Binary 的局部最优说明部分条件不需要完整融合，不自动触发更换主方法。

“Full 跨条件更一致”只相对于所统计的基线和指标成立，不能用离线 macro NRMSE 的覆盖率推导 P99 endpoint error 也更稳健。保留已经成立的 Binary 下游优势，并对部署指标的不同进行解释。

本轮不新增 oracle 选择或复杂选择器。简单变体作为特定已验证场景下的低成本选项可以讨论，但选择依据必须在部署时可得，不能使用封存查询真值事后选最优。

---

## 5. P0-C：补齐同一稀疏预算、同一原生接口的端到端证据

Full 的新选型论证不消除部署协议缺口。保留旧 rule-export 与 full-characterization compute-table 结果的准确名称，不能将它们直接改名为统一稀疏原生结果。

### 5.1 冻结有限实验矩阵

复用当前稿已有条件并核验其实现：

| 项目 | 本轮协议 |
|---|---|
| 布局 | AES、Ibex × ASAP7、GF180、IHP SG13G2、Sky130HS |
| 预算 | 参与削减的每个目标规则 B=4/8，报告不足 B 的实际样本数及处理方式 |
| 支持选择 | 原 rule-export 的 farthest-point 实现与 seeds 11/29/47 |
| 模型 | 冻结 source-trained checkpoint；沿用实际 ensemble 与 canonical batching，核验当前三成员、query chunks of 32 的实现；无目标查询标签参与预测或参数更新 |
| 主臂 | Native-sparse、MLI-ext.-native、Binary-native、Full-native |
| 参考 | 原始完整规则产生的 full-table extraction；明确其是输出保真参考 |
| 原生条件 | 相同 layout、库、约束、OpenROAD 版本、getter、width mapping、quantization、RC assembly、SPEF/STA 设置 |

8 布局 × 2 预算 × 3 种子形成 48 个配对设置、16 个 layout–budget 单元。四个主臂的完整候选矩阵为 192 个 arm-settings，不含参考或重复计时；这不是 192 个独立布局。已有完全匹配结果直接复用，不强制重跑。

先冻结 `protocol.yaml`：数据、支持、槽位、模型、batching、失败处理、指标、参考、随机性、计时、统计单位和资源上限。少于四个可用匹配观测等 eligibility 边界按代码和预定协议处理，不能悄悄增加目标观测。

### 5.2 真正隔离隐藏标签

对被削减的规则，只有 S 中的真实观测可进入：原生建表、Anchor、GP/PCHIP、神经网络、门控、局部斜率/曲率等特征、归一化和 fallback。

**禁止先用完整电容值建立原生表，再只在神经输入中 mask 标签，而让 getter 或 fallback 继续返回被隐藏的真实值。**

候选坐标、已知材料、label-blind 的 slot inventory 可以使用，但必须声明来源和访问边界。完整 reference 的数值内容仅对评分侧可见；不得从其电容、STA 或误差反推 eligible 范围、回退规则或模型选择。

若原生结构需要完整几何节点才能建立 canonical grid，允许使用无标签的结构信息并记录；不能借结构需求恢复隐藏电容。若稀疏构造改变槽位范围，先定义所有被测臂共有的合法结构契约，报告与完整参考的映射，不能手工挑有利槽位。

本轮“保留测量值”指保留 S 中当前可用观测，不是同时保留被封存的全部原始测量值。电阻、未参与削减的其他规则可以保持原状，但必须跨方法一致并公开范围，不声称整个规则库或电阻表征成本都按 B 减少。

加入隐藏标签扰动测试：保持 S、坐标、配置和可访问上下文不变，修改测试副本中的封存标签，预测、注入、被测提取输出必须不变；仅独立评分参考/分数允许改变。不要改写真实 golden。测试失败先定位，不能进入正式性能结论。

### 5.3 四个主臂的准确含义

| 主臂 | 定义 |
|---|---|
| Native-sparse | 原生构造仅使用 S，不注入模型预测 |
| MLI-ext.-native | 相同 S，在共同 eligible canonical slots 上用规定的 MLI-ext. 注入 |
| Binary-native | 相同 S、槽位、冻结 Binary 模型及部署协议 |
| Full-native | 相同 S、槽位、冻结 Full 模型及部署协议 |

共同 eligible 集合依据方法无关结构规则确定；每个方法额外的有效性、fallback 和失败单独报告。不能只留下所有方法都成功的简单案例而不报告排除范围。

未覆盖路径使用共同的、仅依赖允许信息的处理方式。若无法合法构建 Native-sparse 或共同结构，明确技术阻塞，保留已完成诊断；不得悄悄切回 rule-export 后继续称为原生闭环。

### 5.4 Smoke tests 与原生契约

先在一个最小可用布局和一个原稿中误差较大的 IHP 设置执行有限 smoke tests；两个目的分别是接口排错与困难条件检查，不以有利性能作为通过标准。

验证：真实观测恢复、单位/分量映射、非负有限值、slot key 唯一性、注入与 getter 一致、电阻和 special/uncovered 行为一致、输入哈希与参考端点身份。interface-disabled/native-value pass-through 在可比较条件下应保持电气输出。

debug/trace build 用于正确性，release build 用于时间。通过标签隔离和接口测试后，再运行冻结矩阵。正确性修复允许必要重跑，但保留修复记录，不能把调试运行当作最终计时。

### 5.5 必须保存的指标

net-C NRMSE、绝对 WS/TNS deviation、endpoint MAE/P95/P99/max、signed slack deviation；若统计乐观/悲观误差，明确符号和判定。固定 net/endpoint 身份与分母，缺失键单独报告，不静默丢弃。

绝对误差与相对改善并列；基线误差为零时相对改善不强行定义。电容、ps/ns、TNS 等单位明确。

同时记录 eligible/modified/fallback 覆盖率及分阶段时间。Full 未优于某个变体不影响实验“完成”状态；实验完成与性能主张通过分别标记。

---

## 6. P1：基线范围、公平性和独立统计

### 6.1 两条主基线与强数值控制各司其职

OpenRCX kernel 与 MLI-ext. 继续作为 Fig. 4 的主基线，保留“对这两条基线的一致改进”主张。不得将它扩大成“超过所有传统插值法”。

复用已有 Anchor、GP、PCHIP、affine/simplex、IDW 与 adapted MLP 数据，展示有竞争力的方法。若要选择一个强数值默认方法，只能基于 source selection 预先固定；否则分别报告。不能用目标查询真值逐点选择最佳数值结果再作为可部署方法，也不能为突出 Full 隐藏已有强控制。

MLI 分开报告 complete-cell、稀疏单元扩展、outside-support、boundary 的样本数和误差。若多数差异来自 extension，明确这一事实，不把该部分收益全部归因于 MLI 数学核心不足。

从代码说明二维 FEM/Transfer 中 OpenRCX 核的适配、width selection、整数坐标与 compute-bin 处理。四维仅实现测试时，不改写成四维物理验证。

### 6.2 神经基线

对 MLP、CNP、component-supervised adapted AttentionCap 记录源码/权重版本、监督分量、训练数据、updates、batch、ensemble、目标拟合步数、超参候选与选择来源。

相同 B 仅说明目标观测数量一致，不自动代表完整训练资源相同；更新数不同也不自动构成不公平。检查是否存在明确欠优化，再决定是否需要有限 source-validation 敏感性试验。无确凿需要不扩大训练任务。

保留 adapted AttentionCap 的任务适配名称，不声称完整复现原始系统或在其原始任务上全面超越。不得因为当前结果较弱而不断尝试目标集设置，也不能人为限制基线使其表现更差。

### 6.3 统计与来源隔离

保留当前指标定义；区分 ensemble-averaged prediction 的误差与 member-wise error average。不同聚合不能互相替换。

对 Full 相对两条基线、Binary 和强数值方法的差值做配对统计。优先在实际独立 rule/template/context 层级重采样，保留同组查询和多个 holdout/mask 的相关结构，不将所有 queries、seed 或计时重复视为独立证据。

对回退点和最小改进裕量说明统计不确定性；必要时输出置信区间。组数过少时报告完整差值、范围和局限，不伪造可靠显著性。

“60/60”是相关条件上的描述性计数，不是 60 次独立检验，也不是未来应用失败概率估计。总体平均指标改善不等于每张表或每个查询都改善。

说明 source fitting/selection/confirmation、native holdout、标准化 scales 和目标支持的访问范围。确认过的数据若被用于本轮选模型，标记 post-hoc，不重新贴上 untouched test 标签。

---

## 7. P1：部署一致性与物理性质

### 7.1 Query-set dependence 先诊断，不默认重写架构

保持 S、模型和单个目标 slot 不变，比较 Q=1/8/32、不同陪伴 query、排序、分块边界、padding、重复 query 时的同一 slot 输出。分别记录纯排列、集合变化和分块变化，避免混为一项。

报告绝对变化、源尺度归一化变化、相对参考误差的变化，容差按实际 dtype 和应用精度预先定义。query-set dependence 不自动等于数据泄漏；需要明确当前 transductive 预测与固定 canonical batching 的部署契约。

若差异显著影响结论，再考虑独立编码 support/material、由每个 query 读取这些表示的有限对照。仅屏蔽直接 query-to-query 而允许 support 先读 query，不能保证集合不变性。结构修改需一致训练并重新验证，不能仅在推理换 mask 后当作已验证新架构。

本轮默认不自动扩大到新架构研究；固定排序只提供确定性，不宣称查询集合不变。

### 7.2 物理行为与参考类型

检查非负、有限值、观测保持、单位转换、对称上下文和相邻槽位异常跳变。单调性仅在几何与电容分量确有适用依据的条件下检查，不对所有耦合与边界统一强加未经验证的规律。

对 IHP 等较大误差优先检查单位、分量、量化、eligible 范围和外推，不先扩大模型。

保持 independent FEM 的模板与边界覆盖说明。只有已具备真实几何、材料和边界的可用参考时，才增补少量 layout-derived 检查；没有资源就明确缺失，不宣称 full-rule OpenRCX 是独立物理真值。

本文至少区分：离线 reference-label accuracy、完整规则输出保真、独立 FEM accuracy。对完整规则的 WS/TNS 接近不能直接写成 sign-off accuracy 提高。

---

## 8. P1：实际覆盖率、准备开销和复用成本

### 8.1 覆盖率不是单一数字

统一 trace 键和统计范围，分别输出 all calls、raw non-node、effective non-node、eligible slots/returns、populated slots、changed returns、unchanged-after-injection、fallback/excluded。

这些集合未必构成同一条严格包含的漏斗，必要时使用交叉表。只有分母范围相同时才计算诸如 `924647/9888586` 的比例。

“非节点查询需求”“能够写入”“数值改变”“误差改善”是四个不同概念。55.77% 不能直接作为实际受益比例，changed returns 也不是改善的调用数。

### 8.2 不混合准备阶段与提取阶段

按原始计时记录区分 source label generation、source training、target support acquisition、inventory、加载/支持准备、prediction、table construction/injection、PEX、SPEF、STA。未测项目写 unmeasured，不视为零。

同一阶段只计一次；原生 construction/injection 已包含在 PEX 内时，不再次加到外部准备。首次 inventory extraction 若真实需要，就计入成本。保留共有费用与算法专有费用的区别，双方采用相同时间范围。

可使用以下口径，但每项必须与真实调用链对应：

```text
T_cold = T_external_prep + T_native_path
T_total(N_reuse) = T_reusable_prep
                  + N_reuse * (T_per_design_prep + T_native_path)
```

`N_reuse` 表示复用次数，避免与电容分量 K 混淆。只有确实能跨设计缓存的工作才能放入 reusable prep；逐设计 inventory 不得任意摊销。

有真实复用路径时给出 N_reuse=1/10/100 的成本模型，明确哪些数值实测、哪些按实测建模。尚未实现跨设计复用时，只能作标明假设的模型，不宣称已经测得可复用收益。

提取阶段接近原生延迟，不等于首次总成本接近原生，也不是全流程加速。目标 characterization budget 固定，不代表来源数据生成和训练总成本为零。

不沿用上轮聊天中由表格推算的首次比值作为新增实测。先核对 Table III、first-design overhead 和日志口径；若不一致，解释版本/分母/聚合差异后修正。

---

## 9. 论文回写：以 Full 的一致改进为主线，而不是逐条件最优

### 9.1 Introduction 与贡献

问题保持为有限 characterization samples 下的未采样几何求值。介绍 observation-conditioned residual fusion 与 native preparation 的实际区别，不重新定位为通用场求解器替代或完整 RC 提取器。

明确默认配置的目标：在不知道哪种简化变体最适合目标支持条件时，提供跨已测条件更一致的基线改进。不使用“最保险”“任意未知应用无回退”作为无条件科学结论。

贡献可以分别围绕：目标表征条件化估计、数值/学习修正的自适应融合、合法原生计算表准备及统一验证。每条贡献必须有对应数据，不靠成熟模块名称堆砌新颖性。

### 9.2 Abstract

若原始结果核验通过，保留 Full 在全部 60 条件超过两条 kernel baseline 的核心发现，并明确其统计层级是条件级 macro NRMSE。

区分 rule-export fidelity 与 native compute-table；只有统一稀疏原生实验完成且支持时，才把其精度收益和开销写成同一配置的联合结果。不得用旧 rule-export 精度配旧 full-support native 时间。

简化变体的局部优势不要求占据摘要大量篇幅，但不能在摘要写与正文相反的“所有指标最优”。

### 9.3 Method 与 Training

从真实代码补齐 loss、组件权重、optimizer、learning rate、batch、训练 episode、selection、source scales、ensemble、target fitting 及失败回退。不要凭经验填写参数。

统一物理单位与归一化符号，写清 support hull/envelope、候选有效性、GP 配置、稀疏扩展、query batching 和复杂度。

解释 Ungated/Binary/Full 的结构差异，不把同时改变候选集合与表示的对照称作严格隔离“门控单独作用”。对冻结候选替换与重新训练的消融分别命名。

### 9.4 Results 中建立完整消融论证

建议先呈现 Fig. 4 与新的 baseline consistency 表，再解释三种变体在不同支持条件下的差异；随后展示机制对照、固定预算、下游和成本。沿用已有结构也可，但必须有清晰的叙事对应。

可使用以下论证骨架，所有量化和“唯一”表述经数据核验后填写：

> Full is selected as the default configuration for the consistency of its improvements over the two kernel baselines across the evaluated conditions, rather than for attaining the lowest error among all ablations in every condition. Simplifying the fusion can improve accuracy in particular regimes, but does not necessarily preserve the same baseline-improvement coverage. We interpret these results as empirical evidence within the evaluated task and support conditions, not as a guarantee under arbitrary distribution shift.

不要原样保留“does not necessarily”来回避真实计数；已有数据能明确时给出 Binary/Ungated 的实际数目和差值。机制原因只使用本轮能支持的分析，不写成未经验证的事实。

保留 Binary/Ungated 的局部最优、Full 可能较高的准备成本和下游尾部权衡。主张“Full 相对两条基线稳定改善”与“简化变体局部更好”并列呈现，不互相抵消，也不互相混淆。

### 9.5 图表与下游

保留 Fig. 4 的所有条件。新增一致性表及必要的配对差值/误差比展示；强数值对照可用独立表避免过度拥挤。fixed-budget 比较保留有竞争力的 MLP/GP，不只展示较弱方法。

旧 Table II/Fig. 6 准确标注 rule-export。新增 native sparse 对照时注明不同协议，绝不重命名旧实验。下游同时显示绝对 C/WS/TNS/P99 和相对改善，Full/Binary 都可见。

运行成本区分 cold、reuse、PEX-only、SPEF、STA。图表和正文数字从同一机器可读 summary 生成，避免手工复制不同聚合版本。

### 9.6 相关工作与商业工具表述

MLI 是定义清楚的通用数值基线。没有可核查的内部算法文档与等价性证据时，不称为 Calibre xRC 内核复现或已验证的数学等价实现。

商业工具不作为直接算法基线的理由落在目标任务、可控输入与接口范围，不能把整个集成产品笼统称为单一 field solver。

沿用可核实的本地文献来源；需要新增事实时实际读取对应原始文献或官方说明。不要把上轮聊天中的网页 citation ID 直接复制为参考文献，不编造 BibTeX。未核实的差异不写成确定事实。

### 9.7 Limitations 与 Conclusion

限制保持精确且与证据相符：已测条件的经验稳健性、强数值方法在部分任务更优、full-support Anchor 优势、Binary 的下游权衡、query-set dependence、有限 FEM 覆盖、未测成本等。

不把所有负结果集中写成与主线相反的结论，也不删除仍成立的限制。模块无明显独立收益时收缩该模块的创新宣称；Full 的主方法定位不要求所有模块在所有条件都有效。

Conclusion 回到：固定目标表征预算、跨条件对两条主基线的一致改进、原生准备的实际部署证据及边界。不能用“最保险”替代量化发现。

### 9.8 保持论文体裁，而不是把审计日志搬进正文

正文集中呈现问题、方法、协议、主要结果和适用边界。工作树保护、任务恢复、哈希、失败命令、内部阶段名和完整证据索引进入复现材料，不把论文写成工程收尾记录。

这不意味着隐藏影响结论的失败或负结果：相关科学限制和关键不利指标仍在正文可见。通过清晰组织降低重复说明，不以删掉重要事实改善叙事。

---

## 10. 实际执行顺序、资源边界与停止条件

### 10.1 不等待逐阶段确认，按依赖推进

1. 核对指定工作区、保护原稿、建立单一 source of truth 和有限 evidence audit。
2. 复用 Fig. 4 原始数据，完成 60 条件统计、Full 选型论证、失败条件与最小裕量分析。此步不新增训练，可直接产生首轮文稿修改。
3. 冻结原生稀疏协议，完成标签隔离、接口和困难案例 smoke tests；未通过时只修正确性，不启动完整性能矩阵。
4. 运行或复用有限原生四臂矩阵；同时完成基于现有冻结输出的机制诊断与固定融合对照。
5. 仅对缺失而必要的 C1/C3 做限定训练；完成强数值基线、统计、batching、覆盖率与成本核查，避免无边界扩展。
6. 将已证实结果回写指定主稿，自动生成数字和图表，编译并检查 PDF；交付完整状态与可复现入口。

没有依赖关系的轻量工作可并行，但先检查共享机器资源，不停止无关任务。不要以某一新增实验阻塞全部文稿改进。

### 10.2 实验有明确边界

默认保持原有 8 个布局、B=4/8、3 个支持种子、4 个原生主臂，以及原 Fig. 4 的完整评价协议。不为获得更漂亮结果增加更多 seed、工艺、布局、分支或 architecture search。

运行前在协议中记录 max_workers、每任务 timeout、重试条件、训练预算和可用资源；依据现有项目权限保守设置，不能自动使用机器全部核。失败配置是否重试由预先规则决定，不能只重试某个输掉的模型。

已有合格结果复用；代码修复导致必须重跑时给出失效范围，只重跑受影响部分。固定融合 post-hoc 结果与重新训练结果分开，避免无谓扩大。

### 10.3 遇到负结果或阻塞时的处理

- 只有 Binary/Ungated 的局部优势：保留 Full 主方法，补充具体权衡，不自动更名或重做方案。
- 核心 60/60 或“唯一”不成立：核查后如实修正，不能按预设结论改聚合或删除条件。
- 某新模块没有贡献：收缩该模块的机制宣称，不循环加模块追逐目标集。
- 原生稀疏路径确实无法实现：交付具体接口限制、已完成代码/测试及可支持的保守改稿，不把 rule-export 冒充闭环。
- 缺数据、PDK、模型、工具或计算权限：明确依赖和影响，完成其余部分；没有结果不能填零、估计后冒充实测或宣称已解决。

这些情况均不授权回滚用户其他工作、切换硬件项目或强行推送。

---

## 11. 交付位置、验收标准与最终汇报

### 11.1 沿用现有目录；缺少约定时使用以下结构

```text
docs/dac_main13_integrated_revision/
  execution_manifest.md
  evidence_audit.md
  claim_evidence.csv
  protocol.md
  baseline_consistency_report.md
  mechanism_attribution.md
  full_default_rationale.md
  manuscript_change_log.md
  reproduce.md
  final_revision_report.md

configs/dac_main13_integrated_revision/
  protocol.yaml

scripts/dac_main13_integrated_revision/
  ... 核查、实验、统计与图表的实际入口 ...

results/dac_main13_integrated_revision/<experiment_id>/
  manifest.json
  raw/
  coverage_cell_metrics.csv
  baseline_dominance_summary.csv
  baseline_regression_cases.csv
  baseline_margin_summary.csv
  mechanism_candidate_metrics.csv
  native_sparse_metrics.csv
  paired_comparisons.csv
  timing_breakdown.csv
  coverage_accounting.csv
  tests/

paper/dac_layout_query_revision/
  main.tex
  main.pdf
  ... 已有实际依赖 ...
```

已有等价路径可直接复用并在 manifest 映射，不为满足上述文件名复制一套重复结果。main.tex 的实际源依赖以项目为准；原稿快照保留，不把快照当第二个正式主源。

修改后的正文和 PDF 应位于本轮分支/worktree 中上述同一相对路径。报告实际绝对路径；不要声称原服务器目录已更新而实际只修改了另一个未说明的副本。

### 11.2 验收表

| 编号 | 交付目标 | 通过标准；不通过时必须说明 |
|---|---|---|
| A | 基线与保护 | 明确当前分支/HEAD/改动，未假定旧指导已执行；未混用 706FEBA1 或其他项目 |
| B | Full 选型依据 | 完整 60 条件三变体统计、严格/容差计数、相对两条基线的裕量与回退点可复算 |
| C | 机制解释 | 区分结构假设、事后诊断与匹配消融；解释成功与局部非最优，不把门控权重当准确性保证 |
| D | 稀疏原生正确性 | 无隐藏标签依赖；四臂相同信息预算/接口；观测、电阻、单位、特殊路径等测试有记录 |
| E | 下游证据 | 相同协议的 C/WS/TNS/endpoint 指标、原始输出和计时可重建；旧 rule-export 单列 |
| F | 公平性与统计 | 强数值方法可见；基线适配资源有记录；独立单位、重复 episode 与选型状态明确 |
| G | 部署边界 | query batching、覆盖率、冷准备和复用范围有实际说明，不扩大保证 |
| H | 论文实物 | 指定主源已修改、图表数字一致、PDF 编译成功并检查引用/溢出/乱码；不以页数超限失败 |
| I | 可复现性 | 实际命令、版本、数据/权重哈希、输出路径、未完成原因与复现入口齐全 |

实现、实验完成、统计支持、性能主张分别标记 `PASS / FAIL / INCONCLUSIVE / BLOCKED / NOT_RUN`。例如：实验完整运行而 Full 未获胜，应该是“实验 PASS、该性能主张 FAIL/不成立”，不能混成“实验失败”。

### 11.3 最终汇报必须回答

1. 当前修改的是哪个 worktree、分支、提交和正文路径；哪些改动尚未提交或推送。
2. Fig. 4 对三种变体的精确统计是什么，Full 默认配置理由是否成立，哪些措辞因此保留/修正。
3. 哪些机制有独立证据，哪些只是合理但尚未证实的解释。
4. 原生稀疏闭环是否完成、隐藏标签测试是否通过；各条结果使用哪种部署协议。
5. Binary/Ungated 哪些局部优势仍成立；为何这不等于要求逐条件替换 Full。
6. 公平性、统计、batching、成本与覆盖率还剩什么限制。
7. 修改后 LaTeX/PDF、图表、原始结果和复现入口在哪里。

只汇报已实际完成的工作。生成脚本、启动进程、排队或计划进行不等于实验完成；不要承诺论文必然录用，也不要仅以“提升了创新性/竞争力”代替证据。

**现在从指定工作区的基线核对开始执行，而不是再返回一份新的计划。**

---

## 来源与整合边界

本任务书依据当前对话提供的 `main (13).pdf`、已读取的 `CODEX_DAC2027_REVISION_GUIDE.md` 原文，以及用户关于 Full 跨条件超过两条基线的选型说明整合。当前稿中的方法与实验数字主要对应 Section III–V、Fig. 4–6、Table I–III；这里列出的论文数字均是待映射到服务器原始记录的来源报告值。

本任务书新增的统计、诊断、验证和输出要求是修订执行设计，不声称这些实验已经实施或其结果已经成立。未读取服务器实际代码/主稿，也未获得 `CODEX_FPGA_BOUNDED_DEVICE_MIGRATION_AFTER_706FEBA1.md` 原文；对两者不作虚构的执行状态或内容判断。
