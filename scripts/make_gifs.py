"""Make simple GIFs of the blend changing for one or more meal totals.

Usage (from the project root):
    pixi run python scripts/make_gifs.py <meal_image_folder> <out_dir> <total_kcal> [<total_kcal> ...]

Frames run from all-protein to all-carb for each total, with a caption bar
similar to the slider viewer (carb kcal | protein kcal | total kcal).
"""

import glob
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

from slider_viewer import MAX_H, MAX_W, PATTERN  # noqa: E402  (same folder)

BAR_H = 40
FRAME_MS = 350


def frames_for(folder, total):
    rows = []
    for path in glob.glob(os.path.join(folder, "*.jpg")):
        m = PATTERN.search(os.path.basename(path))
        if m and int(m.group(1)) == total:
            c, p = int(m.group(2)), int(m.group(3))
            rows.append((c, p, path))
    return sorted(rows)  # ascending carb kcal: all protein -> all carb


def load_font():
    for name in ("segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, 20)
        except OSError:
            continue
    return ImageFont.load_default()


def make_gif(folder, out_dir, total, font):
    rows = frames_for(folder, total)
    if not rows:
        raise SystemExit(f"No frames for total {total} in {folder}")
    out = []
    for c, p, path in rows:
        img = Image.open(path).convert("RGB")
        img.thumbnail((MAX_W, MAX_H))
        canvas = Image.new("RGB", (img.width, img.height + BAR_H), (40, 40, 40))
        canvas.paste(img, (0, BAR_H))
        draw = ImageDraw.Draw(canvas)
        text = f"carb {c} kcal  |  protein {p} kcal  |  total {total} kcal"
        draw.text((12, 9), text, fill=(240, 240, 240), font=font)
        out.append(canvas)
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, f"blend_total{total}.gif")
    out[0].save(dest, save_all=True, append_images=out[1:], duration=FRAME_MS, loop=0)
    print(f"{dest}  ({len(out)} frames)")


def main(folder, out_dir, totals):
    font = load_font()
    for t in totals:
        make_gif(folder, out_dir, t, font)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]])
