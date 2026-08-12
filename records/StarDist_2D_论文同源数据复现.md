# 复现记录：StarDist 2D / DSB2018 论文模型

## 1. 目标与状态

- 目标：复现 Schmidt 等（MICCAI 2018）StarDist 2D 的官方预训练推理与实例匹配评估路径。
- 状态：**成功**（2026-08-07）。
- 范围：使用论文同源 DSB2018 test split 和官方论文模型，验证归一化、星凸多边形预测、NMS、实例 mask、真实标签评估和 QC；**没有重新训练论文模型，也不是论文全部实验表的逐项复算**。
- 2D 论文：Schmidt U, et al. *Cell Detection with Star-convex Polygons*. MICCAI (2018).

## 2. 可追溯信息

- StarDist：`0.9.2`，对应官方 tag commit `5f21cc938cdd94a7bce6f5b63d0a95d826a75f14`。
- 复现时核对的官方仓库快照：commit `e80c6de700693bc228ed3c9ba1dc19c3785667ee`。
- 模型：`2D_paper_dsb2018`；模型压缩包 SHA-256：`4c11cf68512341d9e8ce3d1278c64ceb8ac400582739f85fcab079a2e82840d2`。
- 权重 `weights_last.h5` SHA-256：`784816ab04540be9d5069bea3de1183e1843c1a4a91abbec0b373e31f037fd39`。
- 数据：官方 `dsb2018.zip`，README 明确说明这是论文使用的 train/test 图像与真值标签；压缩包 SHA-256：`e44921950edce378063aa4457e625581ba35b4c2dbd9a07c19d48900129f386f`。
- 环境：`environments/stardist-2d-reproduction.txt`；配置：`configs/stardist_2d_reproduction.json`；脚本：`scripts/stardist/reproduce_stardist_2d.py`；随机种子：0。

## 3. 计算环境

| 项目 | 记录 |
|---|---|
| OS | macOS 26.0 arm64 |
| 设备 | Apple Silicon；固定 CPU 推理 |
| Python | 3.12.13 |
| StarDist / CSBDeep | 0.9.2 / 0.8.2 |
| TensorFlow / Keras | 2.20.0 / 3.15.1 |
| NumPy | 2.4.6 |

## 4. 数据与参数

- 测试集：50 张单通道显微图像，共 2,460 个真值实例。
- 输入归一化：每张图按第 1 和 99.8 百分位归一化，空间轴为 `(0, 1)`。
- 模型自带阈值：`prob_thresh=0.4178193637`、`nms_thresh=0.5`；没有在 test split 上调参。
- 评价：StarDist 官方 matching 实现，IoU 阈值为 0.50、0.75、0.90；聚合方式为先汇总 TP/FP/FN 再计算指标（`by_image=false`）。

## 5. 运行命令

```bash
export MPLCONFIGDIR="$PWD/cache/matplotlib"
export KERAS_HOME="$PWD/cache/keras"
export CUDA_VISIBLE_DEVICES=-1

python scripts/stardist/reproduce_stardist_2d.py \
  --config configs/stardist_2d_reproduction.json \
  --data-dir data_raw/stardist/dsb2018 \
  --output-dir outputs/stardist_2d \
  2>&1 | tee logs/stardist_2d_reproduction.log
```

## 6. 结果

| IoU 阈值 | TP | FP | FN | Precision | Recall | F1 | Accuracy | PQ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 2,270 | 165 | 190 | 0.9322 | 0.9228 | 0.9275 | 0.8648 | 0.7628 |
| 0.75 | 1,815 | 620 | 645 | 0.7454 | 0.7378 | 0.7416 | 0.5893 | 0.6392 |
| 0.90 | 521 | 1,914 | 1,939 | 0.2140 | 0.2118 | 0.2129 | 0.1191 | 0.1965 |

- 预测实例总数：2,435；真值实例总数：2,460。
- 50 张图总运行时间：33.82 s；平均网络推理 0.606 s/图（首次模型下载和首次环境安装不计入）。
- 自动判据：50 张图均有非空实例预测；每张预测 mask、6 张 QC 图和结构化指标均成功落盘。
- 产物：`outputs/stardist_2d/metrics.json`、`outputs/stardist_2d/masks/`、`outputs/stardist_2d/figures/`、`logs/stardist_2d_reproduction.log`。

## 7. 结果解释与限制

- IoU=0.50 时 F1 为 0.9275，说明论文模型在这套论文 test split 上成功恢复了高质量实例检测；更严格阈值下分数下降，反映边界像素级吻合比“找到正确实例”更难。
- 这里的 `accuracy` 是 StarDist matching 定义的 `TP/(TP+FP+FN)`，不是像素准确率；`PQ` 是匹配质量与检测质量的乘积。
- 结果不能与论文表格里的不同数据集、不同阈值或 mean-over-image 数字直接混用。软件栈是当前兼容实现，不是 2018 年原始 TensorFlow 环境的逐位复刻。
- StarDist 适合可由单中心射线描述的近星凸对象。明显凹陷、分枝、细长或中心不可见的对象仍是结构性弱点。
- 3D 论文共享“中心到边界射线 + NMS”的思想，但输出为星凸多面体，并引入各向异性网格/尺度等 3D 约束；本次没有下载 3D 体数据或执行 3D 模型，不能把 2D 成功等同于 3D 已复现。

## 8. 结论

已达到“官方论文模型 + 论文同源真实标签 + 完整 test split + 可重复命令 + mask/QC/日志 + 实例指标”的 2D 复现标准。若目标是训练级复现，下一步应固定论文 train/validation 划分，重新训练 32-ray 模型、优化阈值，并用同一 matching 代码与本基线比较。
