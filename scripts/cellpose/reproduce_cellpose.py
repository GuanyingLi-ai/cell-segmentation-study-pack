#!/usr/bin/env python3
"""Reproduce legacy Cellpose `cyto` pretrained inference on official demo images."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
import torch
from cellpose import models, plot
from cellpose.io import imread


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_version(name: str) -> str:
    from importlib.metadata import version

    return version(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    masks_dir = args.output_dir / "masks"
    figures_dir = args.output_dir / "figures"
    masks_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)

    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    model = models.CellposeModel(
        gpu=bool(config["use_gpu"]), model_type=config["model_type"]
    )
    records = []
    started = time.perf_counter()

    for filename in config["images"]:
        source = args.input_dir / filename
        image = imread(source)
        image_started = time.perf_counter()
        mask, flows, _style = model.eval(
            image,
            channels=config["channels"],
            diameter=float(config["diameter"]),
            flow_threshold=float(config["flow_threshold"]),
            cellprob_threshold=float(config["cellprob_threshold"]),
            min_size=int(config["min_size"]),
        )
        elapsed = time.perf_counter() - image_started
        mask = np.asarray(mask, dtype=np.uint32)
        labels = np.unique(mask)
        foreground = mask > 0
        areas = np.bincount(mask.ravel())[1:]
        areas = areas[areas > 0]
        contiguous = np.array_equal(labels, np.arange(int(mask.max()) + 1))

        mask_path = masks_dir / f"{source.stem}_cp_masks.tif"
        tifffile.imwrite(mask_path, mask)

        fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
        axes[0].imshow(image)
        axes[0].set_title("official demo input")
        axes[1].imshow(mask, cmap="nipy_spectral")
        axes[1].set_title(f"instances: {int(mask.max())}")
        axes[2].imshow(plot.mask_overlay(image, mask))
        axes[2].set_title("Cellpose overlay")
        for axis in axes:
            axis.axis("off")
        figure_path = figures_dir / f"{source.stem}_qc.png"
        fig.savefig(figure_path, dpi=160)
        plt.close(fig)

        records.append(
            {
                "image": filename,
                "input_sha256": sha256(source),
                "shape": list(image.shape),
                "mask_sha256": sha256(mask_path),
                "mask_count": int(mask.max()),
                "foreground_fraction": float(foreground.mean()),
                "median_instance_area_px": float(np.median(areas)) if areas.size else 0.0,
                "labels_contiguous": bool(contiguous),
                "runtime_seconds": elapsed,
            }
        )

    valid = all(
        item["mask_count"] > 0
        and 0.0 < item["foreground_fraction"] < 1.0
        and item["labels_contiguous"]
        for item in records
    )
    report = {
        "status": "success" if valid else "failed",
        "success_criterion": (
            "Each official demo image yields >0 instances, a non-degenerate "
            "foreground fraction, contiguous integer labels, and persisted QC artifacts."
        ),
        "scope": "pretrained inference reproduction; not full paper training/benchmark",
        "config": config,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cellpose": package_version("cellpose"),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "device": str(model.device),
            "cellpose_model_file": str(model.pretrained_model),
            "cellpose_model_sha256": sha256(Path(model.pretrained_model)),
            "cellpose_local_models_path": os.environ.get("CELLPOSE_LOCAL_MODELS_PATH"),
        },
        "total_runtime_seconds": time.perf_counter() - started,
        "images": records,
    }
    (args.output_dir / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
