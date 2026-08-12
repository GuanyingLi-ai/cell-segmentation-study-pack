# Cellpose 预训练推理复现

本实验复现 Stringer 等（2021）Cellpose 的核心推理路径：网络预测细胞概率与二维流场，像素沿流场汇聚形成实例。为避免与 Cellpose-SAM 混淆，固定 `cellpose==3.1.1.1` 并显式选择 legacy `cyto` 模型。

## 一键运行

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

首次运行会从 Cellpose 官方站点下载 legacy `cyto` 权重。输入是官方仓库 README 链接的论文测试图子集。`metrics.json` 保存输入、模型和 mask 的 SHA-256、版本、参数、耗时与完整性检查。

## 成功标准与边界

三张官方 demo 图都必须产生至少一个实例，前景比例必须在 `(0, 1)` 内，标签必须是从 0 开始连续的整数，并成功写出 mask 与 QC 图。这个标准证明安装、权重、预处理、网络推理、flow dynamics 和输出链路均可运行；由于 demo 包不含人工标签，它不是论文 AP 数字的独立复算，也不是论文全量训练复现。

## 参考

- 论文：https://doi.org/10.1038/s41592-020-01018-x
- 固定版本源码：https://github.com/MouseLand/cellpose/tree/v3.1.1.1
- 固定版本 API：https://cellpose.readthedocs.io/en/v3.1.1.1/api.html
- 参数说明：https://cellpose.readthedocs.io/en/v3.1.1.1/settings.html
