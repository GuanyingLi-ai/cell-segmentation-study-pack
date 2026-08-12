# 复现记录：SOPA / Xenium 组织区域分割

## 1. 目标与状态

- 目标：复现 SOPA `segmentation.tissue` 的预训练/无训练组织 ROI 推断与验证
- 状态：脚本已迁移，等待提供本机 Xenium `outs` 数据后运行
- 对应模块：SOPA analysis pipeline / tissue segmentation

## 2. 可追溯信息

- 来源代码仓库：`/Users/liguanying/sopa/`
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

## 5. 运行记录

```bash
python scripts/sopa/reproduce_tissue.py \
  --data /path/to/Human_Breast_Biomarkers_S1_Top_outs \
  --output outputs/sopa_tissue \
  --channel DAPI --level 2
```

当前未运行：源仓库未发现 `output` 产物，脚本预设的 `/Users/liguanying/Downloads/Human_Breast_Biomarkers_S1_Top_outs` 当前也未检测到。

## 6. 产物位置

- SpatialData：`outputs/sopa_tissue/zarr/`
- 指标报告：`outputs/sopa_tissue/reports/`
- QC 图：`outputs/sopa_tissue/qc/`

## 7. 复现标准

- `cell_centroid_inside_pct >= 95`
- `roi_area_pct <= 50`
- 报告中的 `passed` 为 `true`

## 8. 下一步

补充正确的 Xenium `outs` 路径后运行 DAPI；随后对其他 morphology channel 逐一运行并比较 JSON 报告。完整细胞实例分割与 transcript aggregation 应另立实验记录。
