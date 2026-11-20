"""Measure plate position and food extent relative to the plate midline.

Usage (from the project root):
    pixi run python scripts/measure_plate.py photos/empty_plate.JPG photos/carbs/fries_261119/ff_775.JPG ...

For each image it prints:
  - plate centre (x, y) and radius, from the largest low-saturation (white) blob
  - food extent: the rightmost food pixel on the left half and the leftmost food
    pixel on the right half, as offsets from the plate centre x (in pixels)
"""

import sys

import cv2
import numpy as np

SCALE = 0.25  # work on a quarter-size image for speed; results are scaled back


def load(path):
    img = cv2.imread(path)
    if img is None:
        raise SystemExit(f"Could not read {path}")
    return img


def plate_geometry(bgr_small):
    hsv = cv2.cvtColor(bgr_small, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    # Plate is pale/low saturation; wood is saturated orange.
    plate = ((sat < 60) & (val > 120)).astype(np.uint8) * 255
    plate = cv2.morphologyEx(plate, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(plate)
    # Largest component, ignoring background label 0.
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    blob = (labels == idx).astype(np.uint8) * 255
    # Fill holes (food sits inside the plate) by filling the blob's convex hull.
    contours, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = cv2.convexHull(max(contours, key=cv2.contourArea))
    (cx, cy), r = cv2.minEnclosingCircle(hull)
    return cx, cy, r, blob


def food_mask(bgr_small, plate_blob, cx, cy, r):
    # Food = anything inside the plate's disk that is not plate-coloured.
    # The plate blob has food-shaped holes, so disk minus blob is the food.
    disk = np.zeros_like(plate_blob)
    cv2.circle(disk, (int(cx), int(cy)), int(r * 0.92), 255, -1)
    food = cv2.bitwise_and(disk, cv2.bitwise_not(plate_blob))
    food = cv2.morphologyEx(food, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return food


def main(paths):
    for path in paths:
        full = load(path)
        h, w = full.shape[:2]
        small = cv2.resize(full, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
        cx, cy, r, blob = plate_geometry(small)
        food = food_mask(small, blob, cx, cy, r)
        ys, xs = np.nonzero(food)
        mid = cx
        left = xs[xs < mid]
        right = xs[xs >= mid]
        inv = 1 / SCALE
        print(f"{path}  image {w}x{h}")
        print(f"  plate centre x={cx * inv:.0f} y={cy * inv:.0f} radius={r * inv:.0f}")
        if left.size:
            print(f"  carb food rightmost x offset from centre: {(left.max() - mid) * inv:+.0f} px")
        else:
            print("  carb food on left: none detected")
        if right.size:
            print(f"  protein food leftmost x offset from centre: {(right.min() - mid) * inv:+.0f} px")
        else:
            print("  protein food on right: none detected")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
