#!/usr/bin/env python3
"""Reproduce the CellSAM YeaZ example and summarize its instance mask."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from skimage.measure import regionprops_table
from skimage.segmentation import find_boundaries


PACK_ROOT = Path(__file__).resolve().parents[2]


def summarize(image_path: Path, mask_path: Path, output_dir: Path) -> None:
    image = np.asarray(Image.open(image_path))
    mask = np.load(mask_path)
    if image.shape[:2] != mask.shape:
        raise ValueError(f"Shape mismatch: image={image.shape}, mask={mask.shape}")

    output_dir.mkdir(parents=True, exist_ok=True)
    props = regionprops_table(
        mask,
        properties=("label", "area", "centroid", "bbox", "equivalent_diameter_area"),
    )
    labels = np.asarray(props["label"])
    areas = np.asarray(props["area"])
    summary = {
        "image": str(image_path),
        "mask": str(mask_path),
        "image_shape": list(image.shape),
        "cell_count": int(labels.size),
        "foreground_fraction": float(np.count_nonzero(mask) / mask.size),
        "area_pixels": {
            "mean": float(areas.mean()),
            "median": float(np.median(areas)),
            "min": float(areas.min()),
            "max": float(areas.max()),
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    columns = list(props)
    rows = zip(*(props[column] for column in columns))
    with (output_dir / "cell_measurements.csv").open("w", encoding="utf-8") as handle:
        handle.write(",".join(columns) + "\n")
        for row in rows:
            handle.write(",".join(str(value) for value in row) + "\n")

    boundaries = find_boundaries(mask, mode="outer")
    overlay = np.stack([image] * 3, axis=-1) if image.ndim == 2 else image[..., :3].copy()
    overlay = overlay.astype(np.uint8, copy=False)
    overlay[boundaries] = (255, 40, 40)
    Image.fromarray(overlay).save(output_dir / "segmentation_overlay.png")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    axes[0].imshow(image, cmap="gray")
    axes[0].set_title("Official YeaZ input")
    axes[1].imshow(mask, cmap="nipy_spectral", interpolation="nearest")
    axes[1].set_title(f"CellSAM instances (n={labels.size})")
    axes[2].imshow(overlay)
    axes[2].set_title("Boundary overlay")
    for axis in axes:
        axis.axis("off")
    fig.savefig(output_dir / "reproduction_panel.png", dpi=180)
    plt.close(fig)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


def run_inference(image_path: Path, mask_path: Path) -> None:
    from cellSAM import cellsam_pipeline

    image = np.asarray(Image.open(image_path))
    prediction = cellsam_pipeline(image, use_wsi=False)
    np.save(mask_path, prediction)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image", type=Path,
        default=PACK_ROOT / "data_raw/cellsam/yeaz/YeaZ.png",
    )
    parser.add_argument(
        "--mask", type=Path,
        default=PACK_ROOT / "data_raw/cellsam/yeaz/YeaZ_pred.npy",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=PACK_ROOT / "outputs/cellsam/yeaz",
    )
    parser.add_argument(
        "--run-model",
        action="store_true",
        help="Download/load CellSAM weights and replace --mask with fresh inference.",
    )
    args = parser.parse_args()
    if args.run_model:
        run_inference(args.image, args.mask)
    summarize(args.image, args.mask, args.output_dir)


if __name__ == "__main__":
    main()
