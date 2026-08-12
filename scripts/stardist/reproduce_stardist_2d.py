#!/usr/bin/env python3
"""Reproduce StarDist 2D pretrained inference on the paper's DSB2018 test split."""

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

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

import csbdeep
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import tifffile
from csbdeep.utils import normalize
from skimage.segmentation import find_boundaries
from stardist import __version__ as stardist_version
from stardist.matching import matching, matching_dataset
from stardist.models import StarDist2D


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


def main() -> None:
    args = parse_args()
    cfg = json.loads(args.config.read_text())
    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    tf.random.set_seed(cfg["seed"])

    image_paths = sorted(args.data_dir.glob(cfg["input_glob"]))
    label_paths = sorted(args.data_dir.glob(cfg["label_glob"]))
    labels_by_name = {p.name: p for p in label_paths}
    pairs = [(p, labels_by_name[p.name]) for p in image_paths if p.name in labels_by_name]
    if not pairs:
        raise RuntimeError("No matching image/mask pairs found")

    masks_dir = args.output_dir / "masks"
    figures_dir = args.output_dir / "figures"
    masks_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    model = StarDist2D.from_pretrained(cfg["model"])
    percentile_low, percentile_high = cfg["normalization_percentiles"]
    predict_kwargs = {}
    if cfg["prob_thresh"] is not None:
        predict_kwargs["prob_thresh"] = cfg["prob_thresh"]
    if cfg["nms_thresh"] is not None:
        predict_kwargs["nms_thresh"] = cfg["nms_thresh"]

    true_masks, predicted_masks, per_image = [], [], []
    started = time.perf_counter()
    for index, (image_path, label_path) in enumerate(pairs):
        image = tifffile.imread(image_path)
        truth = tifffile.imread(label_path).astype(np.int32, copy=False)
        normalized = normalize(image, percentile_low, percentile_high, axis=(0, 1))
        tic = time.perf_counter()
        prediction, _ = model.predict_instances(normalized, **predict_kwargs)
        seconds = time.perf_counter() - tic
        prediction = prediction.astype(np.int32, copy=False)
        tifffile.imwrite(masks_dir / image_path.name, prediction, compression="zlib")
        score = matching(truth, prediction, thresh=0.5)
        per_image.append({
            "image": image_path.name,
            "ground_truth_instances": int(truth.max()),
            "predicted_instances": int(prediction.max()),
            "precision_at_0_5": score.precision,
            "recall_at_0_5": score.recall,
            "f1_at_0_5": score.f1,
            "mean_matched_score_at_0_5": score.mean_matched_score,
            "panoptic_quality_at_0_5": score.panoptic_quality,
            "inference_seconds": seconds,
        })
        true_masks.append(truth)
        predicted_masks.append(prediction)

        if index < cfg["qc_images"]:
            rgb = np.repeat(normalized[..., None], 3, axis=-1)
            rgb = np.clip(rgb, 0, 1)
            overlay = rgb.copy()
            overlay[find_boundaries(truth, mode="inner")] = (0.1, 0.9, 0.2)
            overlay[find_boundaries(prediction, mode="inner")] = (1.0, 0.15, 0.15)
            fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
            axes[0].imshow(image, cmap="gray")
            axes[0].set_title("Input")
            axes[1].imshow(truth, cmap="nipy_spectral")
            axes[1].set_title(f"Ground truth (n={truth.max()})")
            axes[2].imshow(overlay)
            axes[2].set_title(f"GT green / prediction red (n={prediction.max()})")
            for axis in axes:
                axis.axis("off")
            fig.savefig(figures_dir / f"{image_path.stem}_qc.png", dpi=160)
            plt.close(fig)

    aggregate = {}
    for threshold in cfg["iou_thresholds"]:
        score = matching_dataset(true_masks, predicted_masks, thresh=threshold, show_progress=False)
        aggregate[str(threshold)] = score._asdict()

    total_seconds = time.perf_counter() - started
    result = {
        "status": "success" if all(x["predicted_instances"] > 0 for x in per_image) else "failed",
        "scope": "pretrained inference and evaluation; no model retraining",
        "model": cfg["model"],
        "model_thresholds": {"prob": float(model.thresholds.prob), "nms": float(model.thresholds.nms)},
        "dataset_root": str(args.data_dir),
        "dataset_readme_sha256": sha256(args.data_dir / "README.md"),
        "n_images": len(pairs),
        "aggregate": aggregate,
        "per_image": per_image,
        "total_seconds": total_seconds,
        "mean_inference_seconds": float(np.mean([x["inference_seconds"] for x in per_image])),
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "stardist": stardist_version,
            "csbdeep": csbdeep.__version__,
            "tensorflow": tf.__version__,
            "numpy": np.__version__,
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
        {k: result[k] for k in ("status", "model", "n_images", "aggregate", "total_seconds")},
        indent=2,
        default=json_default,
    ))


if __name__ == "__main__":
    main()
