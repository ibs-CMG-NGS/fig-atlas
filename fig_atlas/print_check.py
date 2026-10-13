"""Print-size compliance check for a rendered matplotlib figure.

Answers: "if this figure is placed on the given page, what point sizes do its
text and lines actually print at, and do they clear the minimums?"

Only artists that are really drawn are counted (a draw pass is recorded),
so hidden tick labels, ``axis('off')`` axes, empty strings etc. never show up
as false positives. The figure's printed size is its tight bounding box (what
``savefig(bbox_inches="tight")`` produces), scaled down to the page content
width if wider -- a figure narrower than the page prints at native size.

Height is reported separately rather than folded into the scale: a figure
taller than the page can be split across pages at full width, so the font
verdict uses the width-fit scale, and ``pages_needed`` says whether a split
(or a redesign) is required.
"""
from __future__ import annotations

import math
from contextlib import contextmanager

from .page import PageSpec

_LINESTYLE_NONE = {"None", "none", "", " "}


def _visible(artist) -> bool:
    try:
        return bool(artist.get_visible())
    except Exception:
        return False


def _text_size(t) -> tuple[float, str] | None:
    s = t.get_text()
    if not _visible(t) or not s or not s.strip():
        return None
    return float(t.get_fontsize()), s


def _line2d_width(ln) -> tuple[float, str] | None:
    if not _visible(ln):
        return None
    if ln.get_linestyle() in _LINESTYLE_NONE:
        # Marker-only lines, e.g. tick marks: the stroke is the marker edge.
        if ln.get_marker() in (None, "None", "none", ""):
            return None
        w = float(ln.get_markeredgewidth())
        return (w, "marker/tick") if w > 0 else None
    w = float(ln.get_linewidth())
    return (w, "line") if w > 0 and len(ln.get_xdata()) >= 2 else None


def _patch_width(p) -> tuple[float, str] | None:
    if not _visible(p):
        return None
    w = float(p.get_linewidth() or 0.0)
    ec = p.get_edgecolor()
    if w <= 0 or ec is None or len(ec) < 4 or ec[3] <= 0:
        return None
    return w, type(p).__name__


def _collection_width(c) -> tuple[float, str] | None:
    if not _visible(c):
        return None
    if not c.get_paths():
        return None          # draws nothing (e.g. a colorbar's empty divider lines)
    ecs = c.get_edgecolor()
    if ecs is None or len(ecs) == 0 or float(max(e[3] for e in ecs)) <= 0:
        return None
    ws = [float(w) for w in c.get_linewidths() if w and w > 0]
    return (min(ws), type(c).__name__) if ws else None


@contextmanager
def _record_draws():
    from matplotlib.collections import Collection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.text import Text

    texts: dict[int, tuple[float, str]] = {}
    lines: dict[int, tuple[float, str]] = {}
    hooks = [(Text, texts, _text_size), (Line2D, lines, _line2d_width),
             (Patch, lines, _patch_width), (Collection, lines, _collection_width)]
    originals = {}
    for cls, sink, extract in hooks:
        orig = cls.draw
        originals[cls] = orig

        def draw(self, renderer, *args, _orig=orig, _sink=sink, _extract=extract, **kwargs):
            try:
                rec = _extract(self)
                if rec is not None:
                    _sink[id(self)] = rec
            except Exception:
                pass
            return _orig(self, renderer, *args, **kwargs)

        cls.draw = draw
    try:
        yield texts, lines
    finally:
        for cls, orig in originals.items():
            cls.draw = orig


def audit_figure(
    fig,
    page: PageSpec,
    min_font_pt: float = 5.0,
    min_line_pt: float = 0.25,
    max_offenders: int = 8,
) -> dict:
    """How ``fig`` prints on ``page``: drawn, shrunk to the page width if wider,
    and measured. Returns a dict with ``scale_to_page_width``,
    ``pages_needed``, the smallest printed text and line (``min_font_printed_pt``,
    ``min_line_printed_pt``), the texts below ``min_font_pt``
    (``smallest_texts``) and the verdicts ``font_ok``, ``line_ok`` and
    ``fits_one_page``. `fa audit-print` and preflight run it on every figure."""
    with _record_draws() as (texts, lines):
        fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = fig.get_tightbbox(renderer)
    w_in, h_in = float(bbox.width), float(bbox.height)

    scale = min(1.0, page.content_width_in / w_in) if w_in > 0 else 1.0
    printed_h_in = h_in * scale
    pages_needed = max(1, math.ceil(printed_h_in / page.content_height_in - 1e-9))

    font_sizes = [sz for sz, _ in texts.values()]
    line_widths = [w for w, _ in lines.values()]
    small_texts = sorted(
        {(round(sz * scale, 2), round(sz, 2), s.replace("\n", " ")[:40])
         for sz, s in texts.values() if sz * scale < min_font_pt}
    )
    thin_kinds: dict[str, int] = {}
    for w, kind in lines.values():
        if w * scale < min_line_pt:
            thin_kinds[kind] = thin_kinds.get(kind, 0) + 1

    return {
        "page": page.name,
        "fig_width_mm": round(w_in * 25.4, 1),
        "fig_height_mm": round(h_in * 25.4, 1),
        "scale_to_page_width": round(scale, 3),
        "printed_height_mm": round(printed_h_in * 25.4, 1),
        "pages_needed": pages_needed,
        "n_texts": len(font_sizes),
        "min_font_native_pt": round(min(font_sizes), 2) if font_sizes else None,
        "min_font_printed_pt": round(min(font_sizes) * scale, 2) if font_sizes else None,
        "max_font_printed_pt": round(max(font_sizes) * scale, 2) if font_sizes else None,
        "n_texts_below_min": sum(1 for sz in font_sizes if sz * scale < min_font_pt),
        "n_lines": len(line_widths),
        "min_line_printed_pt": round(min(line_widths) * scale, 3) if line_widths else None,
        "n_lines_below_min": sum(thin_kinds.values()),
        "thin_line_kinds": thin_kinds,
        "smallest_texts": [
            {"printed_pt": p, "native_pt": n, "text": s} for p, n, s in small_texts[:max_offenders]
        ],
        "min_font_pt": min_font_pt,
        "min_line_pt": min_line_pt,
        "font_ok": all(sz * scale >= min_font_pt for sz in font_sizes),
        "line_ok": not thin_kinds,
        "fits_one_page": pages_needed == 1,
    }
