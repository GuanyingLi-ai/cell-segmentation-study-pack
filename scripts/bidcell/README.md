# BIDCell v1.0.3 官方小样本复现

本目录复现论文 Code availability 指向的 BIDCell 软件归档，而不是用当前最新版替代。固定版本为 GitHub tag `v1.0.3`、commit `dc5be568ca5aed0ac1ed024e6d2003a3a46be923`、Zenodo DOI `10.5281/zenodo.10070794`。

## 范围

- 输入：归档内置 Xenium breast cancer 小样本、DAPI、313-gene transcript table、乳腺癌单细胞参考和正/负 marker。
- 工作流：Cellpose 核分割 → expression maps/patches → nucleus expression/预注释 → 1 epoch、60-step 自监督训练 → 双 shift 推断 → connected-cell 后处理 → cell × gene matrix。
- 这是官方 installation/demo 的端到端可运行性复现；没有论文 benchmark 的人工真值，不能报告 Dice、AP、PQ 或 CellSPA 全套指标。

## 环境与执行

建议使用 Python 3.10，并安装 `environments/bidcell-v1.0.3-lock.txt`。官方 `pyproject.toml` 只有依赖下界，直接安装会拉取不兼容的新版本；这里依据 v1.0.3 的 `pdm.lock` 固定关键依赖。

```bash
git clone --branch v1.0.3 https://github.com/SydneyBioX/BIDCell.git vendor/BIDCell-v1.0.3
python -m pip install vendor/BIDCell-v1.0.3
python -m pip install -r environments/bidcell-v1.0.3-lock.txt

export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export MPLCONFIGDIR="$PWD/cache/matplotlib"
export CELLPOSE_LOCAL_MODELS_PATH="$PWD/cache/bidcell-models"
export NUMBA_CACHE_DIR="$PWD/cache/numba"

/usr/bin/time -lp python scripts/bidcell/reproduce_bidcell.py \
  --config configs/bidcell_small_example.yaml \
  --project-dir . 2>&1 | tee logs/bidcell_reproduction.log
```

首次运行会创建 `outputs/bidcell/work/` 中间文件；最终 mask、矩阵、QC 与指标分别收集到 `outputs/bidcell/` 的稳定路径。

## 已验证结果（2026-08-07）

- 710 个连续标签细胞，mask 为 `382 × 510`，前景比例 0.4667。
- 186,146 条输入 transcript、313 个基因；输出矩阵 710 × 313，无空细胞。
- 总归属 transcript 140,884；每细胞中位 transcript 167、非零基因 61。
- 总 wall time 816.31 s（Apple M5 CPU；不含环境安装），训练 60 steps，推断含两个 patch shift。
- macOS 日志中的 LaunchServices notification 警告没有中断计算；NumPy `swapaxes` FutureWarning 也不影响输出。

原始运行日志见 `logs/bidcell_reproduction.log`，结构化判据见 `outputs/bidcell/metrics.json`。
