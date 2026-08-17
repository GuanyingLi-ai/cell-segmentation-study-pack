#!/usr/bin/env python3
"""Reproduce the official SMURF-lite Mouse Brain tutorial with checkpoints."""

from __future__ import annotations

import copy
import gzip
import json
import os
import pickle
import platform
import sys
import time
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd
import scanpy as sc
import smurf as su


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw"
OUT = ROOT / "outputs"
CHECKPOINTS = ROOT / "data_processed" / "checkpoints"
CHECKPOINTS.mkdir(parents=True, exist_ok=True)
(OUT / "cell_by_gene").mkdir(parents=True, exist_ok=True)
(OUT / "qc").mkdir(parents=True, exist_ok=True)

POSITIONS = RAW / "binned_outputs/square_002um/spatial/tissue_positions.parquet"
MATRIX = RAW / "binned_outputs/square_002um/filtered_feature_bc_matrix"
IMAGE = RAW / "Visium_HD_Mouse_Brain_tissue_image.tif"
SEGMENTATION = RAW / "segmentation_final.npy"


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def save_pickle(obj, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)
    temporary.replace(path)


def main() -> None:
    started = time.time()
    required = [POSITIONS, MATRIX / "matrix.mtx.gz", IMAGE, SEGMENTATION]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n" + "\n".join(missing))

    versions = {
        name: metadata.version(name)
        for name in [
            "pysmurf", "numpy", "pandas", "scanpy", "scipy", "matplotlib",
            "numba", "scikit-learn", "Pillow", "anndata", "h5py", "pyarrow", "igraph",
        ]
    }
    provenance = {
        "python": sys.version,
        "platform": platform.platform(),
        "versions": versions,
        "inputs": {"positions": str(POSITIONS), "matrix": str(MATRIX), "image": str(IMAGE), "segmentation": str(SEGMENTATION)},
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        "official_tutorial": "https://the-mitra-lab.github.io/SMURF/tutorials/notebooks/Tutorial_Mousebrian.html",
        "random_seed": 0,
    }
    (OUT / "qc" / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    log(f"Versions: {versions}")

    so_path = CHECKPOINTS / "so_after_spot_info.pkl"
    if so_path.exists():
        log(f"Loading spatial-object checkpoint: {so_path}")
        with so_path.open("rb") as handle:
            so = pickle.load(handle)
    else:
        log("Preparing spatial object from 2 um positions and full H&E image")
        so = su.prepare_dataframe_image(str(POSITIONS), str(IMAGE), "HE")
        segmentation = np.load(SEGMENTATION, mmap_mode="r")
        expected = so.image_temp().shape[:2]
        if segmentation.shape != expected:
            raise ValueError(f"Segmentation shape {segmentation.shape} != cropped image shape {expected}")
        so.segmentation_final = np.asarray(segmentation)
        log("Generating cell/spot information")
        so.generate_cell_spots_information()
        save_pickle(so, so_path)
        log(f"Saved checkpoint: {so_path}")

    adata_path = CHECKPOINTS / "adata_in_tissue.h5ad"
    if adata_path.exists():
        log(f"Loading expression checkpoint: {adata_path}")
        adata = sc.read_h5ad(adata_path)
    else:
        log("Loading 2 um filtered feature-barcode matrix")
        adata = sc.read_10x_mtx(MATRIX)
        adata = copy.deepcopy(adata[so.df.loc[so.df.in_tissue == 1, "barcode"]])
        sc.pp.filter_genes(adata, min_counts=1000)
        adata.write_h5ad(adata_path)
        log(f"Saved filtered expression checkpoint: {adata.shape}")

    nuclei_path = CHECKPOINTS / "nuclei_raw.h5ad"
    if nuclei_path.exists():
        adata_raw = sc.read_h5ad(nuclei_path)
        log(f"Loaded nuclei checkpoint: {adata_raw.shape}")
    else:
        log("Aggregating nuclei × genes matrix")
        su.nuclei_rna(adata, so)
        adata_sc = copy.deepcopy(so.final_nuclei)
        sc.pp.filter_cells(adata_sc, min_counts=5)
        adata_raw = copy.deepcopy(adata_sc)
        adata_raw.write_h5ad(nuclei_path)
        log(f"Saved nuclei checkpoint: {adata_raw.shape}")

    iteration_dir = CHECKPOINTS / "iterations"
    iteration_dir.mkdir(exist_ok=True)
    final_adatas = iteration_dir / "adatas.h5ad"
    final_cells = iteration_dir / "cells_final.pkl"
    final_weights = iteration_dir / "weights_record.pkl"
    if not (final_adatas.exists() and final_cells.exists() and final_weights.exists()):
        log("Running initial single-cell analysis")
        adata_sc = su.singlecellanalysis(copy.deepcopy(adata_raw), resolution=2, show=False)
        log("Starting SMURF iterative arrangement")
        su.itering_arragement(
            adata_sc,
            adata_raw,
            adata,
            so,
            resolution=2,
            save_folder=str(iteration_dir) + os.sep,
            show=False,
            keep_previous=False,
        )

    log("Loading converged iteration outputs")
    adatas_final = sc.read_h5ad(final_adatas)
    with final_cells.open("rb") as handle:
        cells_final = pickle.load(handle)
    with final_weights.open("rb") as handle:
        weights_record = pickle.load(handle)

    log("Generating final cells × genes matrix (plot=False)")
    adata_final = su.get_finaldata_fast(
        cells_final, so, adatas_final, adata, weights_record, plot=False
    )
    final_path = OUT / "cell_by_gene" / "adata_sc_final.h5ad"
    adata_final.write_h5ad(final_path)

    counts = np.asarray(adata_final.X.sum(axis=1)).ravel()
    genes = np.asarray((adata_final.X > 0).sum(axis=1)).ravel()
    stats = pd.DataFrame({
        "cells": [adata_final.n_obs],
        "genes": [adata_final.n_vars],
        "total_counts": [float(counts.sum())],
        "mean_counts_per_cell": [float(counts.mean())],
        "median_counts_per_cell": [float(np.median(counts))],
        "mean_genes_per_cell": [float(genes.mean())],
        "median_genes_per_cell": [float(np.median(genes))],
        "wall_seconds": [time.time() - started],
    })
    stats.to_csv(OUT / "qc" / "summary_statistics.csv", index=False)
    log(f"SUCCESS: wrote {final_path} with shape {adata_final.shape}")


if __name__ == "__main__":
    main()
