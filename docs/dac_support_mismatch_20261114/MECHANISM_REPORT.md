# 有界支持协议验证：未充分执行报告

**机制状态：INCONCLUSIVE_IMPLEMENTATION。全局状态：COMPLETION_ACCURACY_ONLY，未升级。**

实际起点与审阅提交均为 `b0a2edcac216af53b417be2a3b922c4deff98185`，分支 `research/dac-capacitance-characterization-20261114`，开始时工作树干净。已核对既有 REVIEW_PACKET §8 与全部六个起始权重。旧实验、原稿、源数据、求解记录及原权重未覆盖、未回退。最终交付提交由 Git 提交本身及归档外的交付回执标识；避免在提交内容中嵌入无法自洽的自身 SHA。

## 执行结论与覆盖

计划 12 个 U=2000 续训终点；**启动 0，完成 0，训练失败 0，未启动 12**。另有 **2 次预检失败及 1 次依赖性的冻结失败**，不能把这些误称为 3 个训练失败。pilot 未启动，正式续训更新数为零，新增终点评测为零。预检确实执行了起点 forward/隐藏标签扰动/原 Full 入口对照，CPU 全部计入账本，但这些检查不是完整 step-0 误差评测，不能填入 E[a,0]。

因此 D[Full]、D[binary]、I、G 及 C、种子一致性、置信区间都为 **NA（未测）**，不是零、无改善或 Full 失败。本次不能回答低预算训练是否有效，不能建立或否证局部 Full 价值；也不能声称预算不足。旧日志线性估计全部续训约 3887.2 秒，但 pilot 未运行，保守可行性未验证。

## 阻塞、唯一修复与停止依据

1. `prepare.log`：冻结索引写 JSON 时 `numpy.int64` 不可序列化。此前六个权重加载及隐藏标签检查通过，没有训练。唯一实现修复将 geometry_order 返回的索引转为 Python int，数值、顺序、科学协议均未改变。初次不完整输出位于 `invalid_prepare/`，没有删除，失败 CPU 已入账。
2. `prepare_repaired.log`：原采样器与重建编码的 `delta` 普通数组相等断言失败。后续**只读诊断**表明三个种子的首步四家族，所有检查字段在把 NaN 哨兵视为相同后完全一致。原 `unified/basis.py` 明确定义不可用解析基位置为 NaN，`valid` 屏蔽它们；`np.array_equal` 默认 NaN 不等于自身。这里是新预检的错误判定，不是原模型数值发散、标签泄漏或已证明的采样失配。
3. 冻结命令在前序失败后仍被尝试；CPU 串行锁只限制并发，不检查前序成功。冻结因 `DATA_MANIFEST.json` 缺失退出，未生成 `FREEZE_MANIFEST.json`。这是调度没有成功依赖门的缺陷，不隐去其执行记录。没有训练命令运行。

任务书只允许一次实现修复，该额度已用于第1项。本次未再次修改检查或重跑训练链；没有因修复容易或预算尚有余量擅自放宽该约束。剩余工作仅做只读诊断、清晰失败交付及最新用户明确授权的文稿版本与远端推送。若另行授权新一轮，实现上应使用带 NaN 语义的比较，并使各阶段在前序成功后才可启动；这不是本轮已完成的修复，也不是建议增加模型/搜索。

## 原设置、拟议对照与已经核验的事实

- 原 FEM reference 使用16张153节点源训练表；原 H 协议 mcar/block/extrapolation，缺失率 .1/.3/.5/.7，支持数138/107/77/46；整宽留出支持136。B4/8/16/32 都低于原范围。设置层面失配仍成立，致因尚未证实。
- Full/binary 各源种子0/1/2的完整 checkpoint strict load；Full 对原 scorer 入口逐值一致。binary 使用原 SimpleControl 类完整权重，非仅 trunk warm start。原 optimizer 状态不存在，拟议 H/L 同样重置 AdamW。源配置 `eta=0`，四家族固定等权，dropout0，归一化 Huber(delta1)，span_weight=False。
- 原源 checkpoint 有12000步训练；此轮拟议追加2000步、lr2e-4、weight_decay1e-4、clip1、全参数训练。lineage 中用于**加载**的 config 把 init_from 清空以禁止再次 warm-start；历史原 config 由原 FROZEN 路径及哈希引用，不应把清空值解读为历史没有 warm start。
- 已生成的24,000个训练 episode 索引在只读诊断中逐项通过原 mask 重建、S_L⊆S_H、|S_L|=B、S_L∩Q=∅及 train ID检查。各seed拟议每终点 Q 节点访问总数为 [397748, 395534, 398951]；同seed四条件相同，**不是三种子必须具有相同 Q 总数**。每步所有条件的四家族和 query-loss 权重匹配。节点反复访问数不等于独立新标签数；此轮实际新训练访问数为零。
- H 保留原采样器；L 从H支持内使用 geometry_order 覆盖前缀，B由独立 RNG611140+seed 均匀采样。原H的Q不变，移除的支持点不加入loss。这会同时改变观测数量与覆盖，是低支持协议效应，不是纯数量因果识别。
- 拟议主评测复用原16确认表×3数据seed×4预算=192个固定S/Q单元；原支持遗忘检查为16表×4协议=64单元、缺失率.3、data_seed11。未读取其误差挑选方案；未做新的确认预测。

## 计划状态与预登记口径

`FROZEN_PLAN.yaml`、`EPISODE_PLAN.json.gz`、`EVALUATION_PLAN.json`、`RESOURCE_BUDGET.json`、`CHECKPOINT_LINEAGE.json`、`PROTOCOL_DIFF.md` 是**未完成冻结尝试的保留产物**。虽然计划中字段名为 freeze_utc，完整预检/数据清单/执行哈希冻结没有成功，不能称为已冻结且可执行的成功研究。`FREEZE_MANIFEST.json` 缺失；训练入口按设计拒绝运行。`EXECUTION_STATUS.json` 是最终状态。保留这些文件便于审核，不补造成功冻结证据。

拟议主指标：每表/数据seed/B先计算非零真值分量的 query NRMSE 均值，再平均数据seed、同 process-layer 组内表、各组、四预算；预算等权。旧E1是按process/family/component先汇总SSE/SY再开方的macro，二者不可混称同一数字。C=E0−EH，D=EH−EL，I=D_Full−D_binary，G=E_binary_L−E_Full_L。I>0并不推出G>0。B4需单列但不是唯一主指标。没有数据，未进行 bootstrap，未生成误差图或效应图。

旧方案拟定的10%/5%启发阈值没有工程容差来源，不作为EDA充分性门槛；旧验证阈值0.2882/0.2908及首次已测B4下限结论原样保留，没有测B1–3。旧MLP/CNP等结果仍在原 REVIEW_PACKET，不能与尚不存在的新Full终点组成“公平训练”胜出表。

## 资源与成本口径

完整数值见 `RESOURCE_LEDGER.csv` 和 `RESOURCE_SUMMARY.json`（含失败）。预算监督器一次只允许一个单线程进程，禁用CUDA；使用 wait 后 RUSAGE_CHILDREN 的进程树CPU，单列监督器SELF；/proc进程组和RLIMIT_CPU提供硬限制。没有把父子CPU重复相加。新论文LaTeX编译由监督器子进程显式等待，也计入；轻量文件生成/最终打包行政工作以单列60秒保守费用覆盖，不伪称实测。实际计算CPU、保守预算扣账CPU、工作进程墙钟和跨阶段总墙钟分别列出。无新增场求解、GPU、迁移、基线拟合、PEX/STA。

## 论文决策与停止

保留限定规则补全与已测原生接口保真度主张。继续撤下普遍复杂门控必要性、整体表征效率、签核准确性和真实求解加速主张。本次不提供额外机制支持，也不以程序失败否证失配假说。保持停止 Full 扩展的现有研究决策；未完成的机制验证若要重新开展，需要另行明确授权，不能利用剩余预算自动续跑。

旧P99 slack约+7.64 ps差异是旧模型、特定布局与参考规则误差口径的已有结果，不是本次实测、更不是芯片实际时序退化；本次没有修复它的证据。迁移与adapted AttentionCap失败边界不变，未重新开展其语义审计或数值实验。新版本论文只补充训练支持范围和机制证据缺口，原论文及全部旧结果保留。

## 文件导航

同目录 `PAPER_DELTA.md`、`REPRODUCE.md`、`FIGURES_NOT_GENERATED.md`；结果目录中的逐种子NA表、12单元状态、诊断、支持/Q计数、源权重路径哈希、全部日志与账本。新版可编辑稿 `paper/dac_support_revision_20261114/main.tex` / `DAC_REWRITE.md`，PDF同目录。轻量包含旧 REVIEW_PACKET、原 FINAL_DECISION/CLAIM_EVIDENCE 及新状态；原大权重仅引用路径与SHA256。

## 最终计量快照

实测子进程树及监督CPU共 **90.849287秒（0.025236 core-hours）**；另计60秒行政保守费用，总预算扣账 **150.849287秒（0.041903 core-hours）**，距14,400秒硬限剩余14249.150713秒。五个被监督工作进程墙钟合计103.720秒；首个计量阶段启动至最后阶段退出为458秒（包含中间文稿编写间隔，不含最初只读审计及最终Git传输）。正式训练/pilot/终点评测均为零。
