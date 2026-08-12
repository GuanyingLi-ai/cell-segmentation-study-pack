#!/usr/bin/env python3
"""Marker-controlled watershed baseline for bright nuclei images."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import skimage
import tifffile
from scipy import ndimage as ndi
from skimage import exposure, feature, filters, measure, morphology, segmentation
from stardist.matching import matching, matching_dataset


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def segment(image: np.ndarray, cfg: dict) -> tuple[np.ndarray, dict]:
    image_float = exposure.rescale_intensity(image.astype(np.float32), out_range=(0.0, 1.0))
    smoothed = filters.gaussian(image_float, sigma=cfg["gaussian_sigma"], preserve_range=True)
    if cfg["threshold_method"] != "otsu":
        raise ValueError("This reproduction currently supports threshold_method='otsu' only")
    threshold = float(filters.threshold_otsu(smoothed))
    foreground = smoothed > threshold
    # scikit-image 0.26 uses inclusive ``max_size``; subtract one to preserve
    # the conventional "remove objects/holes smaller than N pixels" meaning.
    foreground = morphology.remove_small_objects(
        foreground, max_size=cfg["min_object_size"] - 1
    )
    foreground = morphology.remove_small_holes(
        foreground, max_size=cfg["min_hole_size"] - 1
    )

    distance = ndi.distance_transform_edt(foreground)
    coordinates = feature.peak_local_max(
        distance,
        labels=foreground,
        min_distance=cfg["peak_min_distance"],
        exclude_border=cfg["exclude_border_peaks"],
    )
    markers = np.zeros(distance.shape, dtype=np.int32)
    if coordinates.size:
        markers[tuple(coordinates.T)] = np.arange(1, len(coordinates) + 1)
    labels = segmentation.watershed(
        -distance,
        markers,
        mask=foreground,
        compactness=cfg["watershed_compactness"],
    )
    labels = measure.label(labels, connectivity=1).astype(np.int32, copy=False)
    return labels, {
        "smoothed": smoothed,
        "threshold": threshold,
        "foreground": foreground,
        "distance": distance,
        "markers": markers,
    }


def main() -> None:
    args = parse_args()
    cfg = json.loads(args.config.read_text())
    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])

    image_paths = sorted(args.data_dir.glob(cfg["input_glob"]))
    labels_by_name = {p.name: p for p in args.data_dir.glob(cfg["label_glob"])}
    pairs = [(p, labels_by_name[p.name]) for p in image_paths if p.name in labels_by_name]
    if not pairs:
        raise RuntimeError("No matching image/mask pairs found")

    masks_dir = args.output_dir / "masks"
    intermediates_dir = args.output_dir / "intermediates"
    figures_dir = args.output_dir / "figures"
    for directory in (masks_dir, intermediates_dir, figures_dir):
        directory.mkdir(parents=True, exist_ok=True)

    true_masks, predicted_masks, per_image = [], [], []
    started = time.perf_counter()
    for index, (image_path, label_path) in enumerate(pairs):
        image = tifffile.imread(image_path)
        truth = tifffile.imread(label_path).astype(np.int32, copy=False)
        tic = time.perf_counter()
        prediction, state = segment(image, cfg)
        seconds = time.perf_counter() - tic
        tifffile.imwrite(masks_dir / image_path.name, prediction, compression="zlib")
        score = matching(truth, prediction, thresh=0.5)
        per_image.append({
            "image": image_path.name,
            "ground_truth_instances": int(truth.max()),
            "predicted_instances": int(prediction.max()),
            "otsu_threshold": state["threshold"],
            "foreground_fraction": float(state["foreground"].mean()),
            "marker_count": int(state["markers"].max()),
            "precision_at_0_5": score.precision,
            "recall_at_0_5": score.recall,
            "f1_at_0_5": score.f1,
            "mean_matched_score_at_0_5": score.mean_matched_score,
            "panoptic_quality_at_0_5": score.panoptic_quality,
            "runtime_seconds": seconds,
        })
        true_masks.append(truth)
        predicted_masks.append(prediction)

        if index < cfg["qc_images"]:
            stem = image_path.stem
            tifffile.imwrite(intermediates_dir / f"{stem}_foreground.tif", state["foreground"])
            tifffile.imwrite(intermediates_dir / f"{stem}_distance.tif", state["distance"].astype(np.float32))
            tifffile.imwrite(intermediates_dir / f"{stem}_markers.tif", state["markers"])
            overlay = np.repeat(exposure.rescale_intensity(image, out_range=(0.0, 1.0))[..., None], 3, axis=-1)
            overlay[segmentation.find_boundaries(truth, mode="inner")] = (0.1, 0.9, 0.2)
            overlay[segmentation.find_boundaries(prediction, mode="inner")] = (1.0, 0.15, 0.15)
            fig, axes = plt.subplots(2, 3, figsize=(12, 8), constrained_layout=True)
            panels = (
                (image, "Input", "gray"),
                (state["smoothed"], f"Gaussian σ={cfg['gaussian_sigma']}", "gray"),
                (state["foreground"], f"Otsu foreground (t={state['threshold']:.3f})", "gray"),
                (state["distance"], "Distance transform", "magma"),
                (state["markers"], f"Markers (n={state['markers'].max()})", "nipy_spectral"),
                (overlay, f"GT green / prediction red (n={prediction.max()})", None),
            )
            for axis, (panel, title, cmap) in zip(axes.flat, panels):
                axis.imshow(panel, cmap=cmap)
                axis.set_title(title)
                axis.axis("off")
            fig.savefig(figures_dir / f"{stem}_qc.png", dpi=160)
            plt.close(fig)

    aggregate = {}
    for threshold in cfg["iou_thresholds"]:
        score = matching_dataset(true_masks, predicted_masks, thresh=threshold, show_progress=False)
        aggregate[str(threshold)] = score._asdict()

    result = {
        "status": "success" if all(x["predicted_instances"] > 0 for x in per_image) else "failed",
        "scope": "marker-controlled watershed baseline and evaluation",
        "algorithm": "Gaussian smoothing -> Otsu foreground -> cleanup -> EDT -> local-max markers -> watershed",
        "dataset_root": str(args.data_dir),
        "dataset_readme_sha256": sha256(args.data_dir / "README.md"),
        "n_images": len(pairs),
        "aggregate": aggregate,
        "per_image": per_image,
        "total_seconds": time.perf_counter() - started,
        "mean_runtime_seconds": float(np.mean([x["runtime_seconds"] for x in per_image])),
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_image": skimage.__version__,
        },
        "config": cfg,
    }

    def json_default(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(f"Cannot serialize {type(value).__name__}")

    (args.output_dir / "metrics.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=json_default) + "\n"
    )
    print(json.dumps(
        {k: result[k] for k in ("status", "n_images", "aggregate", "total_seconds")},
        indent=2,
        default=json_default,
    ))


if __name__ == "__main__":
    main()
