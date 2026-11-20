"""Compose blended-meal images for one carb/protein pair at several meal totals.

Usage (from the project root):
    pixi run python scripts/compose_pilot.py <carb_set> <protein_set> <out_dir> <total_kcal> [<total_kcal> ...]

<carb_set> and <protein_set> are folder names inside BLENDED_FOODS_DIR
(e.g. fries_261119), or full paths to a folder.

Example:
    pixi run python scripts/compose_pilot.py fries_261119 meatballs_261120 out/pilot 200 400 600 750

File names are expected to end in _<kcal>.JPG (e.g. ff_025.JPG -> 25 kcal).
The empty plate is empty_plate.JPG in BLENDED_FOODS_DIR (0 kcal on both sides).

For each total S, every split c + p = S (step 25 kcal) is produced:
    carb c kcal (from carb photo), protein p kcal (from protein photo).
Each composite = empty plate, with the carb food pasted where its mask is set,
then the protein food pasted where its mask is set (soft-edged).
"""

import glob
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from food_masks import (  # noqa: E402
    align_to,
    centre_full_res,
    food_mask,
    load,
    refine_alignment,
)

DATA_DIR = os.environ.get("BLENDED_FOODS_DIR", "")


def resolve_set(name):
    """A set name is a folder inside DATA_DIR; a full path is used as given."""
    if os.path.isdir(name):
        return name
    path = os.path.join(DATA_DIR, name)
    if not os.path.isdir(path):
        raise SystemExit(f"Photo set not found: {name} (looked in {DATA_DIR})")
    return path


REF_PATH = os.path.join(DATA_DIR, "empty_plate.JPG")
STEP = 25
FEATHER = 5  # px, full res: soft seam around each food layer


def index_photos(folder):
    """Map kcal -> file path for a folder of portion photos."""
    out = {}
    for p in glob.glob(os.path.join(folder, "*.JPG")) + glob.glob(os.path.join(folder, "*.jpg")):
        m = re.search(r"_(\d{3})\.(jpg|JPG)$", os.path.basename(p))
        if m:
            out[int(m.group(1))] = p
    return out


class Layer:
    """Aligned photo plus its food mask, computed once and reused."""

    def __init__(self, path, ref, rcx, rcy):
        img = load(path)
        cx, cy, r = centre_full_res(img)
        aligned = refine_alignment(align_to(img, rcx - cx, rcy - cy), ref, rcx, rcy, r)
        mask, _ = food_mask(aligned, ref, rcx, rcy, r)
        alpha = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), FEATHER)
        self.img = aligned.astype(np.float32)
        self.alpha = alpha[:, :, None]


def paste(canvas, layer):
    return canvas * (1 - layer.alpha) + layer.img * layer.alpha


def main(carb_dir, protein_dir, out_dir, totals):
    ref = load(REF_PATH)
    rcx, rcy, _ = centre_full_res(ref)
    carbs = index_photos(carb_dir)
    proteins = index_photos(protein_dir)
    os.makedirs(out_dir, exist_ok=True)
    cache = {}

    def layer(side, kcal):
        key = (side, kcal)
        if key not in cache:
            photos = carbs if side == "carb" else proteins
            if kcal not in photos:
                raise SystemExit(f"Missing {side} photo for {kcal} kcal")
            cache[key] = Layer(photos[kcal], ref, rcx, rcy)
        return cache[key]

    base = ref.astype(np.float32)
    for total in totals:
        for c in range(total, -1, -STEP):
            p = total - c
            if (c > 0 and c not in carbs) or (p > 0 and p not in proteins):
                print(f"skip total {total}: carb {c} / protein {p} photo missing")
                continue
            canvas = base.copy()
            if c > 0:
                canvas = paste(canvas, layer("carb", c))
            if p > 0:
                canvas = paste(canvas, layer("protein", p))
            name = f"meal{total:04d}_c{c:03d}_p{p:03d}.jpg"
            cv2.imwrite(os.path.join(out_dir, name), np.clip(canvas, 0, 255).astype(np.uint8),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(name)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    if not DATA_DIR:
        raise SystemExit("Set BLENDED_FOODS_DIR to the photo folder (see README.md).")
    main(resolve_set(sys.argv[1]), resolve_set(sys.argv[2]), sys.argv[3],
         [int(x) for x in sys.argv[4:]])
