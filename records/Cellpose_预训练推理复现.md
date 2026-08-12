# 复现记录：Cellpose / legacy cyto 预训练推理

## 1. 目标与状态

- 目标：复现 Stringer 等（2021）Cellpose 的官方预训练推理路径。
- 状态：**成功**（2026-08-07）。
- 范围：验证 legacy `cyto` 权重的安装、图像读取、网络预测、flow dynamics、实例 mask 与 QC 输出；不是论文全量训练或全部 benchmark 数字复算。
- 对应论文：Stringer C, et al. *Cellpose: a generalist algorithm for cellular segmentation*. Nature Methods 18, 100–106 (2021).

## 2. 可追溯信息

- 官方代码版本：`cellpose==3.1.1.1`，固定版本源码 commit `fb22843e70d03f7884c301b7b72bedd7d9c3d2d9`。
- 模型：legacy `cyto` / `cytotorch_0`。
- 模型 SHA-256：`6a852487b98a3ad91e4e86c969cac520aaac13c609288aad8bd01d4cf76370c6`。
- 数据：Cellpose 官方 README 链接的 `demo_images.zip`（论文测试图子集）。
- 压缩包 SHA-256：`afc6bbfeda55aa6eb7a335934b508e652af19363c92226800f7debadef44a522`。
- 环境：`environments/cellpose-reproduction.txt`。
- 配置：`configs/cellpose_reproduction.json`。
- 脚本：`scripts/cellpose/reproduce_cellpose.py`。
- 随机种子：0。

## 3. 计算环境

| 项目 | 记录 |
|---|---|
| OS | macOS 26.0 arm64 |
| CPU / GPU | Apple M5；本次固定 CPU 推理 |
| Python | 3.12.13 |
| Cellpose | 3.1.1.1 |
| PyTorch | 2.13.0 |
| NumPy | 2.0.2 |

## 4. 数据与参数

- 测试图：`img02.png`、`img05.png`、`img16.png`，均来自官方 demo 包。
- 通道：`[2, 3]`，即绿色细胞通道 + 蓝色核通道。
- `diameter=30`、`flow_threshold=0.4`、`cellprob_threshold=0.0`、`min_size=15`。
- 输入按 Cellpose 默认百分位规则归一化。

## 5. 运行命令

```bash
export CELLPOSE_LOCAL_MODELS_PATH="$PWD/cache/cellpose-models"
export MPLCONFIGDIR="$PWD/cache/matplotlib"
export NUMBA_CACHE_DIR="$PWD/cache/numba"

python scripts/cellpose/reproduce_cellpose.py \
  --config configs/cellpose_reproduction.json \
  --input-dir data_raw/cellpose_demo/demo_images \
  --output-dir outputs/cellpose_reproduction \
  2>&1 | tee logs/cellpose_reproduction.log
```

## 6. 结果

| 图像 | 实例数 | 前景比例 | 中位实例面积（px） | 推理耗时（s） | 连续标签 |
|---|---:|---:|---:|---:|---|
| img02 | 104 | 0.5055 | 670.5 | 3.127 | 是 |
| img05 | 179 | 0.2905 | 766.0 | 6.845 | 是 |
| img16 | 50 | 0.6945 | 707.5 | 0.796 | 是 |

- 三图总执行时间：12.43 s（不含首次权重下载与进程启动）。
- 自动判据：每张图实例数大于 0、前景比例在 `(0,1)`、标签为从 0 开始的连续整数，且 mask/QC 文件均落盘。
- 判定：`outputs/cellpose_reproduction/metrics.json` 中 `status = success`。
- 产物：`outputs/cellpose_reproduction/masks/`、`outputs/cellpose_reproduction/figures/`、`logs/cellpose_reproduction.log`。

## 7. 偏差与限制

- 官方 demo 包没有人工实例标签，因此本实验不能诚实报告 Dice、AP、PQ 或 AJI；把这些栏位留空比用伪 ground truth 更可靠。
- 使用 3.1.1.1 运行 legacy `cyto` 权重，是对 2021 模型推理的兼容复现，并非原始 1.0 软件栈的逐位复刻。
- Apple Silicon 上固定 CPU，避免把 MPS 数值差异混入基线；日志中的 PyTorch sparse invariant warning 未导致失败或无效 mask。
- 视觉抽查显示细胞实例与亮环状细胞主体对齐，未见整图前景、空 mask 或明显输出损坏；弱信号区仍有漏检风险。

## 8. 结论

已达到“官方预训练推理可复跑、结果可追溯、输出可视检”的复现标准。若要复算论文 AP，需要另行下载带人工 mask 的论文测试集并严格还原其数据划分与评估代码。
