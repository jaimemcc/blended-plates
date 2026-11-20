"""Make food masks by differencing each photo against the empty-plate reference.

Usage (from the project root):
    pixi run python scripts/food_masks.py <reference.JPG> <out_dir> <photo.JPG> [<photo.JPG> ...]

Steps per photo:
  1. Find the plate centre (same method as measure_plate.py) and shift the photo
     so its plate centre lines up with the reference plate centre.
  2. Compare the aligned photo with the reference in Lab colour space.
  3. Threshold the difference (Otsu, inside the plate disk) to get a food mask.
  4. Clean up with morphology and drop tiny specks.

Writes:
  <out_dir>/<stem>_mask.png     white = food, black = plate/background
  <out_dir>/<stem>_qc.jpg       small overlay for checking by eye
and prints the food area (pixels) and shift applied, for a monotonic-with-kcal check.
"""

import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from measure_plate import SCALE, load, plate_geometry  # noqa: E402

MIN_COMPONENT_PX = 2000
ECC_MIN_CC = 0.6      # reject ECC refinements with weak correlation
ECC_MAX_SHIFT = 15    # full-res px; larger refinements are treated as divergence


def centre_full_res(img):
    small = cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
    cx, cy, r, _ = plate_geometry(small)
    return cx / SCALE, cy / SCALE, r / SCALE


def align_to(img, shift_x, shift_y):
    h, w = img.shape[:2]
    m = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
    return cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_REPLICATE)


def refine_alignment(aligned, ref, rcx, rcy, r):
    """Sub-pixel translation refinement (ECC) on the plate rim region."""
    g_ref = cv2.cvtColor(cv2.resize(ref, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY).astype(np.float32)
    g_al = cv2.cvtColor(cv2.resize(aligned, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY).astype(np.float32)
    m = np.zeros(g_ref.shape, np.uint8)
    cv2.circle(m, (int(rcx / 2), int(rcy / 2)), int(r / 2 * 1.02), 255, -1)
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    try:
        cc, warp = cv2.findTransformECC(g_ref, g_al, warp, cv2.MOTION_TRANSLATION, crit, m, 5)
    except cv2.error:
        return aligned
    dx, dy = warp[0, 2] * 2, warp[1, 2] * 2
    # Only trust a confident, small refinement; otherwise keep the coarse alignment.
    if cc < ECC_MIN_CC or abs(dx) > ECC_MAX_SHIFT or abs(dy) > ECC_MAX_SHIFT:
        return aligned
    h, w = aligned.shape[:2]
    m2 = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(aligned, m2, (w, h), borderMode=cv2.BORDER_REPLICATE)


def lab_diff(a, b):
    la = cv2.cvtColor(a, cv2.COLOR_BGR2LAB).astype(np.float32)
    lb = cv2.cvtColor(b, cv2.COLOR_BGR2LAB).astype(np.float32)
    # Ignore lightness differences a little; food differs mostly in colour and texture.
    d = np.sqrt((la[:, :, 0] - lb[:, :, 0]) ** 2 * 0.5 + (la[:, :, 1] - lb[:, :, 1]) ** 2 + (la[:, :, 2] - lb[:, :, 2]) ** 2)
    return d


def food_mask(aligned, ref, cx, cy, r):
    d = lab_diff(cv2.GaussianBlur(aligned, (5, 5), 0), cv2.GaussianBlur(ref, (5, 5), 0))
    disk = np.zeros(d.shape, np.uint8)
    cv2.circle(disk, (int(round(cx)), int(round(cy))), int(r * 0.97), 255, -1)
    values = d[disk > 0].astype(np.uint8)
    t, _ = cv2.threshold(values.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = ((d > t) & (disk > 0)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= MIN_COMPONENT_PX
    mask = keep[labels].astype(np.uint8) * 255
    return mask, t


def main(ref_path, out_dir, photo_paths):
    os.makedirs(out_dir, exist_ok=True)
    ref = load(ref_path)
    rcx, rcy, _ = centre_full_res(ref)
    for p in photo_paths:
        img = load(p)
        cx, cy, r = centre_full_res(img)
        dx, dy = rcx - cx, rcy - cy
        aligned = refine_alignment(align_to(img, dx, dy), ref, rcx, rcy, r)
        mask, t = food_mask(aligned, ref, rcx, rcy, r)
        stem = os.path.splitext(os.path.basename(p))[0]
        folder = os.path.basename(os.path.dirname(os.path.abspath(p)))
        tag = f"{folder}_{stem}"
        cv2.imwrite(os.path.join(out_dir, f"{tag}_mask.png"), mask)
        small_img = cv2.resize(aligned, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
        small_mask = cv2.resize(mask, small_img.shape[1::-1], interpolation=cv2.INTER_NEAREST)
        overlay = small_img.copy()
        overlay[small_mask > 0] = (0, 0, 255)
        cv2.imwrite(os.path.join(out_dir, f"{tag}_qc.jpg"), overlay)
        area = int(np.count_nonzero(mask))
        print(f"{tag}: shift=({dx:+.0f},{dy:+.0f}) px  otsu={t:.0f}  food_area={area}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
