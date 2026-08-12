# 复现记录：BIDCell / 官方 Xenium 小样本端到端

## 1. 目标与状态

- 目标：复现 Fu 等（2024）BIDCell Code availability 提供的软件归档和官方 `example_small.py` 路径。
- 状态：**成功**（2026-08-07）。
- 范围：预处理、核分割、自监督训练、推断、连接域后处理、cell × gene matrix 和 QC；不是论文全数据 benchmark 或全部 CellSPA 指标复算。
- 论文：Fu X, et al. *BIDCell: Biologically-informed self-supervised learning for segmentation of subcellular spatial transcriptomics data*. Nature Communications 15, 509 (2024). DOI: `10.1038/s41467-023-44560-w`。

## 2. 可追溯信息

- Code availability 仓库：`https://github.com/SydneyBioX/BIDCell`。
- 论文对应归档：BIDCell v1.0.3，Zenodo record 10070794，DOI `10.5281/zenodo.10070794`。
- Git tag / commit：`v1.0.3` / `dc5be568ca5aed0ac1ed024e6d2003a3a46be923`。
- 归档创建时间：2023-11-04；许可证：MIT。
- 环境：`environments/bidcell-v1.0.3-lock.txt`。
- 配置：`configs/bidcell_small_example.yaml`。
- 脚本：`scripts/bidcell/reproduce_bidcell.py`。
- 随机种子：Python、NumPy、PyTorch 均为 0。

### 输入 SHA-256

| 文件 | SHA-256 |
|---|---|
| `morphology_mip_small.tif` | `8d8036253e5770a88712caac222a910cbe68ae7da5809e3798a5d683f12092ed` |
| `transcripts_small.csv` | `da8d3867bc85e006421bee7023fb926e195fecd53a6716dd1084d48a0212da64` |
| `sc_breast.csv` | `eea67b8cd2071de418a618d52caa1aca1624d4dd61c7977497422bb47d2d270d` |
| `sc_breast_markers_pos.csv` | `1f6ba3efecedff7e4f927653cf693f24c193c32de78e362f43203bb005c7e59a` |
| `sc_breast_markers_neg.csv` | `e51b5a45026d8ee575c0789aada3f5edf4b59f1d933db646f4cee3d060e2c120` |
| Cellpose `cytotorch_0` | `6a852487b98a3ad91e4e86c969cac520aaac13c609288aad8bd01d4cf76370c6` |

## 3. 计算环境

| 项目 | 记录 |
|---|---|
| OS | macOS 26.0 arm64 |
| CPU / RAM | Apple M5 10-core / 24 GB；固定 CPU 运行 |
| GPU / VRAM | 未使用；官方建议 CUDA GPU ≥12 GB VRAM |
| Python | 3.10.20 |
| BIDCell | 1.0.3 |
| PyTorch / Cellpose | 2.0.1 / 2.2.3 |
| NumPy / pandas | 1.24.4 / 2.1.0 |

## 4. 数据与预处理

- 平台/组织：10x Xenium，人乳腺癌；官方归档内置的小 ROI。
- DAPI 原始图：1800 × 2400；按 0.2125 µm/px 转成 1 µm target grid 后为 382 × 510。
- transcript：186,146 条，313 个唯一基因；坐标列 `x_location`、`y_location`，先平移至原点。
- Cellpose 得到 710 个 nucleus；expression maps 产生 shift 0 的 88 个 patch 和 shift 24 的 70 个 patch。
- 单细胞参考提供 15 个 cell type 和正/负 marker。

## 5. 模型与运行

- 网络：BIDCell 自带 custom UNet3+，输入 313 通道，patch size 48。
- 损失权重：nuclei encapsulation、oversegmentation、cell calling、overlap、positive marker、negative marker 均为 1.0。
- 训练：1 epoch、60 steps；测试 checkpoint `epoch_1_step_60.pth`。
- `cpus=2`，`OMP_NUM_THREADS=1`；总 wall time 816.31 s，user 673.26 s，sys 130.37 s。

## 6. 结果

| 指标 | 值 |
|---|---:|
| 输出细胞数 | 710 |
| mask 尺寸 | 382 × 510 |
| 标签连续 | 是（0–710） |
| 前景比例 | 0.4667 |
| 中位细胞面积 | 113 target px |
| cell × gene matrix | 710 × 313 |
| 总归属 transcript | 140,884 |
| 每细胞中位 transcript | 167 |
| 每细胞中位非零基因 | 61 |
| 空细胞 | 0 |

产物：`outputs/bidcell/masks/epoch_1_step_60_connected.tif`、`outputs/bidcell/cell_by_gene/expr_mat.csv`、`outputs/bidcell/qc/overlay.png`、`outputs/bidcell/metrics.json`、`logs/bidcell_reproduction.log`。

## 7. 偏差与限制

- 官方 demo 没有人工实例 mask 或 transcript-to-cell gold standard，因此不能诚实计算 Dice、AP、PQ、AJI 或 CellSPA 全套指标；本记录只报告完整性、标签、面积、表达矩阵和运行工程指标。
- 本机无 CUDA，训练和推断使用 CPU；数值结果可能与论文 GTX Titan V 环境存在非确定位级差异。
- 官方 `pyproject.toml` 只给依赖下界，会在今天安装到 Cellpose 4/PyTorch 2.13，无法代表 2023 归档环境。本次按 `pdm.lock` 固定关键版本，并记录这一必要修正。
- 通过 `KMP_DUPLICATE_LIB_OK=TRUE` 避免 macOS 上 OpenMP 运行库冲突；这属于平台兼容设置，不改变模型参数。
- 输入小 ROI 和 60-step demo 仅验证软件路径，不足以支持论文中“优于其他方法”的定量结论。

## 8. 结论

已达到“论文指定归档可安装、官方小样本端到端可运行、mask 与表达矩阵可追溯、输出可视检”的复现标准。若要复算论文主结果，下一步应固定论文各数据集和 CellSPA 评估输入，使用 Linux/CUDA 环境逐数据集复跑，并加入人工或官方 segmentation ground truth。
