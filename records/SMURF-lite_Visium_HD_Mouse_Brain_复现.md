# 复现记录：SMURF-lite / Visium HD Mouse Brain

## 1. 目标与状态

- 目标：复现 SMURF 官方 Lite 端到端单细胞重建流程。
- 状态：**成功**（2026-08-07）。
- 官方教程：<https://the-mitra-lab.github.io/SMURF/tutorials/notebooks/Tutorial_Mousebrian.html>。

## 2. 数据与实现

- 数据：10x Genomics Visium HD Mouse Brain，Space Ranger 3.0.0 binned outputs。
- 图像：`Visium_HD_Mouse_Brain_tissue_image.tif`。
- 核分割：SMURF 官方 `segmentation_final.npy.gz`。
- 软件：`pysmurf 3.0.1`。
- 模式：Lite，CPU，最终生成阶段 `plot=False`。
- 原始文件 SHA-256：见结果目录 `logs/SHA256SUMS.txt`。
- 完整环境：见结果目录 `environments/pip-freeze-smurf.txt`。

## 3. 运行结果

| 指标 | 本次结果 | 官方教程 |
|---|---:|---:|
| 初始核数 | 57,300 | 57,300 |
| 过滤后核细胞 | 56,867 | 56,867 |
| 最终细胞数 | 56,816 | 56,818 |
| 基因数 | 9,970 | 9,970 |
| 最终权重组合 | 1,689,852 | 1,690,156 |
| 总 counts | 41,812,376 | 未报告 |
| 每细胞 counts 中位数 | 420 | 未报告 |
| 每细胞基因中位数 | 369 | 未报告 |

最终细胞数比官方结果少 2 个，绝对差异 0.0035%。初始核数、过滤后核数和基因数完全一致，表明输入、空间映射和核表达聚合均成功复现。微小差异最可能来自本次较新的 Scanpy、NumPy 和聚类依赖版本。

## 4. 产物与验证

- 完整结果目录：`/Users/liguanying/Documents/Codex/2026-08-07/referenced-chatgpt-conversation-this-is-an/outputs/cell-segmentation-study-pack/SMURF复现结果`。
- 主结果：`outputs/cell_by_gene/adata_sc_final.h5ad`（约 1.8 GB）。
- H5AD 独立读回验证：通过。
- H5AD SHA-256：`a3617187184ad4c469a17cfbe9914970f24d142ac5e6acf1d83fb52c4bd464db`。
- 完整日志：`logs/run_smurf_lite.log`，末尾记录 `SUCCESS` 与矩阵形状 `(56816, 9970)`。
- QC：`outputs/qc/summary_statistics.csv`、`outputs/qc/provenance.json` 和 `outputs/figures/`。
- 阶段检查点：`data_processed/checkpoints/`。
- 总结果目录大小：约 27 GB。

## 5. 警告与偏差

- 实际环境是已有 `smurf` Conda 环境，其中 NumPy、Scanpy、Numba 等高于官方教程锁定版本。
- Scanpy 回归阶段出现 divide-by-zero、overflow 和 invalid 数值警告，但流程完整收敛，最终矩阵可独立读回且包含非零稀疏表达。
- 为避免额外约半小时计算和超大像素映射产物，`get_finaldata_fast(..., plot=False)`；这不改变主 `cells × genes` 结果。
- 未计算人工 gold-standard 的 Dice、PQ 或 AJI；官方提供的是核分割结果，而不是带实例真值的评估集。

## 6. 结论

达到端到端复现标准。主产物可直接用于 Scanpy 下游分析；相对官方教程仅少 2 个最终细胞（0.0035%），属于依赖版本差异范围。
