# 复现记录：SOPA / Xenium 组织区域分割

## 1. 目标与状态

- 目标：复现 SOPA `segmentation.tissue` 的预训练/无训练组织 ROI 推断与验证
- 状态：**成功**（Human Breast DAPI / level 2 组织 ROI；2026-07-30）。
- 对应模块：SOPA analysis pipeline / tissue segmentation

## 2. 可追溯信息

- 来源代码仓库：`/Users/liguanying/sopa/`；实际结果归档于 `/Users/liguanying/Projects/sopa/output/`
- 来源 commit：`9b19079932f033a2ecb956ab5445884a8d660566`
- 来源工作树文件：`reproduce_breast_tissue.py`、`reproduce_tissue_channels.py`（均为未提交文件）
- SOPA 版本：2.2.10
- 环境文件：`environments/sopa-reproduction.txt`
- 执行脚本：`scripts/sopa/reproduce_tissue.py`
- 随机种子：不适用（阈值/形态学组织分割）

## 3. 数据

- 平台/组织：10x Xenium / Human Breast Biomarkers
- 输入：Xenium `outs` 目录中的 `morphology_focus` 与 `cell_boundaries.parquet`
- 默认通道：DAPI
- 默认金字塔层级：2
- gold standard：10x cell boundaries 的细胞包围盒质心，仅用于 ROI 覆盖验证

## 4. 模型/推断参数

| 参数 | 值 | 说明 |
|---|---:|---|
| mode | staining | 基于染色信号提取组织区域 |
| image_key | morphology_focus | Xenium 形态图像 |
| channel | DAPI | 可由命令行替换 |
| level | 2 | 全图推荐起点 |
| expand_radius_ratio | 0.05 | ROI 外扩比例 |

## 5. 运行记录与结果

```bash
python scripts/sopa/reproduce_tissue.py \
  --data /path/to/Human_Breast_Biomarkers_S1_Top_outs \
  --output outputs/sopa_tissue \
  --channel DAPI --level 2
```

Human Breast DAPI / level 2 已完成并通过脚本预设判据：

| 指标 | 结果 |
|---|---:|
| 参考细胞数 | 209,467 |
| ROI 占全片面积 | 5.05% |
| 参考细胞质心位于 ROI 内 | 99.2% |
| ROI 与参考细胞包围盒交集 | 88.0% |
| 运行时间 | 118.20 s |
| 自动判定 | `passed=true` |

主报告：`/Users/liguanying/Projects/sopa/output/tissue_reproduction/breast_L2_report.json`。结果同时包含 SpatialData Zarr、全局图、局部放大图和参考细胞叠加 QC。

补充通道对照：DAPI 通过；`ATP1A1/CD45/E-Cadherin`、`18S`、`alphaSMA/Vimentin` 的质心覆盖率分别为 4.5%、4.5%、3.1%，均未通过 95% 阈值。这说明当前 staining 参数适用于 DAPI，不能直接套用到其他形态通道。

Ovarian panel 测试质心覆盖率为 5.3%，`passed=false`，保留为失败对照，不计作成功复现。

## 6. 产物位置

- SpatialData：`/Users/liguanying/Projects/sopa/output/breast_tissue_L2.zarr`
- 指标报告：`/Users/liguanying/Projects/sopa/output/tissue_reproduction/breast_L2_report.json`
- QC 图：`/Users/liguanying/Projects/sopa/output/tissue_reproduction/breast_tissue_L2_{global,zoom,cells_overlay}.png`
- 通道对照：`/Users/liguanying/Projects/sopa/output/tissue_reproduction/channels/channel_comparison.{csv,json}`
- 整体结果目录约 46 GB；资料包内 `outputs/sopa_tissue/` 仍为空，未复制大型 Zarr。

## 7. 复现标准

- `cell_centroid_inside_pct >= 95`
- `roi_area_pct <= 50`
- 报告中的 `passed` 为 `true`

## 8. 结论与下一步

Human Breast DAPI 组织 ROI 已达到本记录定义的成功标准。其他形态通道与 Ovarian panel 的失败结果提示需要按通道/组织重新选择阈值与形态学参数。完整细胞实例分割、边界真值评价和 transcript aggregation 应另立实验记录，不能由本次组织 ROI 成功直接推断。
