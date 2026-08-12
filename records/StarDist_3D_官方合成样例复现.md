# 复现记录：StarDist 3D / 官方合成样例

## 1. 目标与状态

- 目标：复现 Weigert 等（WACV 2020）StarDist 3D 官方教程的预训练推理路径。
- 状态：**成功**（2026-08-07）。
- 范围：官方 `demo3D.zip` 合成 test volumes、`3D_demo` 预训练模型、星凸多面体预测、3D NMS、体素实例 mask、真实标签 matching 和三正交面 QC；未重新训练，也不是论文真实显微数据 benchmark。

## 2. 可追溯信息

- StarDist `0.9.2`，官方 tag commit `5f21cc938cdd94a7bce6f5b63d0a95d826a75f14`。
- 数据：官方 `demo3D.zip`；SHA-256 `fa638943b25efc03808bb130eb1a1930c017cdd5ce4ce79fcbc12fbb031c5300`。
- 模型：`3D_demo`；模型压缩包 SHA-256 `ea05831eb5acc8a2fd31eaa23f4460a196a9af53b14f40affb9d80885f699f90`。
- 权重 `weights_best.h5` SHA-256 `8cce57ad459a4d86c16cfea6b17c0f28dac8fa1aec368c8cabc5a1d532a423bc`。
- 配置：`configs/stardist_3d_reproduction.json`；脚本：`scripts/stardist/reproduce_stardist_3d.py`；环境同 `environments/stardist-2d-reproduction.txt`。

## 3. 数据与参数

- 3 个 test volumes，均为 `(Z,Y,X)=(64,128,128)`，共 235 个真值实例。
- 按体数据空间轴 `(0,1,2)` 使用第 1–99.8 百分位归一化。
- 使用模型自带阈值：`prob_thresh=0.7079326183`、`nms_thresh=0.3`；未在 test volumes 上调参。
- 评价使用官方 matching，IoU 阈值 0.50、0.75、0.90，`by_image=false`。

## 4. 运行命令

```bash
export MPLCONFIGDIR="$PWD/cache/matplotlib"
export KERAS_HOME="$PWD/cache/keras"
export CUDA_VISIBLE_DEVICES=-1

python scripts/stardist/reproduce_stardist_3d.py \
  --config configs/stardist_3d_reproduction.json \
  --data-dir data_raw/stardist/demo3D \
  --dataset-archive data_raw/stardist/demo3D.zip \
  --output-dir outputs/stardist_3d \
  2>&1 | tee logs/stardist_3d_reproduction.log
```

## 5. 结果

| IoU | TP | FP | FN | Precision | Recall | F1 | PQ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 235 | 1 | 0 | 0.9958 | 1.0000 | 0.9979 | 0.8160 |
| 0.75 | 218 | 18 | 17 | 0.9237 | 0.9277 | 0.9257 | 0.7638 |
| 0.90 | 2 | 234 | 233 | 0.0085 | 0.0085 | 0.0085 | 0.0077 |

- 预测 236 个多面体实例；平均 CPU 推理 13.70 s/volume，总执行 43.48 s。
- 3 个体数据均保存 TIFF 实例 mask 和 XY/XZ/YZ 中心切片边界 QC。
- 产物：`outputs/stardist_3d/metrics.json`、`outputs/stardist_3d/masks/`、`outputs/stardist_3d/figures/`、`logs/stardist_3d_reproduction.log`。

## 6. 限制

- demo 数据是合成且近似各向同性；高分不能外推到真实组织、低信噪比、密集粘连或强各向异性体数据。
- IoU=0.90 的急剧下降说明边界达到近乎逐体素重合仍很困难，不应只报告 IoU=0.50。
- 真正的论文级复现还需固定训练划分、polyhedron rays、anisotropy、patch、augmentation 和阈值优化，并复跑论文真实 3D 数据。

## 7. 结论

已达到“官方 3D 数据 + 官方预训练模型 + 真实 3D 标签 + 体积实例指标 + 3D mask/QC/日志”的最小复现标准。
