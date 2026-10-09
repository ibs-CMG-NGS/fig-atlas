"""Image panels: loading, display adjustments, and their record (roadmap 6a.3).

Journals require that image adjustments be disclosed and, for linear changes,
applied to the whole image. This module turns source image files into the
RGB array a panel shows -- crop, a linear display range per channel, an
optional gamma, channel tinting -- and registers exactly what was done.
``fa build`` writes that into the figure's provenance record with each
source file's hash; publish lists it in the README; verify warns when a
nonlinear adjustment (gamma != 1) was used.

Formats: whatever Pillow reads (PNG, JPEG, 8/16-bit TIFF). A multi-channel
microscope image comes as one greyscale file per channel, tinted and summed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

PENDING: list[dict] = []


@dataclass
class Channel:
    path: str
    color: str = "white"                  # tint for a greyscale channel (matplotlib colour)
    display_range: list | None = None     # [min, max] in the image's own units; None -> percentiles
    label: str = ""


@dataclass
class Prepared:
    rgb: np.ndarray                       # H x W x 3 floats in [0, 1]
    record: dict = field(default_factory=dict)


def load(path) -> np.ndarray:
    """The image as an array in its own units (uint8, uint16 or float);
    greyscale as H x W, colour as H x W x 3 (alpha dropped)."""
    from PIL import Image
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA", "P", "CMYK", "YCbCr"):
            im = im.convert("RGB")
        arr = np.array(im)
    if arr.ndim == 3:
        arr = arr[..., :3]
    return arr


def _crop(arr: np.ndarray, crop) -> np.ndarray:
    if not crop:
        return arr
    x0, y0, x1, y1 = (int(v) for v in crop)
    h, w = arr.shape[:2]
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
        raise ValueError(f"crop {list(crop)} is outside the image ({w} x {h} px)")
    return arr[y0:y1, x0:x1]


def _display(arr: np.ndarray, display_range, percentiles) -> tuple[np.ndarray, list[float]]:
    """Linear map to [0, 1]: one (min, max) for the whole image (all colour
    planes alike), from ``display_range`` or the given percentiles."""
    a = arr.astype(float)
    if display_range is not None:
        lo, hi = (float(v) for v in display_range)
    else:
        lo, hi = (float(v) for v in np.percentile(a, list(percentiles)))
    if hi <= lo:
        hi = lo + 1.0
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0), [lo, hi]


def prepare(channels: list[Channel], crop=None, gamma: float = 1.0,
            percentiles=(0.0, 100.0)) -> Prepared:
    """Crop, scale and (for several greyscale channels) tint and sum."""
    from matplotlib.colors import to_rgb
    if not channels:
        raise ValueError("no image given")
    gamma = float(gamma)
    rgb = None
    rec_channels = []
    for ch in channels:
        raw = load(ch.path)
        shape, dtype = list(raw.shape), str(raw.dtype)
        img, used = _display(_crop(raw, crop), ch.display_range, percentiles)
        if gamma != 1.0:
            img = img ** gamma
        if img.ndim == 3:                          # a colour image: shown as is
            if len(channels) > 1:
                raise ValueError(f"{ch.path}: a colour image cannot be combined with other channels")
            layer = img
        else:
            layer = img[..., None] * np.array(to_rgb(ch.color))[None, None, :]
        rgb = layer if rgb is None else rgb + layer
        rec_channels.append({"path": str(ch.path), "shape": shape, "dtype": dtype, "color": ch.color,
                             "label": ch.label, "display_range": used,
                             "display_range_source": "given" if ch.display_range is not None
                             else f"percentiles {list(percentiles)}"})
    rgb = np.clip(rgb, 0.0, 1.0)
    return Prepared(rgb, {"channels": rec_channels, "crop": list(crop) if crop else None,
                          "gamma": gamma, "shown_px": [int(rgb.shape[1]), int(rgb.shape[0])]})


def record(entry: dict) -> dict:
    """Register what a panel did to its images, for the figure saved next."""
    PENDING.append(entry)
    return entry


def take() -> list[dict]:
    out = PENDING[:]
    PENDING.clear()
    return out


def with_hashes(entries: list[dict], rel, sha256) -> list[dict]:
    """Record entries with repository-relative paths and file hashes."""
    out = []
    for e in entries:
        e = {**e, "channels": [dict(c) for c in e["channels"]]}
        for c in e["channels"]:
            p = Path(c["path"]).resolve()
            c["path"] = rel(p)
            c["sha256"] = sha256(p) if p.is_file() else None
        e["nonlinear"] = e.get("gamma", 1.0) != 1.0
        out.append(e)
    return out


def readme_lines(entries: list[dict]) -> list[str]:
    """The README's "Images" section: source, crop, display range, gamma, scale."""
    if not entries:
        return []
    lines = ["## Images",
             "Source images and the adjustments applied to them (linear display range per channel, "
             "whole image; gamma when not 1)."]
    for e in entries:
        head = f"- Panel {e.get('panel') or '?'}"
        if e.get("crop"):
            head += f": crop x {e['crop'][0]}-{e['crop'][2]}, y {e['crop'][1]}-{e['crop'][3]} px"
        if e.get("pixel_size"):
            head += f"; pixel {e['pixel_size']:g} {e.get('pixel_unit', '')}".rstrip()
        if e.get("scale_bar"):
            head += f"; scale bar {e['scale_bar']:g} {e.get('pixel_unit', '')}".rstrip()
        if e.get("nonlinear"):
            head += f"; **gamma {e['gamma']:g} (nonlinear)**"
        lines.append(head)
        for c in e["channels"]:
            lo, hi = c["display_range"]
            lines.append(f"  - `{c['path']}` ({c['dtype']}, {c['shape'][1]} x {c['shape'][0]} px"
                         + (f", {c['label']}" if c["label"] else "") + f"): display {lo:g}-{hi:g}"
                         + (f", tint {c['color']}" if len(e['channels']) > 1 else "")
                         + (f", sha256 {c['sha256'][:12]}" if c.get("sha256") else ""))
    return lines
