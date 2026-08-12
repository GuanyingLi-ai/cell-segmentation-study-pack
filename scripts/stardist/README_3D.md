# StarDist 3D 官方合成样例复现

使用官方 `demo3D.zip` 的 3 个 test volumes 和官方 `3D_demo` 模型，执行体数据归一化、星凸多面体预测、3D NMS、体素实例 mask 和真实标签 matching 评价。

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

完整环境、指标和边界见 `records/StarDist_3D_官方合成样例复现.md`。
