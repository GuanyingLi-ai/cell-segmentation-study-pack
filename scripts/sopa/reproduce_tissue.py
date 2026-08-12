#!/usr/bin/env python3
"""Reproduce SOPA tissue segmentation on a 10x Xenium output directory."""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import sopa
import spatialdata as sd
from shapely.geometry import Point, box


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Xenium outs directory")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--channel", default="DAPI", help="Morphology channel")
    parser.add_argument("--level", type=int, default=2, help="Image pyramid level")
    parser.add_argument("--expand-radius-ratio", type=float, default=0.05)
    parser.add_argument("--skip-run", action="store_true", help="Validate an existing zarr")
    parser.add_argument("--fresh", action="store_true", help="Replace existing zarr")
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in value).strip("_")


def cell_stats(data: Path) -> tuple[list[float], pd.Series, pd.Series, int]:
    path = data / "cell_boundaries.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing validation file: {path}")
    frame = pd.read_parquet(path)
    grouped = frame.groupby("cell_id").agg(
        x0=("vertex_x", "min"), y0=("vertex_y", "min"),
        x1=("vertex_x", "max"), y1=("vertex_y", "max"),
    )
    bounds = [float(grouped.x0.min()), float(grouped.y0.min()),
              float(grouped.x1.max()), float(grouped.y1.max())]
    return bounds, (grouped.x0 + grouped.x1) / 2, (grouped.y0 + grouped.y1) / 2, len(grouped)


def validate(sdata: sd.SpatialData, bounds: list[float], cx: pd.Series,
             cy: pd.Series, n_cells: int, channel: str, level: int,
             zarr_path: Path, elapsed: float | None) -> dict:
    roi = sdata["region_of_interest"].geometry.iloc[0]
    image = sdata.images["morphology_focus"]["scale0"]["image"]
    slide_area = int(image.sizes["y"]) * int(image.sizes["x"])
    reference_box = box(*bounds)
    inside = sum(roi.contains(Point(x, y)) for x, y in zip(cx, cy))
    inside_pct = 100 * inside / n_cells
    roi_pct = 100 * roi.area / slide_area
    intersection_pct = 100 * roi.intersection(reference_box).area / reference_box.area
    passed = inside_pct >= 95 and roi_pct <= 50
    return {
        "channel": channel, "level": level, "zarr_path": str(zarr_path),
        "n_cells": n_cells, "roi_area_pct": round(roi_pct, 2),
        "cell_centroid_inside_pct": round(inside_pct, 1),
        "roi_bbox_intersection_pct": round(intersection_pct, 1),
        "elapsed_min": round(elapsed / 60, 1) if elapsed is not None else None,
        "passed": passed,
    }


def save_plot(sdata: sd.SpatialData, bounds: list[float], channel: str,
              report: dict, path: Path) -> None:
    x0, y0, x1, y1 = bounds
    pad = 800
    image = sdata.images["morphology_focus"]["scale4"]["image"]
    crop = image.sel(c=channel, y=slice(y0 - pad, y1 + pad),
                     x=slice(x0 - pad, x1 + pad)).compute().values
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.imshow(crop, cmap="gray", origin="upper",
              extent=[x0 - pad, x1 + pad, y1 + pad, y0 - pad])
    sdata["region_of_interest"].plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2)
    ax.set_title(f"{channel}: ROI={report['roi_area_pct']}%, cells inside={report['cell_centroid_inside_pct']}%")
    ax.set_xlim(x0 - pad, x1 + pad)
    ax.set_ylim(y1 + pad, y0 - pad)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    args = parse_args()
    data = args.data.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not data.exists():
        raise FileNotFoundError(f"Data directory not found: {data}")
    output.mkdir(parents=True, exist_ok=True)
    tag = f"{safe_name(args.channel)}_L{args.level}"
    zarr_path = output / "zarr" / f"tissue_{tag}.zarr"
    report_path = output / "reports" / f"tissue_{tag}.json"
    plot_path = output / "qc" / f"tissue_{tag}.png"
    for path in (zarr_path.parent, report_path.parent, plot_path.parent):
        path.mkdir(parents=True, exist_ok=True)

    elapsed = None
    if args.skip_run:
        if not zarr_path.exists():
            raise FileNotFoundError(f"Existing zarr not found: {zarr_path}")
        sdata = sd.read_zarr(zarr_path)
    else:
        if args.fresh and zarr_path.exists():
            shutil.rmtree(zarr_path)
        if zarr_path.exists():
            sdata = sd.read_zarr(zarr_path)
        else:
            sdata = sopa.io.xenium(data, aligned_images=False, transcripts=False)
            available = [str(c) for c in sopa.utils.get_channel_names(sdata)]
            if args.channel not in available:
                raise ValueError(f"Unknown channel {args.channel!r}; available: {available}")
            started = time.time()
            sopa.segmentation.tissue(
                sdata, mode="staining", image_key="morphology_focus",
                channel=args.channel, level=args.level,
                expand_radius_ratio=args.expand_radius_ratio,
            )
            elapsed = time.time() - started
            sdata.write(zarr_path)

    bounds, cx, cy, n_cells = cell_stats(data)
    report = validate(sdata, bounds, cx, cy, n_cells, args.channel,
                      args.level, zarr_path, elapsed)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if not args.no_plots:
        save_plot(sdata, bounds, args.channel, report, plot_path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Report: {report_path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
