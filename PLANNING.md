# Blended Plates: Planning Notes

## Goal

Combine photos of a **carb** (left half of the plate) and a **protein** (right half of the plate) into single images of a "meal", processed as a batch. Participants will drag a slider to move between carb-only and protein-only meals of the same total size.

- Several carb/protein pairings ("blends").
- Photos are taken in portions of **25 kcal steps**, from 25 kcal up to roughly 750–900 kcal per food.
- Meal sizes run from **200 kcal** upwards in 25 kcal steps, to about **750 kcal** (may change).
- For each meal size, the blend moves from all carb (e.g., 200 carb / 0 protein) to all protein (0 carb / 200 protein) in 25 kcal steps (e.g., 175 / 25, 150 / 50, …).
- Each food is confined to its half of the plate in the source photos.

## Requirements Summary

| Item | Value |
|---|---|
| Portion steps in source photos | 25 kcal |
| Source range per food | 25 kcal to ~750–900 kcal |
| Meal total sizes | 200 kcal to ~750 kcal, in 25 kcal steps (23 sizes) |
| Blend steps per meal size | 25 kcal (carb + protein = meal total) |
| Food location | Each food confined to its half |
| Plate position | Intended fixed; may drift slightly |

### Output count

Assuming constant meal total (see assumptions below), each carb–protein pair produces:

For each meal total S (200, 225, …, 750), there are S/25 + 1 blend steps. Summed over the 23 totals:

**460 images per carb–protein pair.**

| Carbs | Proteins | Pairs | Images |
|---|---|---|---|
| 3 | 3 | 9 | 4,140 |
| 4 | 4 | 16 | 7,360 |
| 5 | 5 | 25 | 11,500 |

Source photos needed are much fewer: roughly 30 per food (25–750 kcal), plus an empty-plate reference. The expensive part is the composite count, not the segmentation.

### Assumptions to confirm

1. **Constant meal total along the slider.** Moving the slider swaps calories between carb and protein but keeps the total fixed (e.g., 200 kcal meal = 200/0, 175/25, …, 0/200). If instead the total changes with the slider, the grid is different.
2. **Empty-plate reference exists.** The all-carb and all-protein ends need the other side empty. Ideally there is a 0 kcal photo of each side, or an empty plate shot in the same setup.
3. **Max size.** If meals go above 750 kcal, the source photos up to 900 kcal are needed too.
4. **Same lighting and camera** across all photos, so that the two halves blend without colour shifts.

## Key Insight: Confinement Simplifies the Problem

Because each food sits on its own half of the plate, the composite can be built from **food masks on an empty plate**, rather than by cutting a seam through two full photos:

- **Background:** the empty plate (0 kcal reference).
- **Carb layer:** the food pixels from the carb photo, restricted to the left half.
- **Protein layer:** the food pixels from the protein photo, restricted to the right half.

Restricting each mask to its half means no food from one side can leak into the other, and the seam sits on empty plate where it is invisible.

## Recommended Approach: Segmented Food Layers on an Empty Plate

This is Option C from below, simplified by the confinement.

1. **Align the photos (once).** Detect the plate in each photo (e.g., OpenCV `HoughCircles`, or template match on the empty-plate shot). Align everything to the reference with a translation/rotation/scale. Check alignment on a few samples.
2. **Create one food mask per source photo.** Run a segmentation tool on each carb and protein photo:
   - `rembg` for a quick first pass.
   - Segment Anything (SAM) if `rembg` misses parts of rice, sauces, or mixed dishes. Click or box prompts help.
   - Photoshop "Select Subject" plus manual cleanup for any stubborn photos.
3. **Restrict masks to halves.** Carb mask = food mask ∩ left half. Protein mask = food mask ∩ right half. (If segmentation is unreliable, a plain half-plane mask is a valid fallback, since the foods are already confined.)
4. **Composite.** For each blend, start from the empty plate, paste the carb layer and protein layer using their masks, with a slight feather on mask edges. Shadows may need a soft shadow layer or be left as-is for consistency.
5. **Batch.** Generate every combination from parameters (see manifest below), not by hand.

Segmentation runs once per source photo (about 60 photos per food type, including the empty plate), not once per composite. That makes the 460-per-pair output cheap to produce.

**Sanity check:** the food mask area for each carb and protein should increase roughly monotonically with kcal. A photo that breaks this is probably mis-segmented or mis-shot.

## Manifest and Naming

Generate the manifest from parameters so the grid is exact and auditable.

Source files, one per food per kcal step:

```
carbs/rice/rice_carb_025kcal.jpg
carbs/rice/rice_carb_050kcal.jpg
...
proteins/chicken/chicken_prot_025kcal.jpg
...
```

Output files, encoding both foods and both calories:

```
rice_025c_chicken_175p_total200.jpg
```

Manifest (CSV):

```csv
output,carb,carb_kcal,protein,protein_kcal,total_kcal
rice_chicken_200_175-25.jpg,rice,175,chicken,25,200
rice_chicken_200_150-50.jpg,rice,150,chicken,50,200
...
```

Generation rule: for each carb, each protein, each total S in {200, 225, …, 750}, each carb kcal c in {S, S−25, …, 0}, set protein kcal p = S − c. Source photos at 0 kcal are the empty plate, so a 0 kcal side is taken from the empty-plate reference.

## Other Options (for reference)

### Option A: Fixed-Mask Compositing (simplest)

Use one fixed left/right mask on two full photos, with a feathered seam. Good for a quick test. Weaker if food crosses the seam or the plate moves. Because foods are confined to halves, this may already be good enough, so it is worth trying first as a baseline.

### Option B: Plate Detection and Alignment, then Option A

Same as Option A plus an alignment step. This is part of the recommended approach anyway.

### Option C: Segmentation (recommended, see above)

Most flexible. Handles size changes, position drift, and cleaner colour control.

### Option D: Generative Editing (not recommended)

AI inpainting could smooth seams, but it can alter the food and defeat the purpose of documenting real portions.

## Practical Tips

- **Shoot for consistency.** Lock the camera, distance, focal length, white balance, and exposure.
- **Shoot the empty plate** in the same setup, at the same time as the others.
- **Match exposure** between carb and protein photos if they differ. A simple levels or histogram match helps.
- **Keep originals untouched.** Write outputs to a separate folder.
- **Save intermediates as PNG or TIFF.** Only the final outputs need to be JPEG.
- **Check the segmentation on a contact sheet** of all source photos before running the batch.

## Tooling Options

| Tool | Good for | Notes |
|---|---|---|
| Python + Pillow / OpenCV / NumPy | Alignment, masks, compositing, manifest | Best fit for 460 × pairs outputs. Scriptable. |
| `rembg` / SAM (Python) | Food masks | Run once per source photo. |
| ImageMagick (CLI) | Simple compositing | Good for Option A baseline. |
| Photoshop Actions + File > Automate > Batch | Manual or semi-manual work | Feasible for a pilot, slow for thousands of outputs. |

## Suggested Next Steps

1. **Confirm the assumptions** above (constant total, empty-plate photo, max size, same lighting).
2. **Send 2–3 sample photos** (one carb, one protein, plus the empty plate) so I can test alignment and segmentation.
3. **Pilot:** one carb × one protein at three totals (e.g., 200, 400, 600 kcal), with the full blend steps. Check the results by eye.
4. **Full batch** from the generated manifest, once the pilot looks right.

## Photo Storage Plan

- **Photos live outside the repo**, in the folder set by `BLENDED_FOODS_DIR` (`pixi.toml`). Sets are folders (e.g. `fries_261119`, `fusilli_261119`, `meatballs_261120`), so any carb set can be combined with any protein set.
- **Checksum manifest** (`photo_manifest.csv`, written by `scripts/photo_manifest.py`) records the SHA-256 of every photo. `pixi run photo-check` detects missing, changed or new photos. Re-write it only when the photo set is changed on purpose.
- **Generated outputs** (`out/`, `masks/`) are git-ignored and regenerated from the photos and scripts.
- **Later, once the photo set is stable:** consider Git LFS for `photos/`-equivalent data so the originals are versioned in the repo too. Not done during prototyping, because every photo change would add its full size to the LFS store.

## Known Limitations and Decisions

- **Top-down footprint may saturate.** Background-difference masks for fries at 400 and 775 kcal have almost the same area, so the photos may not show the extra food above about 400 kcal. Decision: leave as is. The slider experiment will show empirically whether the difference is perceptible. If not, retake photos (e.g., an angled shot) at a later stage.
- **Alignment.** Coarse plate-centre alignment, then ECC sub-pixel refinement accepted only if correlation ≥ 0.6 and correction ≤ 15 px (larger values indicate divergence, as seen on fu_900). Fixed the thin rim artefacts on fries at 25 kcal.
- **Composite logic.** Each source photo contains only its own food, so no half-plane cut is applied. Composite = empty plate, then carb pixels where the carb mask is set, then protein pixels where the protein mask is set. Overlaps go to protein.
- **Scripts.** `scripts/measure_plate.py` (plate centre), `scripts/food_masks.py` (difference masks, written to `masks/`).

## Open Questions

- [ ] Is the meal total constant along the slider? (Assumed yes.)
- [ ] Is there a 0 kcal (empty plate) photo per setup?
- [ ] Is the max meal size 750 kcal, or might it go higher?
- [ ] How many carbs and proteins are planned? (Sets the batch size: 460 images per pair.)
- [ ] Preferred output resolution and format?
- [ ] Is Python acceptable as the tool, or should everything stay in Photoshop?
