# Cell Segmentation 学习资料包

Study notes and reproducible experiments for cell segmentation.

更新时间：2026-08-07

本资料包面向空间转录组与显微图像中的细胞分割学习、论文总结、方法选型和复现实验。所有文件均为 Markdown，可用 VS Code、Obsidian、Typora、Notion 等直接编辑。

## 文件导航

1. [总框架](00_总框架.md)：问题定义、方法分类、学习路线和选型逻辑。
2. [方法总结](01_方法总结.md)：11 个方法的简介、核心思想、输入输出、优缺点与复现要点。
3. [核心论文与资源](02_核心论文与资源.md)：论文、官方代码和文档入口。
4. [论文阅读模板](templates/论文阅读模板.md)：逐篇精读、方法拆解和批判性评价。
5. [复现记录模板](templates/复现记录模板.md)：环境、数据、参数、日志、结果与偏差。
6. [方法比较表模板](templates/方法比较表模板.md)：用于 benchmark 和综述写作。
7. [SOPA 组织区域分割复现](scripts/sopa/README.md)：可运行脚本、环境、验证指标与输出约定。
8. [Cellpose 预训练推理复现](scripts/cellpose/README.md)：legacy `cyto` 模型、官方 demo 输入、实例 mask、QC 图与可追溯指标。
9. [CellSAM YeaZ 最小复现](scripts/cellsam/README.md)：官方数据、结果级复现、产物及复现边界。
10. [BIDCell v1.0.3 官方小样本复现](scripts/bidcell/README.md)：论文指定 Zenodo 归档、Xenium 小样本、60-step 自监督训练、mask、cell × gene matrix 与 QC。
11. [CellSAM 官方 Tutorial](tutorials/cellsam/README.md)：官方教程归档说明（未运行）。
12. [Baysor v0.7.1 最小复现](scripts/baysor/README.md)：隔离 Julia 环境、确定性合成转录本、500 次迭代、归属/矩阵/多边形与 QC。
12. [StarDist 2D 论文同源数据复现](scripts/stardist/README.md)：官方论文模型、DSB2018 test 真值、实例匹配指标、mask 与 QC。
13. [Watershed / DSB2018 复现](scripts/watershed/README.md)：无训练 marker-controlled 基线、中间产物、实例指标及与 StarDist 的同数据对照。
14. [StarDist 3D 官方合成样例复现](scripts/stardist/README_3D.md)：3 个体数据、星凸多面体推理、3D mask、实例指标及三正交面 QC。
15. [复现状态总览](records/复现状态总览.md)：区分成功、部分完成、待数据、环境受阻和未开始项目。

## 推荐使用顺序

先读总框架，理解 image-based、transcript-informed、soft segmentation 和 pipeline 的边界；再从 Watershed、StarDist、Cellpose 建立实例分割基础；随后学习 Mesmer、CellSAM；最后进入 Baysor、Segger、BIDCell、SMURF 以及 Space Ranger、Sopa。

## 复现资料组织建议

```text
project/
├── data_raw/          # 原始数据，只读
├── data_processed/    # 配准、裁剪、格式转换后的数据
├── configs/           # 参数文件
├── scripts/           # 可重复执行脚本
├── environments/      # conda、uv 或容器环境描述
├── outputs/
│   ├── masks/
│   ├── cell_by_gene/
│   ├── qc/
│   └── figures/
└── records/           # 使用本包复现模板填写
```

## 重要原则

- 固定原始数据版本、软件版本、随机种子和坐标单位。
- 图像分割质量与转录本归属质量分别评估。
- 不仅报告 IoU/F1，也检查过分割、欠分割、无核细胞、细胞大小分布、每细胞转录本数和表达污染。
- 在整张切片运行前，先选有代表性的 ROI 做参数扫描和人工复核。
- 厂商管线与单一算法分开比较；默认参数结果与调参后结果分开记录。
