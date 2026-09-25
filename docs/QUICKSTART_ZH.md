# 中文使用说明

本仓库提供论文 **Support-Conditioned Residual Gating for Sparse Capacitance Completion** 的代码、数据、模型和结果。主要结果与图表入口见 [README](../README.md)，大数据和模型通过 GitHub Release 下载。

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
- `docs/DATABASES_ZH.md`：数据规模、划分、单位与用途。

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

全部 39 张结果表均与发布版本逐字节比对，STA 空间图由记录的端点、路径和坐标重建。此命令复用测量记录；完整评分、训练和固定版图 STA 重放见 [复现指南](REPRODUCING.md)。

## 发布范围

`configs/selected_models.json` 给出四个域各三个正式模型成员及其校验值。其余检查点用于初始化、模型选择或消融研究。

数值验证包提供 FEM 配置、结果、日志与求解源码，按需下载即可。原始 CTF 通过固定版本脚本独立获取；第三方规则与版图数据的许可见 [THIRD_PARTY.md](../THIRD_PARTY.md)。
