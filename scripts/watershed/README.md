# Marker-controlled Watershed / DSB2018 复现

本目录将 Vincent 与 Soille（1991）的 watershed 思想落实为显微核实例分割中常用的 marker-controlled pipeline：Gaussian 平滑、Otsu 前景、形态学清理、欧氏距离变换、局部极大值 markers、对负距离图执行 watershed。

## 运行

```bash
export MPLCONFIGDIR="$PWD/cache/matplotlib"

python scripts/watershed/reproduce_watershed.py \
  --config configs/watershed_reproduction.json \
  --data-dir data_raw/stardist/dsb2018 \
  --output-dir outputs/watershed \
  2>&1 | tee logs/watershed_reproduction.log
```

输出包含实例 mask、6 组前景/距离图/markers 中间文件、6 张六联 QC 图及 `metrics.json`。完整解释见 `records/Watershed_DSB2018_复现.md`。
