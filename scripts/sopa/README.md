# SOPA 组织区域分割复现

本模块从本机 `/Users/liguanying/sopa/` 中的两份复现脚本整理而来，复现 SOPA 对 10x Xenium `morphology_focus` 图像的组织区域分割，并用厂商提供的 `cell_boundaries.parquet` 做覆盖率验证。

## 运行

在学习包根目录执行：

```bash
python scripts/sopa/reproduce_tissue.py \
  --data /path/to/Human_Breast_Biomarkers_S1_Top_outs \
  --output outputs/sopa_tissue \
  --channel DAPI \
  --level 2
```

快速检查已有结果：

```bash
python scripts/sopa/reproduce_tissue.py \
  --data /path/to/Human_Breast_Biomarkers_S1_Top_outs \
  --output outputs/sopa_tissue \
  --channel DAPI --level 2 --skip-run
```

更换 `--channel` 可比较不同 morphology channel；每个通道单独运行一次即可。输出包括 SpatialData Zarr、JSON 指标和 QC 叠加图。

## 判定标准

- 至少 95% 的 10x 细胞边界质心落在 SOPA ROI 内。
- ROI 不超过整张切片面积的 50%，用于拦截明显阈值失败。
- 该实验是 tissue ROI segmentation，不是单细胞实例边界算法复现。
