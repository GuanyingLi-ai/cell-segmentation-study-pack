#!/usr/bin/env python3
"""Run the BIDCell v1.0.3 official small Xenium example and collect QC."""

import argparse
import json
import random
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tifffile
import torch
from skimage.segmentation import find_boundaries

from bidcell import BIDCellModel


def newest(path: Path) -> Path:
    candidates = [item for item in path.iterdir() if item.is_dir()]
    if not candidates:
        raise RuntimeError(f"No BIDCell run found under {path}")
    return max(candidates, key=lambda item: item.name)


def collect_outputs(project: Path, data_dir: Path, run_dir: Path) -> dict:
    seg_src = run_dir / "test_output" / "epoch_1_step_60_connected.tif"
    expr_src = data_dir / "cell_gene_matrices" / run_dir.name / "expr_mat.csv"
    mask_dst = project / "outputs/bidcell/masks/epoch_1_step_60_connected.tif"
    expr_dst = project / "outputs/bidcell/cell_by_gene/expr_mat.csv"
    qc_dst = project / "outputs/bidcell/qc/overlay.png"
    mask_dst.parent.mkdir(parents=True, exist_ok=True)
    expr_dst.parent.mkdir(parents=True, exist_ok=True)
    qc_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(seg_src, mask_dst)
    shutil.copy2(expr_src, expr_dst)

    seg = tifffile.imread(seg_src)
    dapi = tifffile.imread(data_dir / "dapi_resized.tif")
    expr = pd.read_csv(expr_src, index_col=0)
    gene_expr = expr.drop(columns=["cell_id"], errors="ignore")
    labels = np.unique(seg)
    cells = labels[labels > 0]
    areas = np.bincount(seg.ravel())[1:]
    areas = areas[areas > 0]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    axes[0].imshow(dapi, cmap="gray")
    axes[0].imshow(np.ma.masked_where(~find_boundaries(seg), find_boundaries(seg)), cmap="autumn", alpha=0.9)
    axes[0].set_title(f"DAPI + BIDCell boundaries (n={len(cells)})")
    axes[0].axis("off")
    axes[1].hist(areas, bins=40, color="#4472C4")
    axes[1].axvline(np.median(areas), color="#C00000", linestyle="--", label=f"median={np.median(areas):.0f} px")
    axes[1].set(xlabel="Cell area (target pixels)", ylabel="Count", title="Predicted cell-size distribution")
    axes[1].legend()
    fig.savefig(qc_dst, dpi=180)
    plt.close(fig)

    metrics = {
        "status": "success",
        "bidcell_version": "1.0.3",
        "zenodo_doi": "10.5281/zenodo.10070794",
        "git_commit": "dc5be568ca5aed0ac1ed024e6d2003a3a46be923",
        "random_seed": 0,
        "transcripts_input": 186146,
        "genes": int(gene_expr.shape[1]),
        "cells": int(len(cells)),
        "mask_shape": list(seg.shape),
        "labels_contiguous": bool(np.array_equal(cells, np.arange(1, len(cells) + 1))),
        "foreground_fraction": float((seg > 0).mean()),
        "median_cell_area_px": float(np.median(areas)),
        "total_assigned_transcripts": int(gene_expr.to_numpy().sum()),
        "median_transcripts_per_cell": float(np.median(gene_expr.sum(axis=1))),
        "median_genes_per_cell": float(np.median((gene_expr > 0).sum(axis=1))),
        "empty_cells": int((gene_expr.sum(axis=1) == 0).sum()),
    }
    (project / "outputs/bidcell/metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/bidcell_small_example.yaml")
    parser.add_argument("--project-dir", default=".")
    args = parser.parse_args()
    project = Path(args.project_dir).resolve()
    config = (project / args.config).resolve()

    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    model = BIDCellModel(str(config))
    model.run_pipeline()
    data_dir = project / "outputs/bidcell/work"
    run_dir = newest(data_dir / "model_outputs")
    print(json.dumps(collect_outputs(project, data_dir, run_dir), indent=2))


if __name__ == "__main__":
    main()
