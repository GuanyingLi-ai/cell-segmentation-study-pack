# Baysor 方法学习笔记

> 整理来源：Petukhov et al. 论文流程讲解、Baysor 官方文档与本包 smoke 复现  
> 关联论文：Petukhov V, et al. *Cell segmentation in imaging-based spatial transcriptomics* (Nat Biotechnol, 2022)  
> 关联脚本：[`../scripts/baysor/`](../scripts/baysor/)  
> 关联记录：[`Baysor 最小复现`](../records/Baysor_Petukhov_复现.md)  
> 最后更新：2026-08-13

## 一、一句话理解

Baysor 不画细胞膜，而是把每个 RNA 分子当作空间中的一个点，依据 **位置近、基因组成像、大小合理** 三件事，推断它属于哪个细胞或背景噪声。

本质上是 **空间 + 基因 + 细胞大小约束** 的细胞级聚类，不是普通 k-means。

## 二、解决什么问题

| 传统做法 | 问题 |
|---|---|
| 只用 DAPI 核分割 | 核 ≠ 全细胞，胞质分子易丢失 |
| watershed 扩核 | 依赖图像质量与配准，调参多 |
| 不做分割（只看区域） | 难得到单细胞表达矩阵 |

Baysor 的核心假设：**同一细胞内的分子，应在空间上聚集，且基因组成相对稳定。**

## 三、整体流程

```text
分子表 (x, y, gene) [+ 可选 prior]
        ↓
过滤低表达基因；若有 prior 则估计 scale
        ↓
背景分离：哪些点是噪声？
        ↓
基因组成聚类：几种 major cell type 口味？
        ↓
主分割（BMM + MRF + EM，默认 500 轮）
  · 初始化大量候选 cell
  · 迭代：重分配分子 → 更新 cell 中心/大小/基因 profile → 删小簇/生新簇
        ↓
输出：segmentation.csv / counts / polygons / cell stats / QC
```

### 三条命令

| 命令 | 用途 |
|---|---|
| `baysor preview` | 快速看数据，估参数 |
| `baysor run` | 主分割 |
| `baysor segfree` | 不做硬分割，只算 NCV 邻域组成 |

## 四、三层方法（论文结构）

| 层级 | 做什么 | 类比 |
|---|---|---|
| NCV | 每个分子看 k 近邻的基因比例 | 先看局部“社区类型”，不先分户 |
| MRF + EM | 统一处理背景分离、类型聚类、细胞分割 | 邻居怎么分，会影响你怎么分 |
| BMM 主分割 | 自动决定 cell 数，联合空间 + 基因 + scale | 带约束的“找细胞聚类” |

## 五、和普通聚类的区别

| | 普通聚类 | Baysor |
|---|---|---|
| 特征 | 只看坐标或只看基因 | **同时看坐标 + 基因** |
| 簇数 | 通常事先指定 k | **Bayesian mixture 自动增减** |
| 空间 | 常忽略 | **MRF：邻居标签应连续** |
| 大小 | 无约束 | **scale：簇大小应像细胞** |
| 噪声 | 少见显式建模 | **单独 background component** |

记忆：**Baysor ≈ 聚类，但是“为空间转录组找细胞”设计的聚类。**

## 六、输入与输出

### 输入

- 必需：`x, y, gene`（CSV/Parquet）
- 可选：`z`（3D）、prior segmentation（DAPI/Cellpose mask 或 CSV 列 `:cell`）

### 输出

| 文件 | 内容 |
|---|---|
| `segmentation.csv` | 每分子 → cell ID、confidence、cluster、is_noise |
| `segmentation_counts.tsv` | cell × gene 矩阵 |
| `segmentation_cell_stats.csv` | 面积、密度、confidence、lifespan 等 QC |
| `segmentation_polygons_2d.json` | 细胞边界（GeoJSON） |

## 七、关键参数速查

| 参数 | 含义 | 设错会怎样 |
|---|---|---|
| `scale` | 期望细胞半径（与坐标同单位） | 太小→过分割；太大→欠分割 |
| `min_molecules_per_cell` | 多少分子才算一个真 cell | 太高→漏小 cell；太低→噪声变 cell |
| `n_clusters` | 基因组成聚类数（≈ major cell type） | 与组织复杂度不匹配时 purity 下降 |
| `prior_segmentation_confidence` | prior 可信度（0–1） | 0=忽略 DAPI；1=严格服从 prior |
| `iters` | 主分割迭代次数（默认 500） | 太少可能未收敛 |

多数派生参数（NN 数、初始 cell 数等）从 `min_molecules_per_cell` 自动推导。

## 八、prior 怎么用

DAPI / poly(A) / 已有分割 **不是硬边界**，而是 soft prior：

```text
prior confidence = 0     → 完全忽略图像
prior confidence = 0.2   → 参考但允许修正（默认）
prior confidence > 0.7   → 图像质量高、数据稀疏时
prior confidence = 1     → 严格服从 prior
```

适用：**ISS 等稀疏数据** 常需 prior；**MERFISH 等高密度数据** 可 transcript-only。

## 九、论文怎么验证（无 gold standard）

1. **汇总统计**：细胞数、分子分配率、每 cell 分子数/面积  
2. **Pearson 相关 benchmark**：分割不一致时，哪边“同 cell 内基因更一致”  
3. **生物学案例**：osmFISH 中非神经元是否被漏检；marker purity  
4. **稳定性**：换 random seed 结果是否一致  

## 十、常见失败模式

| 场景 | 原因 | 应对 |
|---|---|---|
| 同类细胞粘在一起 | scale 太大 | 减小 scale |
| 一个 cell 被拆成多个 | scale 太小 | 增大 scale |
| 背景分子误分配 | 噪声模型/阈值 | 调 `-m`，检查 assignment_confidence |
| 核/胞质被拆成两 cell | 亚细胞结构 | 设 nuclei/cyto genes，`n_clusters=1` |
| 稀疏区域分不出 | 分子太少 | 加 DAPI prior |
| 形状很复杂 | 模型假设椭圆点云 | 加 whole-body prior |

## 十一、本包 smoke 实验如何解释

| 项目 | 结果 |
|---|---:|
| 输入 | 60 cell × 80 分子 + 600 背景，6 genes |
| 推断 cell 数 | 60 |
| ARI | 0.994 |
| 全部分子分配率 | 94.98% |

说明：**软件主链路跑通**；高分因合成数据“细胞分离清楚、类型差异大”，**不能外推为真实组织精度**。

本包 **未复现** 论文 ISS/osmFISH/MERFISH 等真实 benchmark。

## 十二、学习与实验顺序

1. 理解输入是 `(x, y, gene)` 分子表，不是图像 mask。  
2. 分清三层：NCV 探索 → MRF 框架 → BMM 主分割。  
3. 记住 Baysor 是 **空间+基因联合聚类**，不是单纯 k-means。  
4. 先 `preview` 估 scale，再小 ROI 跑 `run`。  
5. 用 assignment rate、cell size、marker purity 做 QC。  
6. 对照 [`records/Baysor_Petukhov_复现.md`](../records/Baysor_Petukhov_复现.md) 看 smoke 边界。

## 十三、自测问题

- 为什么 DAPI 核分割不足以代表全细胞？  
- Baysor 和普通聚类最大的三点区别是什么？  
- `scale` 和 `min_molecules_per_cell` 分别控制什么？  
- prior confidence 为 0.2 是什么意思？  
- 论文没有 gold standard 时，怎么间接评价分割质量？  
- 本包 smoke test 高分说明了什么、不能说明什么？

## 十四、主线速记

```text
分子点云 → 去噪声 → 基因口味聚类 → 空间+基因+scale 联合分 cell
→ transcript assignment → cell×gene → polygon → QC
```

记忆重点：**Baysor 的关键不是“画边界”，而是“让每个分子找到最合理的 cell 归属”；图像 prior 只是参考，不是最终裁判。**
