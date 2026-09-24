# 中文使用说明

本仓库是当前残差门控电容补全论文的公开代码与数据库仓库，不包含论文本身。默认分支提供代码、结果图表、数据清单；大数据和模型放在同一仓库的 Release 中，读者不需要旧私有仓库的访问权。

## 最短使用流程

```bash
git clone https://github.com/GRYYYYYYY/residual-gating-capacitance.git
cd residual-gating-capacitance
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m capdata fetch database models
python -m capdata list
python scripts/inference_demo.py --domain reference
```

只想使用数据时，`python -m capdata fetch database` 只依赖 Python 标准库，无需先安装 PyTorch。完整训练/模型推理才需要安装研究依赖。

```python
from capdata import load_tables
train = load_tables('public_rules_holdout')
reference_train = load_tables('reference_original')
confirmation = load_tables('eval_reference_confirmation_round3_main', partition='confirmation')
```

公开规则和自建 FEM 的物理语义、单位及输出通道数不同，应分别使用。默认只读 train；不要把 validation/confirmation/test 或 STA 评测记录混回训练。

## 统一管理

- `database/catalog.json`：数据库 ID、用途、版本、规模、单位、划分、对应包和路径。
- `database/packages.json`：各压缩包名称、大小和 SHA-256。
- `database/files.json` / `files-extended.json.gz`：每个成员文件的导出及源文件哈希。
- `configs/selected_models.json`：四个域正式模型与检查点的对应关系。
- `docs/DATABASES_ZH.md`：中文总目录，以及不属于当前论文的数据排除清单。

```bash
python -m capdata fetch --all
python -m capdata verify --all
```

可使用 `--root /你的/数据库目录` 将包安装到集中存储位置，读取前设置 `RG_DATA_ROOT`。旧实验驱动中仍使用固定 `runs/` 路径的命令建议在仓库内运行；统一 loader 支持外部数据库根目录。

本地离线安装包：

```bash
python -m capdata fetch database models --from-dir /下载的压缩包目录
```

同样的命令可安全重复执行；本地已有内容与发布哈希不一致时会拒绝覆盖。

## 复现图表

```bash
python -m capdata fetch database models experiment-records sta-visualization
python scripts/reproduce_reports.py --sta --output results/my_reproduction
```

38 张原结果表和新增的 STA 决策表都与论文版本逐字节比对。空间图来自真实端点/路径/坐标，保留 seed 2 的 MAE 例外，不制造未测得的改进。

## 发布范围

181 个当前研究检查点加 12 个早期初始化检查点均保留；其中正式模型只有 `selected_models.json` 指定的 12 个成员，其他文件是候选/消融/初始化证据。

36,072 次 FEM 的 spec/result/log 与求解源码保留，约 125 GB 可重新生成的 mesh 中间文件不上传。原始 CTF 独立下载；商业 PTF、凭据、服务器环境、其他研究数据和论文正文不上传。原有本地实验文件均保持不变。

历史记录可通过 `python -m capdata fetch historical-evidence` 单独安装。一份约 21 GB 的损坏诊断日志仅保留末尾 64 KiB；原文件未删除，省略原因见 `database/omitted_intermediates.json`。
