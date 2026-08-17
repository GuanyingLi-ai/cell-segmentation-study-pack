#!/usr/bin/env python3
"""SMURF-lite 官方 Mouse Brain 端到端复现脚本。

流程：数据检查 → spatial object → cell/spot 映射 → nuclei×genes →
单细胞聚类 → SMURF 软分配迭代 → 最终 cells×genes → QC。
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import pickle
import time
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd
import scanpy as sc
import smurf as su


def message(text: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}", flush=True)


def atomic_pickle(obj, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="包含 binned_outputs、全分辨率 TIFF 和 segmentation_final.npy 的目录",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resolution", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    checkpoint_dir = output_dir / "checkpoints"
    iteration_dir = checkpoint_dir / "iterations"
    qc_dir = output_dir / "qc"
    for directory in (output_dir, checkpoint_dir, iteration_dir, qc_dir):
        directory.mkdir(parents=True, exist_ok=True)

    positions = data_dir / "binned_outputs/square_002um/spatial/tissue_positions.parquet"
    matrix_dir = data_dir / "binned_outputs/square_002um/filtered_feature_bc_matrix"
    image = data_dir / "Visium_HD_Mouse_Brain_tissue_image.tif"
    segmentation = data_dir / "segmentation_final.npy"

    # 0. 严格输入检查：不使用随机图像或模拟数据兜底。
    required = [positions, matrix_dir / "matrix.mtx.gz", image, segmentation]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("缺少必要输入：\n" + "\n".join(missing))

    versions = {}
    for package in ("pysmurf", "scanpy", "anndata", "numpy", "pandas", "numba"):
        versions[package] = metadata.version(package)
    (qc_dir / "provenance.json").write_text(
        json.dumps(
            {
                "versions": versions,
                "data_dir": str(data_dir),
                "resolution": args.resolution,
                "tutorial": "https://the-mitra-lab.github.io/SMURF/tutorials/notebooks/Tutorial_Mousebrian.html",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    message(f"环境：{versions}")

    # 1. 构建 SMURF spatial object，并把核分割映射到 2 µm spots。
    so_checkpoint = checkpoint_dir / "so_after_spot_info.pkl"
    if so_checkpoint.exists():
        message("读取 spatial object 检查点")
        with so_checkpoint.open("rb") as handle:
            so = pickle.load(handle)
    else:
        message("1/7 构建 spatial object")
        so = su.prepare_dataframe_image(str(positions), str(image), "HE")
        labels = np.load(segmentation, mmap_mode="r")
        expected_shape = so.image_temp().shape[:2]
        if labels.shape != expected_shape:
            raise ValueError(f"分割尺寸 {labels.shape} 与裁剪图像 {expected_shape} 不一致")
        so.segmentation_final = np.asarray(labels)
        message("2/7 生成 cells/spots 信息和最近邻网络")
        so.generate_cell_spots_information()
        atomic_pickle(so, so_checkpoint)

    # 2. 加载真实 2 µm 表达矩阵，排序到 SMURF 使用的 in-tissue barcode。
    expression_checkpoint = checkpoint_dir / "adata_in_tissue.h5ad"
    if expression_checkpoint.exists():
        adata = sc.read_h5ad(expression_checkpoint)
    else:
        message("3/7 加载并过滤 2 µm spot×gene 矩阵")
        adata = sc.read_10x_mtx(matrix_dir)
        barcodes = so.df.loc[so.df["in_tissue"] == 1, "barcode"]
        adata = copy.deepcopy(adata[barcodes])
        sc.pp.filter_genes(adata, min_counts=1000)
        adata.write_h5ad(expression_checkpoint)
    message(f"spot×gene：{adata.shape}")

    # 3. 聚合核覆盖 spots 的 RNA，得到 nuclei×genes。
    nuclei_checkpoint = checkpoint_dir / "nuclei_raw.h5ad"
    if nuclei_checkpoint.exists():
        adata_raw = sc.read_h5ad(nuclei_checkpoint)
    else:
        message("4/7 聚合 nuclei×genes 表达矩阵")
        su.nuclei_rna(adata, so)
        adata_nuclei = copy.deepcopy(so.final_nuclei)
        sc.pp.filter_cells(adata_nuclei, min_counts=5)
        adata_raw = copy.deepcopy(adata_nuclei)
        adata_raw.write_h5ad(nuclei_checkpoint)
    message(f"nuclei×gene：{adata_raw.shape}")

    # 4. 初始聚类，并执行 SMURF 的迭代软分配/细胞扩张。
    adatas_path = iteration_dir / "adatas.h5ad"
    cells_path = iteration_dir / "cells_final.pkl"
    weights_path = iteration_dir / "weights_record.pkl"
    if not (adatas_path.exists() and cells_path.exists() and weights_path.exists()):
        message("5/7 初始单细胞分析（归一化、PCA、UMAP、Leiden）")
        adata_clustered = su.singlecellanalysis(
            copy.deepcopy(adata_raw),
            resolution=args.resolution,
            random_state=0,
            show=False,
        )
        message("6/7 运行 SMURF 软分配迭代")
        su.itering_arragement(
            adata_clustered,
            adata_raw,
            adata,
            so,
            resolution=args.resolution,
            save_folder=str(iteration_dir) + os.sep,
            show=False,
            keep_previous=False,
        )

    # 5. 加载收敛结果并重建最终 cells×genes 矩阵。
    adatas_final = sc.read_h5ad(adatas_path)
    with cells_path.open("rb") as handle:
        cells_final = pickle.load(handle)
    with weights_path.open("rb") as handle:
        weights_record = pickle.load(handle)

    message("7/7 根据收敛权重生成最终 cells×genes")
    adata_final = su.get_finaldata_fast(
        cells_final,
        so,
        adatas_final,
        adata,
        weights_record,
        plot=False,
    )
    result_path = output_dir / "adata_sc_final.h5ad"
    adata_final.write_h5ad(result_path)

    # 6. 数值 QC 与独立读回所需的摘要。
    counts = np.asarray(adata_final.X.sum(axis=1)).ravel()
    genes = np.asarray((adata_final.X > 0).sum(axis=1)).ravel()
    summary = pd.DataFrame(
        {
            "cells": [adata_final.n_obs],
            "genes": [adata_final.n_vars],
            "total_counts": [float(counts.sum())],
            "mean_counts_per_cell": [float(counts.mean())],
            "median_counts_per_cell": [float(np.median(counts))],
            "mean_genes_per_cell": [float(genes.mean())],
            "median_genes_per_cell": [float(np.median(genes))],
            "matrix_nnz": [int(adata_final.X.nnz)],
        }
    )
    summary.to_csv(qc_dir / "summary_statistics.csv", index=False)
    message(f"完成：{result_path}，形状 {adata_final.shape}")


if __name__ == "__main__":
    main()
