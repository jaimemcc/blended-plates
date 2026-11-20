# blended-plates

Builds blended-meal images (carb on the left half of the plate, protein on the right) at fixed meal totals, for a slider-based experiment. See `PLANNING.md` for the design.

## Setup

Dependencies are managed with [pixi](https://pixi.sh):

```
pixi install
```

The source photos are **not** in the repo. They live in the folder set by `BLENDED_FOODS_DIR` in `pixi.toml` (currently `C:/Users/jmc010/Data/blended-foods`). Each carb or protein set is a subfolder (e.g. `fries_261119`, `fusilli_261119`, `meatballs_261120`), and `empty_plate.JPG` sits at the top level. Keep a backup of that folder elsewhere.

To check the photos against the recorded checksums:

```
pixi run photo-check
```

`photo_manifest.csv` records the SHA-256 of every photo. Re-run `pixi run python scripts/photo_manifest.py write` only when you deliberately change the photo set.

## Regenerating the outputs

`out/` and `masks/` are generated and git-ignored. To rebuild them:

```
pixi run compose-fries
pixi run compose-fusilli
pixi run gifs-fries
pixi run gifs-fusilli
```

To combine different sets, call the script directly with any set names from the data folder:

```
pixi run python scripts/compose_pilot.py <carb_set> <protein_set> out/<name> 200 400 600 750
```

Each composite run skips any split whose photo is missing (e.g. the all-protein 750 split, since the meatball photos stop at 725 kcal).

## Checking the results

```
pixi run gui
```

Opens the slider viewer on `out/`, with a set dropdown and a meal-total dropdown.

## Scripts

- `scripts/photo_manifest.py`: write or check the SHA-256 manifest of the photo folder.
- `scripts/measure_plate.py`: plate centre and radius, for checking alignment.
- `scripts/food_masks.py`: food masks by differencing each photo against the empty plate, with QC overlays in `masks/`.
- `scripts/compose_pilot.py`: builds the composite meals for one carb/protein pair.
- `scripts/make_gifs.py`: animated GIFs of the blend for chosen totals.
- `scripts/slider_viewer.py`: simple slider GUI for checking the images.
