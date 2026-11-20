"""Simple slider viewer for checking generated meal images.

Usage (from the project root):
    pixi run python scripts/slider_viewer.py <root_folder>

The root folder holds one subfolder per carb/protein set, each containing
meal images named like meal0400_c175_p225.jpg (from compose_pilot.py), e.g.
    out/pilot/          (fries x meatballs)
    out/pilot_fusilli/  (fusilli x meatballs)
If the root folder itself contains meal images, it is shown as a single set.

Pick a set and a meal total from the drop-downs, then drag the slider (or use
the left/right arrow keys) to move from all-protein to all-carb for that total.
Throwaway tool for checking images, not the experiment platform.
"""

import glob
import os
import re
import sys
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

PATTERN = re.compile(r"meal(\d{4})_c(\d{3})_p(\d{3})\.jpg$", re.IGNORECASE)
MAX_W, MAX_H = 900, 560


def index_meals(folder):
    """Return {total: {carb_kcal: (protein_kcal, path)}} for one folder."""
    meals = {}
    for path in glob.glob(os.path.join(folder, "*.jpg")):
        m = PATTERN.search(os.path.basename(path))
        if not m:
            continue
        total, c, p = int(m.group(1)), int(m.group(2)), int(m.group(3))
        meals.setdefault(total, {})[c] = (p, path)
    return meals


def index_sets(root):
    """Return {set_name: {total: {carb_kcal: (protein_kcal, path)}}} for every set under root."""
    sets = {}
    if index_meals(root):
        sets[os.path.basename(os.path.abspath(root))] = index_meals(root)
    for sub in sorted(os.listdir(root)):
        path = os.path.join(root, sub)
        if os.path.isdir(path):
            meals = index_meals(path)
            if meals:
                sets[sub] = meals
    return sets


class Viewer(tk.Tk):
    def __init__(self, root):
        super().__init__()
        self.title("Blended plates viewer")
        self.sets = index_sets(root)
        if not self.sets:
            raise SystemExit(f"No meal images (meal####_c###_p###.jpg) found in {root}")
        self.photo = None
        self.cache = {}

        # Pack the slider first (bottom) so it is never pushed off-screen by the image.
        bottom = ttk.Frame(self, padding=8)
        bottom.pack(side="bottom", fill="x")

        top = ttk.Frame(self, padding=8)
        top.pack(side="top", fill="x")
        ttk.Label(top, text="Set:").pack(side="left")
        self.set_var = tk.StringVar(value=sorted(self.sets)[0])
        set_combo = ttk.Combobox(top, textvariable=self.set_var, state="readonly", width=18,
                                 values=sorted(self.sets))
        set_combo.pack(side="left", padx=6)
        set_combo.bind("<<ComboboxSelected>>", lambda e: self.on_set_change())

        ttk.Label(top, text="Meal total (kcal):").pack(side="left", padx=(12, 0))
        self.total_var = tk.StringVar()
        self.total_combo = ttk.Combobox(top, textvariable=self.total_var, state="readonly", width=8)
        self.total_combo.pack(side="left", padx=6)
        self.total_combo.bind("<<ComboboxSelected>>", lambda e: self.on_total_change())

        self.info = ttk.Label(top, text="")
        self.info.pack(side="right")

        self.image_label = ttk.Label(self)
        self.image_label.pack(side="top", padx=8, pady=4)

        self.slider = ttk.Scale(bottom, from_=0, to=1, orient="horizontal", command=self.on_slide)
        self.slider.pack(fill="x", expand=True)
        labels = ttk.Frame(bottom)
        labels.pack(fill="x")
        ttk.Label(labels, text="all protein").pack(side="left")
        ttk.Label(labels, text="all carb").pack(side="right")

        self.on_set_change()
        self.bind("<Left>", lambda e: self.step(-1))
        self.bind("<Right>", lambda e: self.step(1))

    @property
    def meals(self):
        return self.sets[self.set_var.get()]

    def on_set_change(self):
        totals = sorted(self.meals)
        self.total_combo.configure(values=[str(t) for t in totals])
        # Keep the current total if this set has it, otherwise use the first total.
        if int(self.total_var.get() or -1) not in totals:
            self.total_var.set(str(totals[0]))
        self.on_total_change()

    def on_total_change(self):
        self.steps = sorted(self.meals[int(self.total_var.get())].keys())  # carb kcal values
        self.slider.configure(from_=0, to=len(self.steps) - 1)
        self.slider.set(len(self.steps) // 2)
        self.show_index(len(self.steps) // 2)

    def on_slide(self, value):
        self.show_index(int(round(float(value))))

    def step(self, delta):
        idx = int(round(float(self.slider.get()))) + delta
        idx = max(0, min(len(self.steps) - 1, idx))
        self.slider.set(idx)
        self.show_index(idx)

    def show_index(self, idx):
        total = int(self.total_var.get())
        carb = self.steps[idx]
        protein, path = self.meals[total][carb]
        self.info.configure(text=f"carb {carb} kcal  |  protein {protein} kcal  |  total {total} kcal")
        if path not in self.cache:
            img = Image.open(path)
            img.thumbnail((MAX_W, MAX_H))
            self.cache[path] = ImageTk.PhotoImage(img)
        self.photo = self.cache[path]
        self.image_label.configure(image=self.photo)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    Viewer(sys.argv[1]).mainloop()
