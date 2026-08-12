#!/usr/bin/env python3
"""Generate a deterministic transcript point cloud for a Baysor smoke reproduction."""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=202208)
    parser.add_argument("--cells", type=int, default=60)
    parser.add_argument("--molecules-per-cell", type=int, default=80)
    parser.add_argument("--noise-molecules", type=int, default=600)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    genes = ["Gad1", "Slc17a7", "Aldoc", "Pdgfra", "Sox10", "Ttr"]
    profiles = [
        [0.58, 0.08, 0.10, 0.08, 0.08, 0.08],
        [0.08, 0.58, 0.08, 0.10, 0.08, 0.08],
        [0.08, 0.08, 0.50, 0.14, 0.12, 0.08],
    ]

    ncols = math.ceil(math.sqrt(args.cells))
    rows: list[tuple[float, float, str, int, bool]] = []
    centers: list[tuple[float, float]] = []
    for cell_id in range(1, args.cells + 1):
        row, col = divmod(cell_id - 1, ncols)
        cx = 12.0 + col * 19.0 + rng.uniform(-1.2, 1.2)
        cy = 12.0 + row * 19.0 + rng.uniform(-1.2, 1.2)
        centers.append((cx, cy))
        profile = profiles[(cell_id - 1) % len(profiles)]
        for _ in range(args.molecules_per_cell):
            x = rng.gauss(cx, 2.6)
            y = rng.gauss(cy, 2.6)
            gene = rng.choices(genes, weights=profile, k=1)[0]
            rows.append((x, y, gene, cell_id, False))

    xmax = max(x for x, _ in centers) + 12.0
    ymax = max(y for _, y in centers) + 12.0
    for _ in range(args.noise_molecules):
        rows.append((rng.uniform(0, xmax), rng.uniform(0, ymax), rng.choice(genes), 0, True))

    rng.shuffle(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["x", "y", "gene", "cell_truth", "is_noise_truth"])
        for x, y, gene, cell_id, is_noise in rows:
            writer.writerow([f"{x:.6f}", f"{y:.6f}", gene, cell_id, str(is_noise).lower()])

    print(f"wrote {len(rows)} molecules from {args.cells} cells to {args.output}")


if __name__ == "__main__":
    main()
