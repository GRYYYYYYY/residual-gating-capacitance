"""Render a self-contained review from derived CSVs; no experiments."""
import csv,json
from pathlib import Path
D=Path(__file__).resolve().parent
read=lambda n:list(csv.DictReader((D/n).open()))
same=read('same_budget.csv');cover=read('coverage_cost.csv');delta=read('downstream_deltas.csv');ds=read('downstream_delta_summary.csv');reverse=read('reverse_transfer.csv');freezes=json.loads((D/'threshold_freeze.json').read_text())
def table(h,rs):return '| '+' | '.join(h)+' |\n| '+' | '.join(['---']*len(h))+' |\n'+''.join('| '+' | '.join(str(x) for x in r)+' |\n' for r in rs)
def fmt(x,n=6):return 'NA' if x in ('',None) else f'{float(x):.{n}g}'
labels={'anchor':'Anchor','cmi':'CMI','gp':'调参 GP','affine':'local affine','residual':'ungated residual','binary':'binary','full':'Full','pruned':'pruned（未选部署）','mlp_adapt':'适配 MLP','cnp':'CNP','attentioncap_adapted':'adapted AttentionCap','pchip':'PCHIP/回退','mlp_zero':'source-only MLP','attentioncap_zero':'source-only AttentionCap'}
methods=list(labels)[:11]
accuracy=''
for s,bs in [('public',[4,8]),('reference',[4,8,16,32,64]),('to_asap7',[4,8,16,32,64])]:
 rr=[]
 for m in methods:
  rr.append([labels[m]]+[fmt(next((r['macro_nrmse'] for r in same if (r['setting'],r['method'],int(r['budget']))==(s,m,b)),None)) for b in bs])
 accuracy+=f'### {s}：固定预算 macro NRMSE\n\n'+table(['方法']+[f'B={b}' for b in bs],rr)+'\n'
cov=[]
for m in methods:
 rr=[]
 for s in ('public','reference','to_asap7'):
  z=next((r for r in cover if (r['setting'],r['method'],r['threshold_index'])==(s,m,'1')),None)
  rr.append('未执行' if z is None else f"{z['reached']}/{z['defined']} ({100*float(z['coverage_defined']):.2f}%)")
 cov.append([labels[m]]+rr)
coverage_table=table(['方法','Public（991 条有定义轨迹）','FEM（48 条）','迁移（24 条）'],cov)
ns=[]
for comparator in ('cmi','anchor','affine','binary'):
 for metric in ('net_cap_nrmse','ws_abs_ns','slack_p99_ns','tns_abs_ns','false_positive'):
  r=next(r for r in ds if (r['comparator'],r['metric'])==(comparator,metric))
  ns.append([comparator,metric,f"{r['full_better']}/{r['ties']}/{r['full_worse']}",fmt(r['min_signed_difference']),fmt(r['max_signed_difference']),fmt(r['relative_percent_min']),fmt(r['relative_percent_max'])])
native_table=table(['对照','指标','Full 优/平/劣','差值最小','差值最大','相对差最小%','相对差最大%'],ns)
per=[]
for case in sorted({r['case'] for r in delta}):
 for b in (4,8):
  row=[case,b]
  for c,m in [('cmi','net_cap_nrmse'),('binary','net_cap_nrmse'),('cmi','ws_abs_ns'),('binary','ws_abs_ns')]:
   z=next(r for r in delta if (r['case'],r['budget'],r['data_seed'],r['comparator'],r['metric'])==(case,str(b),'mean',c,m));row.append(f"{fmt(z['full_minus_comparator'])} ({fmt(z['relative_difference_percent'],5)}%)")
  per.append(row)
per_table=table(['布局','B','净 C Δ vs CMI','净 C Δ vs binary','WS Δ(ns) vs CMI','WS Δ(ns) vs binary'],per)
threshold_table=table(['域','Q25','Q50（本次重点）','Q75','验证总表/可评测/有定义'],[[f['setting']]+[f'{v:.17g}' for v in f['thresholds']]+[f"{f['validation_tables_total']}/{f['validation_eligible']}/{f['validation_defined']}"] for f in freezes])
revtable=table(['B','零目标 MLP NRMSE','适配 MLP NRMSE','适配+补表秒/表'],[[b,fmt(next(r['macro_nrmse'] for r in reverse if r['method']=='mlp_zero' and r['budget']==str(b))),fmt(next(r['macro_nrmse'] for r in reverse if r['method']=='mlp_adapt' and r['budget']==str(b))),fmt(next(r['combined_completion_adaptation_wall_seconds'] for r in reverse if r['method']=='mlp_adapt' and r['budget']==str(b)))] for b in (4,8,16,32,64)])
appendix=table(['域','方法','B/目标标签(Q)','NRMSE','纯适配秒','纯补表秒','适配+补表秒','fine CPU秒','validated CPU秒'],[[r['setting'],r['method'],f"{r['budget']}/{r['target_labels_for_Q']}",fmt(r['macro_nrmse']),fmt(r['adaptation_only_wall_seconds']),fmt(r['completion_without_adaptation_wall_seconds']),fmt(r['combined_completion_adaptation_wall_seconds']),fmt(r['fine_cpu_seconds_mean']),fmt(r['validated_cpu_seconds_mean'])] for r in same])
text=f'''# DAC 电容规则补全：有限证据整理与机制核对

**结论保持 `COMPLETION_ACCURACY_ONLY`。建议仅考虑一次支持集规模失配的受限因子验证；本次未启动，不能据此保留普遍 Full 优势主张。**

起点完整 SHA：`269a86b15a5619400447266c186485a641b8a8ef`。开始时 HEAD 与之相同，工作区干净。工作分支为 `research/dac-capacitance-characterization-20261114`。本文、CSV 和归档均为新增派生材料；没有新训练、推理、场求解、PEX/STA 或超参数搜索。只做已有记录汇总、哈希核对和不执行模型的采样数量重建。随包的 `FINAL_DECISION.md`、`CLAIM_EVIDENCE.csv`、`main.pdf` 是该起点的**原样副本**，新增审阅限定写在本文，不静默改写历史论文或结论。

## 1. 审阅范围与关键结论

1. 原 E1–E4 的主要记录确实完成：主矩阵 38,208 条（其中几何覆盖 primary 28,656 条，其他为 random/curvature），AttentionCap 720 条，反向 MLP 240 条，训练种子敏感性 7,164 条；原生 240 个预算状态和 8 个 golden 状态完成。CNP 有完整结果，不能说它未执行，也不能因数值较弱而移出主表。
2. FEM 48 条、迁移 24 条轨迹上，Full、binary、适配 MLP 的**首个已测达标预算全为 B=4**。因此 192/48=4、96/24=4 正是首档下限效应。ungated 和 pruned 在这两个中位门槛下也全部首档达标。不能把 4 解释为最低必要样本量，不能据此排序它们的最优表征效率。
3. 原 FEM/迁移 Full 与匹配控制的训练表均为 153 节点；缺失率采样产生 46/77/107/138 个观测，整宽留出产生 136 个观测。B=4/8/16/32 低于该设置的观测数量范围，B=64 位于范围内但不是训练的离散数量。确认表为 128 节点，网格、层、支持几何分布也发生变化。**数量失配存在，但“失配导致 Full 失败”仍是待验证机制。**
4. 固定预算补全相对数值方法的收益保留；相对 binary 的下游增益并不普遍，部分尾部指标退化。旧结果不能支持完整门控普遍必要、可部署的自动达标停止规则或端到端加速。
5. 数据与计时有明确边界：既有计时未拆分适配和推理，NA 必须保留；阈值是源验证 anchor 误差分位数，无 STA 应用容差依据；最低已测预算由封存 Q 的真值事后判定，是评估统计量，**不是实际在线停止策略**。

## 2. 同预算方法状态与完整数值

Primary 比较统一使用 farthest 几何覆盖支持集、数据种子 11/29/47、固定 Q；所有学习方法使用三成员均值。Public 每预算 338 表×3=1,014 条；FEM 为 16×3=48 条；迁移为 8×3=24 条。Public 的 B16/32/64 无合格表，属于人口不可行，不是已完成，也不补零。所有主比较方法共享 S、Q 和每几何返回的标签分量；FEM 三分量，Public 两分量。训练条件与调参努力并不完全一致，见第 5 节。

| 方法 | public B4/8 | reference、to_asap7 B4/8/16/32/64 | 实现/选择限定 |
|---|---|---|---|
| Anchor、CMI | 完成 | 完成 | 同 S；原生 rank1 下两者相同，不是两份独立证据 |
| GP | 完成 | 完成 | 6 组 length/ridge，源验证预算协议选取 |
| local affine | 完成 | 完成 | 邻居数 4/8/8，沿用旧源验证选择，非本轮重新搜索 |
| ungated residual、binary、Full | 完成 | 完成 | 18 个控制+9 个 Full 实际权重核验；无控制重训 |
| pruned | 完成 | 完成 | 同 Full 权重、linear-only 字典；三域验证均未选为部署版本 |
| 适配 MLP | 完成 | 完成 | 仅 S 上 200 步/成员；不同 source 训练预算，非原作者复现 |
| CNP | 完成 | 完成 | mean-context 条件化；无目标参数更新；不是 ANP |
| adapted AttentionCap | 未执行 | 完成 | 官方网络的共同 FEM 组件监督适配，不是原论文 benchmark |
| PCHIP | 完成 | 完成回退行 | rank2 行回退 linear，不称真正 rank2 PCHIP |
| source-only MLP | 完成 | 完成 | Q 预测不读目标值；不是同信息预算主对照 |
| source-only AttentionCap | 未执行 | 完成 | 仅供迁移诊断；可有极大误差 |
| ANP、Flash-CNNCap 数值比较 | 未执行 | 未执行 | CNP 已满足通用条件化项；Flash 仅范围比较 |

实际完成/未执行/预算不可行和原生执行范围逐项列于 `method_status.csv`。原生仅执行 CMI/Anchor/affine/binary/Full；不能把表预测完成说成 GP、MLP、CNP、pruned 或 AttentionCap 的原生部署已完成。

主误差为 process/family/component 内先累加平方误差及平方真值、再取平方根并对有定义分量等权平均的 macro NRMSE。它不同于逐轨迹达标误差。零真值组仅排除未定义相对量，保留绝对误差。下面所有数值来自原始记录重新汇总，已与原 summary 逐项核对。

{accuracy}

完整的 164 个预算单元，包括额外的 PCHIP 和 source-only 控制，及目标标签量、原生 MAE、纯适配/纯补表/合计时间、fine/validated CPU 成本见 `same_budget.csv`；本文附录也列出关键列。GP 选择为 public (length=1,ridge=1e-4)、reference/transfer (length=2,ridge=1e-6)。

### 计时解释

- 非适配方法的纯适配耗时填 0，含义是**没有该步骤**；其 callable 实测时间记作补表时间，包含该方法的支持特征、数值分支和成员预测。
- 此处“适配步数”指神经参数优化。GP、affine 等仍在 S 上构建后验或回归拟合，其数值求解耗时计入补表；0 个神经更新步骤不表示没有目标数据拟合工作。
- 适配 MLP/AttentionCap 的原始字段只有 `prediction_and_adaptation_wall_seconds`，覆盖复制模型、特征构建、目标优化和预测等。因此纯适配、剔除适配后的纯补表均标 NA；**不能用另一个 zero-shot 调用耗时相减伪造拆分**。
- 选点累计时间未含最初 population/初始化；模型装载也不在每次 callable 时间内。已有 `component_runtime_profile.csv` 是每域一个验证表、Full/pruned 的局部分解，不能外推为全部模型逐轨迹分解。
- source-only 行的“0 标签”只指 Q 的预测信息。调用器仍将 B 个观测值写回完整表；如果交付整个含原观测值的规则表，这 B 个观测不是免费的。它们不参与同信息量阈值效率排序。

## 3. 阈值定义、冻结与预算下限

对每个源验证表，在 seed=11、coverage 支持 B=8（代码允许最大可行 B≤8；实际参与此项的表均为 8）下，先算每个非零真值分量 `sqrt(sum_Q(error²)/sum_Q(y²))`，再在该表的有定义分量间取均值。对这些**逐表误差**取 NumPy 线性分位数 Q25/Q50/Q75，而非对 confirmation 或 STA 调容差：

{threshold_table}

reference 的 24 张源验证表包含 16 张 153 节点与 8 张 128 节点表，覆盖已有两个材料栈；to_asap7 的 12 张全部来自 **FreePDK15 源域**，8 张 153 节点、4 张 128 节点。Public 246 张验证表中一张 n=2 不可评测，另四张被评测 Q 的全部相对分量未定义，因此 241 个误差进入分位数。

三份 `selected_*.json` 在提交 `14865375475a067364fe6f96483af3712882e752` 中已经存在，提交时间 **2026-11-13 22:52:03 UTC**，与现存值、confirmation FROZEN 内的选择值完全相同。selection 本地 mtime 分别为 22:49:41、22:48:42、22:48:44；reference confirmation FROZEN 为 22:52:15，transfer 为 22:55:10。Public 首次失败尝试的 FROZEN 为 22:53:25，成功重跑为 23:06:40。mtime 是本地辅助记录，不当作独立可信时间戳；冻结提交、输入哈希和运行配置的对应关系保存在 `threshold_freeze.json`。

**应用依据：无预先认证的 STA/签核误差容差。** 0.2882/0.2908 是上述相对误差统计的中位数，不能解释为行业要求、允许的芯片时序误差或 MAPE。所有三个分位门槛均保留，未为本审阅另选阈值。

`threshold_trajectories.csv` 提供 36,054 行：每个 setting/method/table/data_seed/threshold 的达标状态、首档误差、首档是否达标、首次已测达标预算、累计唯一查询、fine/validated 成本、对应 callable 耗时，以及未达标时最大已测预算成本。不能在不同 B 的累计快照间重复累加同一条轨迹的购买次数。

| 域/Q50 | 方法 | 达标轨迹 | 首档 B4 已达标 | 累计查询 | 累计 fine CPU 秒 |
|---|---|---|---|---|---|
| FEM | Anchor | 48/48 | 12/48 | 632 | 3567.810261 |
| FEM | Full/binary/适配 MLP（各自） | 48/48 | 48/48 | 192 | 1367.891633 |
| 迁移 | Anchor | 24/24 | 6/24 | 312 | 2005.585372 |
| 迁移 | Full/binary/适配 MLP（各自） | 24/24 | 24/24 | 96 | 765.412983 |

这证明它们在最先测量的 B4 已满足该门槛；没有 B1/2/3 证据，因此不证明它们需要恰好四点，也无法分辨谁在未测预算下更省样本。同样不能说“达到相同误差只需 Full”——多个简单模型已触碰相同下限。B4 的具体误差仍可不同：FEM Full 0.123338，适配 MLP 0.0515023；迁移 Full 0.118243，适配 MLP 0.0477281。

## 4. 成功覆盖、删失与成本口径

以下是在同一统计人口、Q50 门槛、各域最大已测预算以内的达标覆盖；不是只有成功样本的误差均值：

{coverage_table}

Public 全预定人口为 1,014 条，所有方法同样有 23 条 Q 相对误差全未定义，故有定义分母为 991；这些并非执行失败。`coverage_cost.csv` 同时给出 `reached/defined` 和 `reached/all scheduled` 下界（Full 957/1014=94.38%），后者不把未定义者伪装成数值失败。所有预定方法预算记录无缺失、无科学执行失败。两个 n=2 public confirmation 表在所有方法上共同排除，Public 高预算没有可行人口。

首达累计成本只有在所有轨迹均达标时才覆盖全人群。上表 FEM/迁移 Full、Anchor、binary、MLP 的总数确实包含全部 48/24 条；Public 以及 CNP 的成功样本成本不能这样解读。例：FEM CNP 只有 38/48 条达标，成功者 fine CPU 和为 1222.448801 秒；若把其余 10 条按实际已测最大 B64 保留，回溯“首次达标、否则用到最大预算”的全人口成本为 **5141.324966 秒、820 次查询**。迁移 CNP 为 18/24 达标，成功者成本 606.821802 秒，全人口回溯口径为 **2619.766802 秒、456 次查询**。只报成功者会使其看起来虚假地比 Full 更省。

此外，全矩阵本来为每条轨迹生成到最大预算的快照，并未在首达时实际停止。`coverage_cost.csv` 同时提供最大预算全人口工作：FEM 每方法 3072 次/17770.049830 fine CPU 秒，迁移 1536 次/10037.698479 秒；这是同一支持轨迹的成本回放，**不能在方法之间相加成新求解支出**。首达/删失策略需要事后查看 Q，不能直接部署为免验证的采样停止器。

每条轨迹初始四点均计入 B 和求解成本。一点返回所有标签分量，不能把三分量计成三次独立几何查询。fine CPU 来自历史 fine 求解回执，validated 是 coarse+fine+wide 合计；两种口径分开，cached charged_wall=0 不代表求解免费。本次没有新求解器墙钟测量。CPU 秒、目标适配墙钟、原生提取墙钟、历史预训练成本不混加。Public 为已存规则访问模拟，求解成本未知而非零。

成功重跑前的 public fork 执行停滞消耗 **770.07 CPU 秒**，没有可接受预测行；单列失败成本，不作为“不达标模型”或成功轨迹。首次导出遇到 n<4 在输出规则前停止，旧目录保留；native 调度交接有一条墙钟由文件时间重建，原 extraction 计时仍在。上述记录及原始大结果的路径/哈希由 `input_references.csv` 和其引用的完整 native/delivery manifest 提供。

AttentionCap 原始行没有 validated CPU 字段，本审阅在逐项确认 S/Q 与 Full 相同后，从同一批购买几何补出该项**派生的历史成本**；没有修改原始记录，也不称为新增计时。原 source 生成/训练成本仍存在未知项，不能声称总成本优势。

## 5. 实际 checkpoint 的训练支持集核对

`training_checkpoints.csv` 逐个列出 72 个实际相关 checkpoint：9 个 Full、18 个 matched controls、9 个 warm-start、24 个新 MLP/CNP 训练候选、8 个 AttentionCap 候选、4 个反向 MLP 候选。选中用于 confirmation 的和只用于源验证选择的候选均明确区分；pruned 复用 Full，不虚构额外 checkpoint。每个权重核对 SHA 和 COMPLETED/result 记录；训练数据、步数、配置/日志位置、角色均列出。`training_tables.csv` 列出唯一源池表身份、节点数和数值内容哈希。

| 训练族 | 训练表/节点 | episode 或监督方式 | 支持数量范围/集合 | 本轮目标更新 |
|---|---|---|---|---|
| Public Full/ungated/binary | 1051 表：226×13、819×12、6×2 | 家族→process→表均衡；mcar/block/extrapolation | 1,4,6,7,8,9,11,12；B4 在原设置内 | 无 |
| FEM Full/ungated/binary | 16×153 | 同上，外加整宽留出；阶段2 12000步 | 46,77,107,136,138 | 无 |
| 迁移 Full/ungated/binary | 8×153，仅 FreePDK15 | 同上；阶段2 12000步 | 46,77,107,136,138 | 无 |
| FEM/迁移 warm-start | 相同源池，2000步 | mcar/block/extrapolation；10/30/50/70%缺失 | 46,77,107,138 | 无 |
| Public warm-start | 相同源池，2000步 | 同样缺失比例 | 与 public 上表相同 | 无 |
| 新 CNP | 同一源训练表，3000步 | 家族均衡、家族内均匀表；mean context | 从 2/4/8/16/32/64 抽样并截至 n−1 | 无；读 S 条件化 |
| 新直接 MLP | 同一源训练表，3000步 | 同一随机分割，但网络不读 context；loss 在补集 | 不适用“上下文训练”；B只影响训练 loss 子集 | 200步/成员，仅 S |
| adapted AttentionCap | FEM16表/迁移8表，3000步 | 随机表、32几何监督 minibatch，官方对称 Transformer/Laplacian head | 32 是训练样本批量，不是32个条件观测 | 50步/成员，仅 S |
| 反向直接 MLP | ASAP7 8×153，3000步 | 每家族取表，全表监督 loss | 不适用上下文数 | 200步/成员，仅 S |

153 节点的非 width 情况用 `observed = 153 − round(153 × missing_ratio)`：10%→138，30%→107，50%→77，70%→46。9 个宽度、每宽17点，整宽留出后 136；width 分支不按 ratio 制造局部曲线。Full/control 的旧 warm-start 也未覆盖 B4/8/16/32，因此不能用 warm-start 消除失配疑问。Public 24000 阶段2步，FEM/迁移12000；新基线3000步，源采样 process 均衡也不同，不可称全体模型匹配了训练预算。

**证据强度与源码限制：**训练日志记录了步数和 loss，但没有逐 episode 的支持点数。`training_support_histogram.csv` 是按训练 RNG 和采样器重建的数量，不冒充历史遥测；不执行编码器、模型或优化。历史 FEM 数据文件在原 pdkcap 路径找到，SHA 与训练 FROZEN 相符；发布副本的元数据序列化不同，但训练表次序、坐标和标签逐项完全一致。`unified/train.py` 的哈希与所有 Full FROZEN 一致，实际本地控制 runner 哈希也一致；旧 mask snapshot 与发布 mask 在 768 个几何/协议/比例/种子组合上完全一致。

reference/transfer 的旧 `unified/episodes.py` 记录哈希与当前编码器不同，未恢复该旧文件的字节快照；当前及保留训练代码使用的比例常量为 .1/.3/.5/.7。此限制在 `source_audit.csv` 明示，故数量结论是**训练设置/采样逻辑层面的重建，不是完整旧编码器字节重放或逐step实测**。它不改变已核验的权重和本轮实际预测；也不允许声称看到了所有旧训练 episode。

**已有低预算训练：CNP 有；Public 原模型也有小支持。FEM/迁移 Full、ungated、binary 没有本轮低预算再训练。** 直接 MLP 的目标拟合、AttentionCap 的目标拟合不是 Full 的低预算 episode 训练。CNP 已经过小上下文训练却仍表现有限，说明“覆盖小 B”不是充分条件。当前的预算失配还伴随 153→128 节点及缺失协议→固定 Q/coverage 采样变化；不能将全部性能差异单因果归于支持数量。

## 6. 原生下游幅度、平局、尾部与表范围

参考是同一已布线/连接 ODB、SDC、Liberty、工具版本下的完整原规则提取和 STA。golden C/R 精确重放，候选 R 不变；不是实际芯片改进、时序闭合或签核真值。本轮 budget 仅作用于指定 holdout，其他规则仍保留完整表征值。

按每 layout×budget 对三个数据种子取均值，共16个单元。下表 Δ = Full误差 − 对照误差，负数更好；相对差为 `100×Δ/abs(对照)`。分母为零时 NA；绝不填0或无穷大。平局采用 `abs(Δ)≤max(1e−12,1e−9×max(abs(Full),abs(对照)))`，只是数值等同判断，不是统计显著性或工程等效边界。

{per_table}

所有逐种子、逐条件、四个对照和19项指标的 4,864 行记录在 `downstream_deltas.csv`，同时包含有符号差和差的绝对值。下面汇总同时保留平局、劣化和零分母：

{native_table}

对 CMI 的净 C NRMSE 相对降幅为 78.41%–92.54%，WS 误差绝对减少 0.000318245–0.076623744 ns；这些绝对量比“16/16”更能判断工程幅度。它们不意味着所有决策指标都改善：对 CMI 的 false-positive 在3/16单元变差，GF180 AES B8 增加平均0.6667个端点。

对 binary，净 C 只有6/16改善、10/16退化，WS 为4/16改善、12/16退化，无数值平局。P99 slack 在10/16单元更差；最坏 GF180 ibex B4 增加 **0.007643287 ns（7.643 ps）**，WS绝对偏差增加 **0.005903403 ns**，TNS绝对偏差增加 **8.413248698 ns**。其 false-negative 与 binary 16/16平局，false-positive 有2/16退化。小分母会产生数百百分比相对差，必须与绝对量一起读。布局/规则库共享，16个单元不构成16个独立工艺样本。

### 原84表到83表的对应

`downstream_table_map.csv` 逐表给出 study_id、upstream_id、source/process/family/metal、节点数、是否纳入、B4/B8实际购买数和排除理由；84表均找到唯一 upstream 对应并验证逐坐标标签相等。83个纳入表各有2预算×3种子的共同 S/Q；五种原生方法完全相同。

唯一排除：study `e07160f8c4c1dd482e54b279` ↔ upstream `d8648179761870818e46ba61`，ASAP7、OVER、metal10、**2节点**。预先协议 n<4 不可行，不能同时满足既定支持/封存评测要求，因此对所有方法保持 golden。不是因为某模型失败而排除。原生83表与table-confirmation人口不同：只有重叠部分的600个模型/预算/种子 episode做过导出逐预测一致性检查；不能把“83表部署完成”说成“83表全都属于原340表确认集”。

## 7. 相关工作与迁移：实际执行内容

### Adapted AttentionCap

复用官方源码固定提交 `59a48fd1f90e668c061fa27fb22b53ddad3db499` 的对称注意力与 Laplacian head，2层/4头/64维；增加可复原的导体矩形、材料层和外边界 token，仅监督其他方法也有的三个 FEM 分量，**不赠送全矩阵标签**。每域训练16/8表，学习率候选 .001/.0003、3000步；seed0选配置后补seed1/2。目标优化候选0/50/200步在24/12张源验证表选择；最终两域50步/成员，lr=.0003（reference）和 .001（transfer）。每个 S 重新复制源模型并拟合，不用额外 Q 标签早停。

reference adapted B4→64 NRMSE：**0.454598、0.225574、0.202513、0.167701、0.165695**；其 source-only 为0.455131。transfer adapted 为 **6.875326、0.319931、0.211971、0.215341、0.179096**；其 source-only 为 **71227.482013**。极大值是实际有限数值结果，不以“执行成功”掩盖性能失败，也不裁掉。transfer B4 的个别表/种子逐表误差可达40.8146（r3-asap7-M7-OVERUNDER, seed29）；source-only 的 r3-asap7-M8-DIAGUNDER 出现更严重外推误差。没有证据将这一适配的坏结果推广为原论文算法在其原任务上无效。

两个域共720条（adapted/source-only各360），执行失败0；公共rank1任务没有做 AttentionCap。合计适配+补表约0.62–1.13秒/表，纯适配拆分未知。该网络的训练监督、材料/边界适配、数据规模与原论文不同，所以只称 adapted official baseline。

### CNP 与直接 MLP

CNP 完成2388条 primary预算记录，三域完整，无目标参数更新；误差和成功覆盖都已列入主表。它是确定性均值聚合条件化基线，不是ANP。CNP没有因未达门槛而被标记未执行。

Tsai启发的MLP使用现有几何/材料特征，在相同 S 上200步适配；不是其原代码、切片流程或完整netlist装配的复现。已有论文的未见厚度泛化不要求每个厚度重训，不能反向描述来制造新颖性。直接回归与有限目标拟合形成强反例，Full的“参数冻结”并不意味着不需要目标观测。

### 反向 ASAP7→FreePDK15

仅直接 MLP：8张ASAP7训练、12张ASAP7源验证、8张FreePDK15确认表；3000步，两个LR候选，最终 .001，三成员；每个目标 S 200步/成员。240条记录全部有限/ok；不是 Full 的双向迁移，也不是两种完整方法都跨工艺胜出。

{revtable}

跨全部预算池化的 adapted NRMSE 为0.04078487，source-only为0.44136761；前者不是五个表中NRMSE的算术均值，也不应取代逐预算结果。标签预算每个目标几何返回三分量；源表征数据相同但目标优化实际花费单列。

`reverse_transfer.csv` 同时列出 fine/validated 求解成本：它们由逐项匹配 reference 中 FreePDK15 目标表的同一 S/Q 回放得到，是新增派生列而非新增求解或计时。

Flash-CNNCap仍仅保持3D窗口→贡献图/矩阵/网表与本任务固定规则网格补全的范围比较。本轮没有新增不匹配图像实验，没有原Flash数值结果可列。保留通用条件化、残差和混合提取的已有先例，不声称首次提出这些概念。

## 8. 研究决策与唯一建议方案（未启动）

**仍成立：**在声明的公共rank1人群和固定目标观测预算下，训练过的支持条件化模型明显改善数值补全；原生规则导出接口可复现，在83表替换、固定布局条件下提高对完整规则参考的净电容与多数误差指标保真度；Full、binary、直接目标适配有不同误差/计算代价取舍。

**应撤下或继续不作：**Full普遍优于强数值/学习基线；复杂门控普遍必要；4个观测为最低必要样本量；由首达回放推导可部署的在线达标停止；whole-PDK成本、实测求解器墙钟/端到端加速、广泛跨工艺、3D或签核精度优势。Public长训练与新MLP/CNP短训练、不同采样预算，限制其架构优越性解读。旧负结果不因失配假说而撤销。

**是否值得补一次：有针对性价值，但只作为失配机制诊断。** 现有证据是清楚的设置层面失配，并非证明调好 Full 后必胜。建议的唯一实验是一个小型、匹配更新数的 **2架构×2支持数量分布×3训练种子** 因子对照，仅 FEM reference，最多12个续训终点；本次不运行。

预先冻结草案：

| 项目 | 唯一方案 |
|---|---|
| 起点 | 现有reference Full、binary各seed0/1/2权重；每个权重分叉到dense与sparse两臂；保留未经续训的原始结果作为参照 |
| 数据边界 | 原16张153节点训练表；原24张源验证表；原16张128节点确认表。无新增几何、场求解、目标标签、跨域训练；确认集已被看过，不称新盲测 |
| 唯一研究因子 | 训练支持数量：dense均匀选46/77/107/138，sparse均匀选4/8/16/32；两臂同一表顺序、同一geometry-only候选次序、同一固定loss-Q |
| 排除掩码形状混杂 | 每个训练episode先用共同RNG固定15个Q，其余138点使用同一coverage次序；支持取该次序的不同长度前缀，loss只用共同15个Q。dense/sparse都采用此新共同几何协议，不能拿不同mask形状当数量因果证据 |
| 训练预算 | 每个终点恰好2000次额外更新，4个家族/step，AdamW lr=2e-4、weight_decay=1e-4，原梯度裁剪1与损失/归一化，全部参数更新。两臂都重置优化器；无LR/结构/早停搜索，仅最终步 |
| 公平对照 | 同架构dense对sparse定位数量效应；同sparse下Full对binary定位门控增量；复用原Anchor/CMI/GP/affine/适配MLP/CNP记录作为同S/Q强参照。更新数相同不等于墙钟/FLOPs相同，均计时 |
| 验证评测 | 复用既有val S/Q、种子11和B4/8/16/32/64；固定主要机制统计为低B四点的macro NRMSE比值几何均值。所有种子均报，不挑最佳checkpoint |
| 有限机制门槛 | sparse相对本架构dense，低B几何均值误差比≤0.90，至少2/3种子同向，且B64误差比≤1.05。是未来预注册的决策阈值，不是由本轮新测结果调出 |
| Full保留门槛 | 即使数量效应成立，若sparse Full相对sparse binary低B误差改善不足5%，或组级不确定性仍不能区分，则停止Full复杂化，优先简单模型；不能仅凭训练更匹配就改成成本优势结论 |
| 确认与停止 | 若机制门槛不成立，停止并报告，不追加步数/搜索。成立才做一次既有confirmation的冻结评测（仍为已知人群），同时报告失败与B64退化。确认不支持则结束Full扩展；不自动做迁移、原生或新工艺外推 |
| 资源上限 | 4 CPU core-hours，最多2个单线程worker、8GB新增文件，零GPU、零场求解、零新增PEX/STA；单run 30分钟上限。运行前仅核实资源；超限/失败保留并停止，不改变冻结矩阵补跑至胜出 |

这一方案只比较支持数量，在所有臂都固定其它采样几何。它没有被本次授权启动；后续仍需用户决定是否开展。若不做这一次诊断，现有证据已足够建议**结束Full扩展**、保留受限补全与简单适配结果；没有理由继续无边界扩模型。即使诊断通过，也不会自动把 `COMPLETION_ACCURACY_ONLY` 升级为表征效率结论。

## 9. 修正、复现与归档说明

本审阅重算的164个预算单元和36054个门槛状态与原汇总一致，没有发现需要改写旧 headline 数字的汇总错误。需要明确补充的是预算下限、训练支持数量失配、Q事后达标不可当在线停止、CNP删失下的全人口成本、原生决策尾部退化，以及计时无法拆分。原 `FINAL_DECISION.md`/`CLAIM_EVIDENCE.csv` 作为历史快照保留；本文提供更严格的解释。AttentionCap validated CPU 的补全是同S历史成本派生，不是新测量。

必要文件：

| 文件 | 内容 |
|---|---|
| `same_budget.csv`, `method_status.csv` | 所有实际预算单元、误差、标签和成本；完成/未执行/回退/预算不可行 |
| `threshold_freeze.json`, `threshold_trajectories.csv`, `coverage_cost.csv` | 精确阈值与冻结证据；每轨迹首达/删失/初始计费；同人口覆盖 |
| `training_checkpoints.csv`, `training_tables.csv`, `training_support_histogram.csv`, `source_audit.csv` | 72权重及训练数据逐项索引、设置与重建范围、源码版本限制 |
| `downstream_table_map.csv`, `downstream_deltas.csv`, `downstream_delta_summary.csv` | 84↔83表对应；逐条件/逐seed绝对和相对差、平局与尾部 |
| `reverse_transfer.csv`, `component_runtime_profile.csv` | 反向迁移逐预算；已有局部计时剖面（非全体拆分） |
| `input_references.csv`, `provenance.json`, `verification.json` | 本地大文件路径与SHA、来源提交、交叉核验 |
| `FINAL_DECISION.md`, `CLAIM_EVIDENCE.csv`, `main.pdf` | 起点提交的原样审阅附件 |
| `build_review.py`, `verify_review.py`, `write_packet.py`, `package_review.py` | 只读重算和打包脚本；不包含实验启动命令 |
| `FILES.csv`, `SHA256SUMS` | 包内文件清单和SHA；不递归包含自己的哈希 |

从工作区根目录 `source experiments/dac_characterization_20261114/env.sh`，按 `build_review.py → verify_review.py → write_packet.py → package_review.py` 运行即可派生重建。脚本仅写本review目录及旁边的zip/校验文件，不修改任何原始结果；重建时先复制已交付审阅包以保留审阅版本。原始SPEF/大日志/权重不装入小包，按 `input_references.csv` 及所引用 native/delivery manifest 访问。小包无外部公开发布。

打包脚本拒绝覆盖已有 zip；重建归档时用 `package_review.py --archive 新路径.zip`。归档旁的 `.sha256` 和 `.manifest.json` 记录整个压缩包的哈希、大小及成员数量。

## 附录：完整预算、误差、标签和成本表

时间为每table/seed调用的平均秒；CPU成本为每轨迹的历史求解均值。`NA` 不等于0。adaptation-only/纯补表拆分未知的行仍提供实测合计。`B/目标标签(Q)` 中 source-only 行的后项为0，但完整表观测恢复仍需B，不能当免费部署。Public求解CPU成本未知。精确未舍入值及更多字段见CSV。

{appendix}
'''
(D/'REVIEW_PACKET.md').write_text(text)
print('REVIEW_PACKET.md',len(text.encode()),'bytes')
