# Baysor v0.7.1 最小复现

## 复现边界

本目录完成的是 Petukhov et al. 方法的**算法可执行性复现**：在确定性生成、具有已知 cell truth 的 transcript point cloud 上，运行 Baysor 无先验分割，并验证 transcript assignment、cell × gene、cell statistics、polygon 与 QC 产物。它不是论文 ISS / osmFISH / MERFISH / STARmap 全套 benchmark 的逐图复算。

官方 ISS 预处理镜像在本次环境中返回防爬 HTML；Figshare 原始 `pciSeq_3-3_right.mat` 是 MATLAB `iss` 自定义类的 opaque MAT v5 对象，离开 MATLAB 类定义不能可靠转换。因此没有把无法核验的解析结果冒充真实数据复现。

## 文件

- `reproduce_baysor.py`：种子 `202208`，生成 60 个细胞、6 个基因、4,800 个细胞内转录本和 600 个背景转录本。
- `evaluate_baysor.py`：计算分配率、ARI、cell purity、细胞转录本分布，并生成双面板 SVG。
- `../../configs/baysor_synthetic.toml`：Baysor 参数。
- `../../environments/baysor-v0.7.1-{Project,Manifest}.toml`：Julia 锁定环境。
- `../../outputs/baysor/`：分子归属、count matrix、cell stats、GeoJSON、多指标和 QC。
- `../../logs/baysor_reproduction.log`：完整标准输出/错误与 wall time。

## 环境

- macOS 26.0, arm64
- Julia 1.10.7
- Baysor v0.7.1（Git tag `v0.7.1`）
- Python 3.14（仅数据生成和评价）

Julia 运行时未复制进资料包。官方说明 v0.7.x 不兼容 Julia 1.11，因此复跑应使用 1.10.x。

## 复跑

在资料包根目录执行：

```bash
python3 scripts/baysor/reproduce_baysor.py \
  --output data_processed/baysor/synthetic_molecules.csv

JULIA_DEPOT_PATH=/path/to/isolated/depot \
julia --project=/path/to/baysor_env \
  -e 'using Baysor; Baysor.command_main()' -- \
  run -c configs/baysor_synthetic.toml \
  --count-matrix-format tsv \
  --polygon-format FeatureCollection \
  -o outputs/baysor/ \
  data_processed/baysor/synthetic_molecules.csv

python3 scripts/baysor/evaluate_baysor.py \
  --segmentation outputs/baysor/segmentation.csv \
  --metrics outputs/baysor/metrics.json \
  --figure outputs/baysor/baysor_qc.svg
```

## 验收结果

| 指标 | 结果 |
|---|---:|
| 输入转录本 | 5,400 |
| 真值 / 推断细胞数 | 60 / 60 |
| 全部分子分配率 | 94.98% |
| 真实细胞分子分配率 | 99.69% |
| ARI（真实细胞分子） | 0.994 |
| 加权 cell purity | 99.87% |
| 每推断细胞转录本中位数 | 85 |
| wall time | 99.75 s |

高分是对“已知真值、按 Baysor 假设构造、细胞间隔清楚”的单元测试结果，不代表真实组织或论文 benchmark 的精度。

## 下一步真实数据复现

优先选择能直接下载 molecule table 的 ISS 或 osmFISH ROI；保留官方 `scale` 与 500 iterations，分别跑无先验和 DAPI/poly(A) prior。随后比较分配率、与 published segmentation 的 overlap、分割互相关和 marker 污染，并将结果与本 smoke baseline 分开报告。
