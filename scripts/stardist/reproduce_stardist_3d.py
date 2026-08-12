#!/usr/bin/env python3
"""Reproduce official StarDist 3D demo-model inference and evaluation."""

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
from stardist.models import StarDist3D


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
    parser.add_argument("--dataset-archive", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def boundary_overlay(image: np.ndarray, truth: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    rgb = np.repeat(np.clip(image, 0, 1)[..., None], 3, axis=-1)
    rgb[find_boundaries(truth, mode="inner")] = (0.1, 0.9, 0.2)
    rgb[find_boundaries(prediction, mode="inner")] = (1.0, 0.15, 0.15)
    return rgb


def main() -> None:
    args = parse_args()
    cfg = json.loads(args.config.read_text())
    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    tf.random.set_seed(cfg["seed"])

    images = sorted(args.data_dir.glob(cfg["input_glob"]))
    labels_by_name = {p.name: p for p in args.data_dir.glob(cfg["label_glob"])}
    pairs = [(p, labels_by_name[p.name]) for p in images if p.name in labels_by_name]
    if not pairs:
        raise RuntimeError("No matching 3D image/mask pairs found")

    masks_dir = args.output_dir / "masks"
    figures_dir = args.output_dir / "figures"
    masks_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    model = StarDist3D.from_pretrained(cfg["model"])
    predict_kwargs = {}
    if cfg["prob_thresh"] is not None:
        predict_kwargs["prob_thresh"] = cfg["prob_thresh"]
    if cfg["nms_thresh"] is not None:
        predict_kwargs["nms_thresh"] = cfg["nms_thresh"]

    true_masks, predicted_masks, per_volume = [], [], []
    started = time.perf_counter()
    for image_path, label_path in pairs:
        image = tifffile.imread(image_path)
        truth = tifffile.imread(label_path).astype(np.int32, copy=False)
        normalized = normalize(
            image,
            cfg["normalization_percentiles"][0],
            cfg["normalization_percentiles"][1],
            axis=tuple(cfg["normalization_axes"]),
        )
        tic = time.perf_counter()
        prediction, details = model.predict_instances(normalized, **predict_kwargs)
        seconds = time.perf_counter() - tic
        prediction = prediction.astype(np.int32, copy=False)
        tifffile.imwrite(masks_dir / image_path.name, prediction, compression="zlib")
        score = matching(truth, prediction, thresh=0.5)
        per_volume.append({
            "volume": image_path.name,
            "shape_zyx": list(image.shape),
            "ground_truth_instances": int(truth.max()),
            "predicted_instances": int(prediction.max()),
            "polyhedra": int(len(details["points"])),
            "precision_at_0_5": score.precision,
            "recall_at_0_5": score.recall,
            "f1_at_0_5": score.f1,
            "panoptic_quality_at_0_5": score.panoptic_quality,
            "inference_seconds": seconds,
        })
        true_masks.append(truth)
        predicted_masks.append(prediction)

        z, y, x = (s // 2 for s in image.shape)
        panels = (
            (normalized[z], truth[z], prediction[z], "XY"),
            (normalized[:, y, :], truth[:, y, :], prediction[:, y, :], "XZ"),
            (normalized[:, :, x], truth[:, :, x], prediction[:, :, x], "YZ"),
        )
        fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
        for col, (raw, gt, pred, plane) in enumerate(panels):
            axes[0, col].imshow(raw, cmap="gray", vmin=0, vmax=1, aspect="auto")
            axes[0, col].set_title(f"{plane} input")
            axes[1, col].imshow(boundary_overlay(raw, gt, pred), aspect="auto")
            axes[1, col].set_title(f"{plane}: GT green / prediction red")
            axes[0, col].axis("off")
            axes[1, col].axis("off")
        fig.suptitle(f"{image_path.name}: GT={truth.max()}, prediction={prediction.max()}")
        fig.savefig(figures_dir / f"{image_path.stem}_qc.png", dpi=160)
        plt.close(fig)

    aggregate = {}
    for threshold in cfg["iou_thresholds"]:
        aggregate[str(threshold)] = matching_dataset(
            true_masks, predicted_masks, thresh=threshold, show_progress=False
        )._asdict()

    result = {
        "status": "success" if all(x["predicted_instances"] > 0 for x in per_volume) else "failed",
        "scope": "official synthetic demo-model 3D inference and evaluation; no retraining",
        "model": cfg["model"],
        "model_thresholds": {"prob": float(model.thresholds.prob), "nms": float(model.thresholds.nms)},
        "dataset_root": str(args.data_dir),
        "dataset_archive_sha256": sha256(args.dataset_archive) if args.dataset_archive else None,
        "n_volumes": len(pairs),
        "aggregate": aggregate,
        "per_volume": per_volume,
        "total_seconds": time.perf_counter() - started,
        "mean_inference_seconds": float(np.mean([x["inference_seconds"] for x in per_volume])),
        "environment": {
            "platform": platform.platform(), "machine": platform.machine(),
            "python": sys.version.split()[0], "stardist": stardist_version,
            "csbdeep": csbdeep.__version__, "tensorflow": tf.__version__, "numpy": np.__version__,
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
        {k: result[k] for k in ("status", "model", "n_volumes", "aggregate", "total_seconds")},
        indent=2, default=json_default,
    ))


if __name__ == "__main__":
    main()
