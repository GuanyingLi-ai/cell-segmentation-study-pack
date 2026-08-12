#!/usr/bin/env python3
"""Evaluate Baysor output against deterministic synthetic truth and draw QC."""

from __future__ import annotations

import argparse
import csv
import colorsys
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.metrics import adjusted_rand_score


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segmentation", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--figure", type=Path, required=True)
    args = parser.parse_args()

    with args.segmentation.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError("segmentation output is empty")

    inferred_col = "cell" if "cell" in rows[0] else "cell_id"
    noise_col = "is_noise"
    inferred_labels = sorted({r[inferred_col] for r in rows if r[inferred_col]})
    inferred_to_int = {label: i + 1 for i, label in enumerate(inferred_labels)}
    truth_rows = [r for r in rows if int(r["cell_truth"]) > 0]
    y_true = [int(r["cell_truth"]) for r in truth_rows]
    y_pred = [inferred_to_int.get(r[inferred_col], 0) if not as_bool(r[noise_col]) else 0 for r in truth_rows]

    assigned = [r for r in rows if not as_bool(r[noise_col]) and r[inferred_col] in inferred_to_int]
    by_cell: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in assigned:
        by_cell[inferred_to_int[row[inferred_col]]].append(row)

    correct = 0
    truth_assigned = 0
    for cell_rows in by_cell.values():
        counts = Counter(int(r["cell_truth"]) for r in cell_rows if int(r["cell_truth"]) > 0)
        if counts:
            correct += counts.most_common(1)[0][1]
            truth_assigned += sum(counts.values())

    counts = [len(v) for v in by_cell.values()]
    metrics = {
        "n_molecules": len(rows),
        "n_truth_cells": len({int(r["cell_truth"]) for r in rows if int(r["cell_truth"]) > 0}),
        "n_inferred_cells": len(by_cell),
        "assigned_rate_all": len(assigned) / len(rows),
        "assigned_rate_truth_molecules": sum(p > 0 for p in y_pred) / len(y_pred),
        "adjusted_rand_index_truth_molecules": adjusted_rand_score(y_true, y_pred),
        "weighted_cell_purity": correct / truth_assigned if truth_assigned else 0.0,
        "median_molecules_per_inferred_cell": float(statistics.median(counts)) if counts else 0.0,
        "min_molecules_per_inferred_cell": min(counts) if counts else 0,
        "max_molecules_per_inferred_cell": max(counts) if counts else 0,
    }
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    xs = [float(r["x"]) for r in rows]
    ys = [float(r["y"]) for r in rows]
    pred = [inferred_to_int.get(r[inferred_col], 0) if not as_bool(r[noise_col]) else 0 for r in rows]
    truth = [int(r["cell_truth"]) for r in rows]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    panel_w, panel_h, margin = 520, 430, 45
    def color(label: int) -> str:
        if label == 0:
            return "#c8c8c8"
        r, g, b = colorsys.hsv_to_rgb((label * 0.61803398875) % 1.0, 0.72, 0.90)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    def points(labels: list[int], xoff: int) -> str:
        out = []
        for x, y, label in zip(xs, ys, labels):
            px = xoff + margin + (x - xmin) / (xmax - xmin) * (panel_w - 2 * margin)
            py = margin + 35 + (y - ymin) / (ymax - ymin) * (panel_h - 2 * margin)
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.35" fill="{color(label)}"/>')
        return "".join(out)
    width, height = panel_w * 2 + 20, panel_h + 70
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#222}.title{font-size:18px;font-weight:700}.sub{font-size:14px;font-weight:600}</style>',
           f'<text class="title" x="{width/2}" y="24" text-anchor="middle">Baysor v0.7.1 synthetic smoke reproduction · ARI {metrics["adjusted_rand_index_truth_molecules"]:.3f}</text>',
           f'<text class="sub" x="{panel_w/2}" y="52" text-anchor="middle">Synthetic truth (gray = background)</text>',
           f'<text class="sub" x="{panel_w+20+panel_w/2}" y="52" text-anchor="middle">Baysor assignment</text>',
           points(truth, 0), points(pred, panel_w + 20), '</svg>']
    args.figure.parent.mkdir(parents=True, exist_ok=True)
    args.figure.write_text("".join(svg), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
