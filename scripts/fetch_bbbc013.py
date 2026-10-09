"""Download the public BBBC013 image set for the imaging pilot (roadmap 6a.4).

BBBC013v1 -- human U2OS cells, cytoplasm-to-nucleus translocation of a
FKHR-EGFP fusion (channel 1) with a DRAQ5 DNA counterstain (channel 2),
96-well plate: 9-point dose curves of Wortmannin and LY294002, negative
(no drug) and positive (150 nM Wortmannin) controls, 4 replicates. 640 x 640
8-bit BMP. Acquired on an IN Cell Analyzer 3000; the pixel size is not
published.

License: "The BBBC013 images are licensed under a Creative Commons
Attribution 3.0 Unported License by Ilya Ravkin."
Citation: "We used image set BBBC013v1 provided by Ilya Ravkin, available
from the Broad Bioimage Benchmark Collection [Ljosa et al., Nature Methods,
2012]."  https://bbbc.broadinstitute.org/BBBC013

The files go to raw_data/pilot-imaging/bbbc013/ (git-ignored), checked
against the SHA-256 pinned below; raw data is never edited afterwards.

Usage:
    python scripts/fetch_bbbc013.py            # download (skips files already present and correct)
    python scripts/fetch_bbbc013.py --check    # only verify what is there
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "raw_data" / "pilot-imaging" / "bbbc013"
BASE = "https://data.broadinstitute.org/bbbc/BBBC013/"
# file -> sha256 (pinned at the first download, 2026-10-08)
FILES = {
    "BBBC013_v1_images_bmp.zip": "c059b569d96f70ad5626fad144867e6ece4353622119c46a8af8f9794f1e7985",
    "BBBC013_v1_platemap_all.txt": "e8db6666271d47962fa7d2abfa3ea965352b8e87bee461f2983d0f667bc7ff08",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify the files without downloading")
    args = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, want in FILES.items():
        p = DEST / name
        if not p.is_file() and not args.check:
            print(f"downloading {name} ...")
            urllib.request.urlretrieve(BASE + name, p)
        if not p.is_file():
            print(f"MISSING  {name}")
            bad += 1
            continue
        got = sha256(p)
        if want is None:
            print(f"UNPINNED {name}  sha256 {got}")
        elif got != want:
            print(f"MISMATCH {name}  sha256 {got} (expected {want})")
            bad += 1
        else:
            print(f"OK       {name}")
    z = DEST / "BBBC013_v1_images_bmp.zip"
    images = DEST / "images"
    if z.is_file() and not images.is_dir() and not args.check:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(images)
        print(f"extracted {sum(1 for _ in images.rglob('*.BMP'))} images to {images.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
