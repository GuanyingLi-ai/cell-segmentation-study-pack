# 复现记录：CellSAM / YeaZ 最小实验

## 1. 目标与状态

- 目标：对论文官方 YeaZ 示例的实例分割结果做独立统计与可视化复现
- 状态：成功
- 复现层级：结果级复现；未重新执行模型权重推理
- 方法：CellSAM foundation model

## 2. 可追溯信息

- 论文：*CellSAM: a foundation model for cell segmentation*, Nature Methods (2025)
- DOI：<https://doi.org/10.1038/s41592-025-02879-w>
- 官方代码：<https://github.com/vanvalenlab/cellSAM>
- 代码 commit：`362a8e521bcd7313d5cb280bcd4cfc12977c1e9f`
- 模型论文版本：1.2（本实验未加载权重）
- 输入图 SHA-256：`8a98ef9d3eea995f511881d8d50074723f8a8c30637babe7d2f1f317346439e9`
- 官方预测 SHA-256：`0a066837418a9af9818e11ceb6bbfe89599af43111dac44bc19a4bae96c26bc3`
- 环境：`environments/cellsam-reproduction.txt`
- 脚本：`scripts/cellsam/reproduce_yeaz.py`

## 3. 数据

- 数据：官方仓库 `sample_imgs/YeaZ.png` 与 `YeaZ_pred.npy`
- 图像尺寸：470 × 486
- 图像类型：酵母显微图像
- mask 类型：二维实例标签，0 为背景
- 本实验无人工 gold standard，因此不报告 Dice、IoU、AP 或 PQ

## 4. 完整命令

```bash
python scripts/cellsam/reproduce_yeaz.py
```

## 5. 结果

| 指标 | 结果 |
|---|---:|
| 实例数 | 95 |
| 前景比例 | 0.4050783644 |
| 平均面积（px） | 973.9789 |
| 中位面积（px） | 1024.0 |
| 最小面积（px） | 103.0 |
| 最大面积（px） | 2962.0 |

### 产物

- 汇总：`outputs/cellsam/yeaz/summary.json`
- 单细胞测量：`outputs/cellsam/yeaz/cell_measurements.csv`
- 边界叠加：`outputs/cellsam/yeaz/segmentation_overlay.png`
- 三联面板：`outputs/cellsam/yeaz/reproduction_panel.png`

## 6. 官方 tutorial

- 归档：`tutorials/cellsam/official_tutorial.md`
- 状态：未运行
- 原因：用户允许 tutorial 只写入框架；运行需要官方模型权重与 DeepCell 令牌

## 7. 偏差与限制

- 成功复现的是官方预测结果的实例统计和可视化，不代表模型在本机重新推理成功。
- 官方 v1.2 权重只通过 `users.deepcell.org` 提供，需要接受许可并配置访问令牌。
- 完整论文评估集压缩约 14 GB、解压约 84 GB；当前磁盘剩余空间不足以安全展开全量数据。

## 8. 结论

YeaZ 官方结果级最小复现成功，数据、脚本、校验值和输出均已归档。若后续配置 DeepCell 令牌，可在同一框架内新增“本机模型推理”实验，并将新预测与官方 mask 做实例级匹配评估。
