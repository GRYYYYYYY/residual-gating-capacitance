# 核对来源与用途

## 指定提交的项目来源

Reference commit: a519539fee8a763c74e1db61427fdd02d85511ca

- https://github.com/GRYYYYYYY/residual-gating-capacitance/blob/a519539fee8a763c74e1db61427fdd02d85511ca/paper/dac_layout_query_revision/main.tex
  正式稿任务定义、基线、全部支持模板结果、runtime与固定节点导出边界。
- https://github.com/GRYYYYYYY/residual-gating-capacitance/blob/a519539fee8a763c74e1db61427fdd02d85511ca/paper/dac_layout_query_revision/extended.tex
  查询分布图、完整计时细节与支持协议分析。
- https://github.com/GRYYYYYYY/residual-gating-capacitance/blob/a519539fee8a763c74e1db61427fdd02d85511ca/unified/cmi.py
  完整角点多线性核心，与掩码情况下的缺角点回退并不是同一层规范。
- https://github.com/GRYYYYYYY/residual-gating-capacitance/blob/a519539fee8a763c74e1db61427fdd02d85511ca/results/layout_offgrid_20261115/census.log
  调用总数、类别数、量化命中数、统计范围和物理映射状态。
- https://github.com/GRYYYYYYY/residual-gating-capacitance/blob/a519539fee8a763c74e1db61427fdd02d85511ca/results/layout_offgrid_20261115/query_census.csv
  逐布局、层、模式的原始分组数据，Codex应据此重算图。

GitHub读取的是同提交可编辑文本与CSV。远程PDF渲染未成功，本任务书不声称已对main.pdf/extended.pdf进行视觉版式验收。

## 官方产品资料：仅用于分类和应用背景

1. Siemens Calibre xACT FAQ:
   https://www.siemens.com/en-gb/products/ic/calibre-design/circuit-verification/xact/
   明确说明 hybrid：器件周边/较低金属层使用场求解，较高层可使用表驱动引擎。不能将xACT整体称为纯场求解器。
2. Synopsys “What is Parasitic Extraction?”:
   https://www.synopsys.com/glossary/what-is-parasitic-extraction.html
   介绍规则型与场求解型路径，并说明StarRC包含Rapid3D，支持2.5D与其他提取应用。不是所有StarRC运行都等于Rapid3D。
3. Synopsys StarRC product page:
   https://www.synopsys.com/implementation-and-signoff/signoff/starrc.html
   说明内置Rapid3D的参考/高精度用途。

这些资料不能证明xRC的精确1D/2D/4D内部公式。该公式在本次任务中来源于用户明确提供的源码核对结论；独立实现与产品完整求值行为的对应关系，需要按任务书限定验证。

## 已上传相关论文

AttentionCap，§4.2：原文已采用单个矩阵行监督来比较CNN-Cap数据。因此，不能从本文组件监督适配误差大，推出该架构无法接受部分矩阵监督或普遍不能插值。
AttentionCap，§4.1/4.3：原始模型训练/适配机会与本文有限任务适配不同；在同任务内说明具体设置。
Flash-CNNCap，§3–4：研究窗口级贡献图与矩阵重建。没有本文同接口实验时只讨论工作流程关系，不作数值输赢声明。

本任务书不提供、复制或要求公开商业专有源码，只规定可核验的数学与接口行为。
