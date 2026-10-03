# 数据库总目录（当前论文）

统一入口：`python -m capdata list`、`python -m capdata info DATASET`。
加载器默认只返回 train；确认集需要显式选择 `partition="confirmation"`，审计全表需要 `partition=None`。

| ID | 表/矩阵数 | 几何点数 | 划分 | 用途 |
|---|---:|---:|---|---|
| `public_rules_original` | 1713 | 20811 | {'train': 1116, 'val': 256, 'test': 341} | original public rules; audit provenance, not the headline training split |
| `public_rules_holdout` | 1713 | 20811 | {'train': 1061, 'val': 247, 'test': 321, 'holdout': 84} | headline public training; 84 downstream tables explicitly held out |
| `reference_original` | 32 | 4896 | {'train': 16, 'val': 8, 'test': 8} | reference-domain training; original 9x17 grid |
| `reference_round2` | 24 | 3672 | {'val': 8, 'confirmation': 16} | historical reference validation/retrospective cohort; keep version identity |
| `reference_round3` | 27 | 3456 | {'confirmation': 19, 'val': 8} | new midpoint 8x16 validation/confirmation/boundary contexts |
| `eval_public_retrospective_original` | 341 | 4143 | {'test': 341} | fixed evaluation cohort; never training data |
| `eval_reference_boundary_round3_edge` | 3 | 384 | {'confirmation': 3} | fixed evaluation cohort; never training data |
| `eval_reference_confirmation_round3_main` | 16 | 2048 | {'confirmation': 16} | fixed evaluation cohort; never training data |
| `eval_reference_retrospective_original` | 8 | 1224 | {'test': 8} | fixed evaluation cohort; never training data |
| `eval_reference_retrospective_round2` | 16 | 2448 | {'test': 16} | fixed evaluation cohort; never training data |
| `eval_to_asap7_boundary_round3_edge` | 2 | 256 | {'confirmation': 2} | fixed evaluation cohort; never training data |
| `eval_to_asap7_confirmation_round3_main` | 8 | 1024 | {'confirmation': 8} | fixed evaluation cohort; never training data |
| `eval_to_asap7_retrospective_original` | 16 | 2448 | {'test': 16} | fixed evaluation cohort; never training data |
| `eval_to_asap7_retrospective_round2` | 8 | 1224 | {'test': 8} | fixed evaluation cohort; never training data |
| `eval_to_freepdk15_boundary_round3_edge` | 1 | 128 | {'confirmation': 1} | fixed evaluation cohort; never training data |
| `eval_to_freepdk15_confirmation_round3_main` | 8 | 1024 | {'confirmation': 8} | fixed evaluation cohort; never training data |
| `eval_to_freepdk15_retrospective_original` | 16 | 2448 | {'test': 16} | fixed evaluation cohort; never training data |
| `eval_to_freepdk15_retrospective_round2` | 8 | 1224 | {'test': 8} | fixed evaluation cohort; never training data |
| `validation_public_val` | 256 | 3116 | {'val': 256} | fixed validation cohort for configuration selection |
| `validation_reference_val` | 24 | 3472 | {'val': 24} | fixed validation cohort for configuration selection |
| `validation_to_asap7_val` | 12 | 1736 | {'val': 12} | fixed validation cohort for configuration selection |
| `validation_to_freepdk15_val` | 12 | 1736 | {'val': 12} | fixed validation cohort for configuration selection |
| `transfer_to_asap7` | 28 | 4284 | {'test': 16, 'train': 8, 'val': 4} | source-only transfer fold of the original reference |
| `transfer_to_freepdk15` | 28 | 4284 | {'train': 8, 'val': 4, 'test': 16} | source-only transfer fold of the original reference |
| `matrices_original` | 4896 | — | — | fine FEM capacitance matrices; not an additional independent population |
| `matrices_round2` | 3672 | — | — | fine FEM capacitance matrices; not an additional independent population |
| `matrices_round3` | 3456 | — | — | fine FEM capacitance matrices; not an additional independent population |
| `public_source_rules` | 51 | — | — | pinned downloaded source rules; separate third-party licenses |
| `sta_spatial` | 2039 | — | — | fixed-layout gf180/ibex endpoint/path observations; not training data |
| `sta_layouts` | 8 | — | — | eight exact routed layouts and 104 golden/Linear/ours SPEFs |
| `fem_numerical_evidence` | 36072 | — | — | coarse/fine/wide solver records, never duplicate training labels |

## 数据边界

公开表的标签来自原规则，不能称为独立求解器真值。自建 FEM 为 CTF-derived、明确边界条件的二维数值问题，单位 F/m，不能称为 foundry/signoff/三维真值。
保留源文件身份时，1,713 张公开电容表都是单宽度；不允许跨 GF180 源文件拼成多宽度真值。
三批 FEM 分别为 32、24、27 张表，共 83 张基础表、12,024 个 fine 矩阵。coarse/fine/wide 共 36,072 个求解结果仅提供数值验证，不能计为额外独立标签。
holdout 库从原公开库派生，84 张表排除出 train/val/test；公开确认文件含 341 行，其中重复表经原 `unique_tables` 合并后实际评分 340 张。
迁移、cross-fit 和 validation/evaluation 文件都是派生视图，不能叠加计算数据量或混回训练。
固定版图 STA 仅改变寄生电容；观察值用于 fidelity，不证明 timing closure。

原始 CTF 文件、商业 PTF、与本论文无关的其他研究数据不在历史数据公开包中；终稿论文现随仓库放在 `paper/`。CTF 可通过固定版本脚本独立下载。
全部机器清单及逐文件 SHA-256 见 `database/catalog.json`、`database/files.json`、`database/packages.json`。

## 终稿范围

终稿采用 public、reference 和 FreePDK15 → ASAP7 三个设置；反向迁移仅保留作历史数据。有效训练/验证表数与原始 JSONL 行数不同，具体见 [终稿对应说明](FINAL_PAPER.md)。终稿采用的检查点映射为 `configs/paper_models.json`。
