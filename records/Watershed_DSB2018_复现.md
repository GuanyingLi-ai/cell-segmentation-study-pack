# 复现记录：Marker-controlled Watershed / DSB2018

## 1. 目标与状态

- 目标：把 Vincent 与 Soille（1991）的 watershed 思想落实为可运行的显微细胞核实例分割基线，并与本包 StarDist 2D 复现使用同一数据和评价口径。
- 状态：**成功**（2026-08-07）。
- 范围：复现现代显微图像中常用的 marker-controlled watershed pipeline；不是逐行复刻 1991 年论文的 immersion simulation 实现，也不声称复算该论文的原始实验。
- 原始论文：Vincent L, Soille P. *Watersheds in Digital Spaces: An Efficient Algorithm Based on Immersion Simulations*. IEEE TPAMI (1991). DOI: [10.1109/34.87344](https://doi.org/10.1109/34.87344)。
- 实现依据：[scikit-image watershed 0.26 文档](https://scikit-image.org/docs/stable/api/skimage.segmentation.html#skimage.segmentation.watershed)。该 API 从给定 markers 对图像进行“注水”，支持 mask、connectivity、compactness 和 watershed line。

## 2. 方法流程

```text
灰度图
  → 强度缩放到 [0,1]
  → Gaussian 平滑（σ=1）
  → Otsu 全局阈值得到前景
  → 删除 <15 px 小对象并填补 <15 px 小孔
  → 前景欧氏距离变换
  → 距离图局部极大值作为 markers（min_distance=5）
  → 在负距离图上执行 marker-controlled watershed
  → 连续整数实例标签
```

距离变换把对象中心变成高点；对其取负后中心成为盆地。每个 marker 对应一个注水源，mask 将扩张限制在估计前景内。粘连对象能否正确分开，主要受前景质量和 marker 数量控制。

## 3. 可追溯信息

- scikit-image：`0.26.0`；实际调用 `skimage.segmentation.watershed`。
- 数据：StarDist 官方 `dsb2018.zip`，README 明确说明包含 StarDist 论文使用的 train/test 图像与真值；压缩包 SHA-256：`e44921950edce378063aa4457e625581ba35b4c2dbd9a07c19d48900129f386f`。
- 数据 README SHA-256：`914a5aae88acdabeb942ebfe2481819ab39056dd15d7e6dffbf54f7c33406ad0`。
- 环境：`environments/watershed-reproduction.txt`；配置：`configs/watershed_reproduction.json`；脚本：`scripts/watershed/reproduce_watershed.py`；随机种子：0。
- StarDist `0.9.2` 仅用于调用同一 matching 评价实现，不参与 Watershed 分割。

## 4. 计算环境

| 项目 | 记录 |
|---|---|
| OS / 设备 | macOS 26.0 arm64 / Apple Silicon CPU |
| Python | 3.12.13 |
| NumPy / SciPy | 2.4.6 / 1.18.0 |
| scikit-image | 0.26.0 |

## 5. 数据、参数与防止信息泄漏

- 测试集：50 张亮核灰度图，共 2,460 个真值实例；与 StarDist 2D 复现完全相同。
- 参数是预先固定的通用基线：Gaussian `sigma=1`、Otsu 阈值、最小对象/孔洞 15 px、marker 最小间距 5 px、`compactness=0`。
- 没有按测试图或测试真值逐图调参，也没有使用真值生成 markers。真值仅在分割完成后用于评价和 QC 叠加。
- 评价使用 IoU=0.50、0.75、0.90；汇总 TP/FP/FN 后计算（`by_image=false`）。

## 6. 运行命令

```bash
export MPLCONFIGDIR="$PWD/cache/matplotlib"

python scripts/watershed/reproduce_watershed.py \
  --config configs/watershed_reproduction.json \
  --data-dir data_raw/stardist/dsb2018 \
  --output-dir outputs/watershed \
  2>&1 | tee logs/watershed_reproduction.log
```

## 7. 结果

| IoU 阈值 | TP | FP | FN | Precision | Recall | F1 | Accuracy | PQ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 1,848 | 645 | 612 | 0.7413 | 0.7512 | 0.7462 | 0.5952 | 0.5877 |
| 0.75 | 1,199 | 1,294 | 1,261 | 0.4809 | 0.4874 | 0.4842 | 0.3194 | 0.4227 |
| 0.90 | 445 | 2,048 | 2,015 | 0.1785 | 0.1809 | 0.1797 | 0.0987 | 0.1693 |

- 预测实例/marker 总数：2,493；真值实例：2,460。
- 平均核心分割时间：0.0231 s/图；含 6 张六联 QC 绘图和全数据评价的总时间：5.13 s。
- 50 张图均得到非空 mask；共保存 50 个预测 mask、18 个中间 TIFF（6 组前景/距离/markers）、6 张 QC 图和 1 个指标文件。
- 产物：`outputs/watershed/metrics.json`、`outputs/watershed/masks/`、`outputs/watershed/intermediates/`、`outputs/watershed/figures/`、`logs/watershed_reproduction.log`。

## 8. 与 StarDist 2D 的同数据对照

| 方法 | F1@0.50 | PQ@0.50 | 核心推理/分割时间（s/图） | 训练 |
|---|---:|---:|---:|---|
| Watershed | 0.7462 | 0.5877 | 0.0231 | 无 |
| StarDist `2D_paper_dsb2018` | 0.9275 | 0.7628 | 0.6055 | 使用官方预训练权重 |

Watershed 快约一个数量级且完全可解释，但固定阈值和 marker 规则难以适应亮度、尺度、密度及粘连程度变化。StarDist 在同一 test split 上明显更准确，不过依赖训练数据、模型权重和较重的软件栈。这里的时间仅用于本机粗略工程比较，两条 pipeline 的计时边界并不完全相同。

## 9. 限制与失败模式

- Otsu 假设前景/背景强度可分；弱信号、强背景或照明不均会直接污染后续全部步骤。
- marker 过多会过分割，过少会合并；`peak_min_distance=5` 是固定像素参数，改变分辨率或对象尺度时必须重新校准。
- 对距离图分水岭更适合近圆/椭圆实体。细长、空心、凹形或内部强度不均的对象可能产生错误 markers。
- 本实验是应用级 marker-controlled pipeline；1991 原论文的核心贡献是数字空间中的高效 immersion watershed 算法与实现细节，二者需在引用时区分。

## 10. 结论

已达到“无训练经典基线 + 固定配置 + 真实 test 标签 + 完整中间产物 + mask/QC/日志 + 与 StarDist 同口径比较”的复现标准。后续若优化 Watershed，应只在独立 validation split 上选择阈值、尺度和 marker 参数，再一次性评价 test split。
