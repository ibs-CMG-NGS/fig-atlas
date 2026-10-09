"""Structural snapshots of rendered figures (roadmap Phase 0).

Pixel comparison is unreliable across platforms: conda (Windows) and pip
(Linux CI) matplotlib builds ship different FreeType versions, so glyph
pixels differ even when nothing changed. Instead, a snapshot records every
artist actually drawn -- text, font size/weight, colors, line widths,
positions in points, marker/image data summaries -- in draw order. Comparing
two snapshots then names exactly what changed ("Text 'Fold change' size 6.0
-> 6.5") and tolerates the sub-point layout jitter of different font
rasterizers.
"""
from __future__ import annotations

import hashlib
import json
import math
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from matplotlib.collections import Collection
from matplotlib.colors import to_hex
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text

POS_TOL_PT = 0.75   # layout jitter allowed between font rasterizers (points)
NUM_REL_TOL = 1e-6


def _hex(c) -> str | None:
    try:
        return to_hex(c, keep_alpha=True)
    except (ValueError, TypeError):
        return None


def _colors(arr) -> list[str]:
    arr = np.asarray(arr)
    if arr.size == 0:
        return []
    arr = arr.reshape(-1, arr.shape[-1]) if arr.ndim > 1 else arr.reshape(1, -1)
    return sorted({to_hex(row, keep_alpha=True) for row in arr})[:16]


def _digest(a) -> str:
    a = np.round(np.ma.filled(np.asarray(a, dtype=float), np.nan), 6)
    return hashlib.sha256(a.tobytes()).hexdigest()[:16]


def _extent_pt(artist, renderer, dpi) -> list[float] | None:
    try:
        bb = artist.get_window_extent(renderer)
    except Exception:
        return None
    vals = [bb.x0, bb.y0, bb.x1, bb.y1]
    if not all(math.isfinite(v) for v in vals):
        return None
    return [round(v * 72.0 / dpi, 2) for v in vals]


def _record(artist, renderer, dpi) -> dict | None:
    if not artist.get_visible():
        return None
    if isinstance(artist, Text):
        s = artist.get_text()
        if not s or not s.strip():
            return None
        return {"kind": "Text", "text": s, "size": float(artist.get_fontsize()),
                "weight": str(artist.get_fontweight()), "style": artist.get_fontstyle(),
                "rotation": round(float(artist.get_rotation()), 2), "color": _hex(artist.get_color()),
                "ha": artist.get_horizontalalignment(), "va": artist.get_verticalalignment(),
                "bbox_pt": _extent_pt(artist, renderer, dpi)}
    if isinstance(artist, Line2D):
        # Record only what is actually painted: the line color when a line is
        # drawn, the marker edge color, and the marker face color only for
        # filled markers. (An errorbar cap '_' paints with its edge color; its
        # unused .color changed default between matplotlib 3.9 and 3.10.)
        xy = np.asarray(artist.get_xydata(), dtype=float)
        ls = str(artist.get_linestyle())
        marker = artist.get_marker()
        has_marker = marker not in (None, "None", "none", "", " ")
        filled = has_marker and artist._marker.is_filled()
        return {"kind": "Line2D", "n": int(len(xy)), "data": _digest(xy),
                "color": _hex(artist.get_color()) if ls not in ("None", "none", "", " ") else None,
                "lw": float(artist.get_linewidth()), "ls": ls, "marker": str(marker),
                "ms": float(artist.get_markersize()),
                "mec": _hex(artist.get_markeredgecolor()) if has_marker else None,
                "mfc": _hex(artist.get_markerfacecolor()) if filled else None}
    if isinstance(artist, Patch):
        return {"kind": type(artist).__name__, "fc": _hex(artist.get_facecolor()),
                "ec": _hex(artist.get_edgecolor()), "lw": float(artist.get_linewidth() or 0.0),
                "bbox_pt": _extent_pt(artist, renderer, dpi)}
    if isinstance(artist, Collection):
        offsets = np.asarray(artist.get_offsets(), dtype=float)
        return {"kind": type(artist).__name__, "n": int(len(offsets)),
                "offsets": _digest(offsets) if len(offsets) else None,
                "paths": len(artist.get_paths()),
                "fc": _colors(artist.get_facecolor()), "ec": _colors(artist.get_edgecolor()),
                "lw": sorted({round(float(w), 4) for w in np.atleast_1d(artist.get_linewidths())})[:8],
                "sizes": sorted({round(float(s), 4) for s in np.atleast_1d(artist.get_sizes())})[:8]
                if hasattr(artist, "get_sizes") else []}
    if isinstance(artist, AxesImage):
        arr = artist.get_array()
        cmap = artist.get_cmap()
        return {"kind": "AxesImage", "shape": list(np.shape(arr)), "data": _digest(arr),
                "cmap": getattr(cmap, "name", None),
                "clim": [None if v is None else round(float(v), 6) for v in artist.get_clim()],
                "bbox_pt": _extent_pt(artist, renderer, dpi)}
    return None


@contextmanager
def _hooked():
    records: list = []
    classes = [Text, Line2D, Patch, Collection, AxesImage]
    originals = {cls: cls.draw for cls in classes}

    def make(orig):
        def draw(self, renderer, *args, **kwargs):
            out = orig(self, renderer, *args, **kwargs)
            try:
                # Window extents are in renderer pixels, so convert with the
                # renderer's dpi (some artists, e.g. a text's bbox patch,
                # have no .figure of their own).
                rec = _record(self, renderer, renderer.dpi)
            except Exception as exc:  # record, never break the draw
                rec = {"kind": type(self).__name__, "error": repr(exc)}
            if rec is not None:
                records.append(rec)
            return out
        return draw

    for cls, orig in originals.items():
        cls.draw = make(orig)
    try:
        yield records
    finally:
        for cls, orig in originals.items():
            cls.draw = orig


def _freetype_version() -> str:
    from matplotlib import ft2font
    return str(getattr(ft2font, "__freetype_version__", "unknown"))


def figure_snapshot(fig) -> dict:
    """Draw ``fig`` once and return its structural snapshot."""
    with _hooked() as records:
        fig.canvas.draw()
    w, h = fig.get_size_inches()
    return {"freetype": _freetype_version(),
            "figsize_in": [round(float(w), 4), round(float(h), 4)], "artists": records}


def _diff(a, b, path: str, out: list[str], skip_bbox: bool = False) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if skip_bbox and k == "bbox_pt":
                continue
            if k not in a or k not in b:
                out.append(f"{path}.{k}: {'missing' if k not in b else 'new'}")
            else:
                _diff(a[k], b[k], f"{path}.{k}", out, skip_bbox)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} -> {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            _diff(x, y, f"{path}[{i}]", out, skip_bbox)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        tol = POS_TOL_PT if "bbox_pt" in path else NUM_REL_TOL * max(1.0, abs(a))
        if abs(a - b) > tol:
            out.append(f"{path}: {a} -> {b}")
    elif a != b:
        out.append(f"{path}: {a!r} -> {b!r}")


def _label(snap: dict, path: str) -> str:
    """Prefix a diff path with the artist it belongs to, e.g. Text 'Fold change'."""
    if path.startswith(".artists["):
        i = int(path[len(".artists["):].split("]")[0])
        arts = snap["artists"]
        if i < len(arts):
            a = arts[i]
            return f"{a['kind']}{' ' + repr(a['text'][:30]) if 'text' in a else ''} "
    return ""


def compare(expected: dict, actual: dict, limit: int = 15) -> list[str]:
    """Differences between two snapshots, as readable lines.

    Positions (``bbox_pt``) are compared only when both snapshots were made
    with the same FreeType version: different versions place glyphs a little
    differently (conda on Windows vs pip wheels on Linux CI), which says
    nothing about the renderer. Text, sizes, colors and data always compare.
    """
    raw: list[str] = []
    same_ft = expected.get("freetype") == actual.get("freetype")
    exp = {k: v for k, v in expected.items() if k != "freetype"}
    act = {k: v for k, v in actual.items() if k != "freetype"}
    _diff(exp, act, "", raw, skip_bbox=not same_ft)
    return [f"{_label(expected, d)}{d}" for d in raw[:limit]] + (
        [f"... and {len(raw) - limit} more"] if len(raw) > limit else [])


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, snap: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
