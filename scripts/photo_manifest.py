"""Write or check a checksum manifest for the photo folder.

The photos themselves live outside the repo (see PLANNING.md). This manifest
records the SHA-256 of every photo, so any set of generated outputs can be
traced back to the exact photos used, and a moved or edited photo is detected.

Usage (from the project root):
    pixi run python scripts/photo_manifest.py write [photo_dir]
    pixi run python scripts/photo_manifest.py check [photo_dir]

photo_dir defaults to the BLENDED_FOODS_DIR environment variable.
The manifest is photo_manifest.csv in the repo root.
"""

import csv
import hashlib
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST = os.path.join(REPO_ROOT, "photo_manifest.csv")


def photo_dir_from(args):
    if len(args) > 1:
        return args[1]
    env = os.environ.get("BLENDED_FOODS_DIR")
    if not env:
        raise SystemExit("Set BLENDED_FOODS_DIR or pass the photo folder as an argument.")
    return env


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(photo_dir):
    """Return {relative_path: (bytes, sha256)} for every JPG under photo_dir."""
    out = {}
    for root, _, files in os.walk(photo_dir):
        for name in files:
            if name.lower().endswith(".jpg"):
                full = os.path.join(root, name)
                rel = os.path.relpath(full, photo_dir).replace(os.sep, "/")
                out[rel] = (os.path.getsize(full), sha256(full))
    return out


def write(photo_dir):
    entries = scan(photo_dir)
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "bytes", "sha256"])
        for rel in sorted(entries):
            size, digest = entries[rel]
            w.writerow([rel, size, digest])
    print(f"Wrote {len(entries)} entries to {MANIFEST}")


def check(photo_dir):
    if not os.path.exists(MANIFEST):
        raise SystemExit(f"No manifest at {MANIFEST}. Run 'write' first.")
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        expected = {r["path"]: (int(r["bytes"]), r["sha256"]) for r in csv.DictReader(f)}
    actual = scan(photo_dir)
    missing = sorted(set(expected) - set(actual))
    new = sorted(set(actual) - set(expected))
    changed = sorted(p for p in set(expected) & set(actual) if expected[p] != actual[p])
    print(f"Manifest entries: {len(expected)}  found in folder: {len(actual)}")
    for label, items in (("MISSING", missing), ("CHANGED", changed), ("NEW", new)):
        for p in items:
            print(f"  {label}: {p}")
    if not (missing or changed or new):
        print("OK: folder matches the manifest.")
    return not (missing or changed or new)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("write", "check"):
        raise SystemExit(__doc__)
    folder = photo_dir_from(sys.argv[1:])
    if sys.argv[1] == "write":
        write(folder)
    else:
        sys.exit(0 if check(folder) else 1)
