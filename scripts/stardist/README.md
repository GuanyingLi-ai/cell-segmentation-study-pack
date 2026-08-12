# StarDist 2D 论文同源数据预训练推理复现

本目录复现 Schmidt 等（MICCAI 2018）的 StarDist 2D 推理与实例匹配评估。使用官方 `dsb2018.zip` 的 test split 和官方 `2D_paper_dsb2018` 权重；不会重新训练论文模型。

## 运行

在资料包根目录执行：

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

结果包括 `metrics.json`、逐图 TIFF 标签图和 6 张带真值/预测边界的 QC 图。完整结论与环境见 `records/StarDist_2D_论文同源数据复现.md`。
