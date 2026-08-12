# 复现记录：Baysor / Petukhov et al. 最小 smoke reproduction

## 1. 目标与状态

- 目标：验证 Baysor 论文方法的核心软件链路和可追溯输出。
- 状态：成功（合成数据 smoke reproduction）；论文真实数据 benchmark 未执行。
- 时间：2026-08-08 00:58–00:59（Asia/Shanghai）。
- 对应范围：方法主链路，不对应论文单一图号。

## 2. 可追溯信息

- 代码：`kharchenkolab/Baysor` tag `v0.7.1`。
- 软件：Baysor 0.7.1；Julia 1.10.7。
- 合成输入种子：202208；Baysor CLI 内部固定 `Random.seed!(1)`。
- 配置：`configs/baysor_synthetic.toml`。
- 环境：`environments/baysor-v0.7.1-Project.toml` 与 `baysor-v0.7.1-Manifest.toml`。
- 生成/评价：`scripts/baysor/reproduce_baysor.py`、`scripts/baysor/evaluate_baysor.py`。

## 3. 计算环境

| 项目 | 记录 |
|---|---|
| OS / 架构 | macOS 26.0 / arm64 |
| Julia | 1.10.7 |
| Baysor | 0.7.1 |
| Python | 3.14 |
| GPU | 未使用 |
| 容器 | 未使用；项目内隔离 Julia depot |

## 4. 数据

- 确定性合成 transcript point cloud：60 个细胞，3 种表达组成，6 个基因。
- 每细胞 80 个转录本，共 4,800 个；均匀背景 600 个；总计 5,400 个。
- 细胞中心近似规则网格，细胞内坐标为二维高斯（σ=2.6），中心间距约 19。
- schema：`x,y,gene,cell_truth,is_noise_truth`。

说明：官方预处理 ISS 镜像返回防爬 HTML；Figshare 原始 MAT 文件为 MATLAB `iss` 自定义类 opaque 对象。本次未对其做未经验证的逆向解析。

## 5. 参数

| 参数 | 值 |
|---|---:|
| scale | 6.5 |
| scale_std | 25% |
| n_clusters | 3 |
| min_molecules_per_gene | 20 |
| min_molecules_per_cell | 20 |
| iters | 500 |
| prior segmentation | 无 |

## 6. 运行记录

- wall time：99.75 s；user 93.55 s；sys 2.63 s。
- 日志显示输入 5,400 transcripts / 6 genes，500 次迭代完成，最终 60 components。
- `n > length(high_conf_ids)` 是局部颜色估计 warning；后续 polygon、CSV/TSV 与统计文件均成功保存，日志以 `All done!` 结束。
- 外层 `/usr/bin/time -lp` 因沙箱禁止 `sysctl kern.clockrate` 返回非零；Baysor 本身已完成，因此不将其记为算法失败。

## 7. 结果

| 指标 | 结果 |
|---|---:|
| 推断细胞数 | 60 |
| 全部分子分配率 | 0.9498 |
| 真实细胞分子分配率 | 0.9969 |
| ARI（真实细胞分子） | 0.9940 |
| 加权 cell purity | 0.9987 |
| 每细胞转录本中位数 | 85 |
| 每细胞转录本范围 | 80–91 |

产物：`segmentation.csv`、`segmentation_counts.tsv`、`segmentation_cell_stats.csv`、`segmentation_polygons_2d.json`、`metrics.json`、`baysor_qc.svg`、参数 dump 与日志。

## 8. 偏差与结论

- 与论文一致：使用 transcript spatial coordinates + gene composition、显式背景、无图像先验的概率分割；输出 transcript assignment、cell × gene 和边界。
- 与论文不一致：输入是容易分离的合成数据，不含真实组织密度梯度、形态复杂性、测量 dropout、邻近同型细胞或配准误差，也未比较 published segmentation / pciSeq / watershed。
- 结论：Baysor v0.7.1 在受支持的 Julia 1.10.7 环境中可稳定完成核心链路；当前结果只可作为安装与回归测试基线，不能作为真实数据精度证据。
- 下一步：取得可直接解析的 ISS/osmFISH molecule table 后，固定 ROI 做无先验与 prior 双臂复现，并补充真实生物学与分割一致性指标。
