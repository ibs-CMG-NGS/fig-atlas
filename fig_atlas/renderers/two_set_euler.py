"""Two-set Euler diagram (area-proportional Venn) inside a universe frame.

Shows how a population (the frame, e.g. all genes of a class) splits by two
independent criteria: the two circles' areas are proportional to their set
sizes and their overlap area to the intersection, so the four regions (A only,
B only, both, neither) read without imposing an order on the criteria -- unlike
a funnel. The frame itself is not area-scaled (a set can cover more of the
population than a circle can cover of a rectangle); the count outside both
circles is printed in the frame.
"""

from __future__ import annotations

import math

import numpy as np
from matplotlib.patches import Circle, Rectangle

from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("two_set_euler", params=[
    # [Sets and colours]
    Param("a_label", str, "A", role="Name of set A, printed above its circle with n"),
    Param("b_label", str, "B", role="Name of set B, printed above its circle with n"),
    Param("a_color", "color", "#93c5fd", unit="hex color", role="Fill of the A-only region"),
    Param("b_color", "color", "#fcd34d", unit="hex color", role="Fill of the B-only region"),
    Param("both_color", "color", "#2563eb", unit="hex color", role="Fill of the intersection"),
    Param("fill_alpha", float, 0.55, unit="[0-1] opacity", range=(0, 1), role="Opacity of the circle fills"),
    Param("edge_color", "color", "#334155", unit="hex color", role="Circle outline colour (and the outside count text)"),
    Param("edge_width", float, 0.6, unit="pt", range=(0, None), role="Circle outline width"),
    # [Frame: the box standing for all genes]
    Param("frame_color", "color", "#94a3b8", unit="hex color", role="Colour of the surrounding 'all genes' box"),
    Param("frame_width", float, 0.6, unit="pt", range=(0, None), role="Width of the surrounding box"),
    Param("frame_pad", float, 0.12, unit="x the larger radius", role="Gap between circles and the box sides"),
    Param("frame_top_room", float, 0.55, unit="x the larger radius", role="Room above the circles for the set labels",
          tune="raise if set labels touch the box"),
    Param("frame_bottom_room", float, 0.30, unit="x the larger radius", role="Room below the circles for the totals"),
    # [Text]
    Param("count_fontsize", float, 6.0, unit="pt", range=(0, None), role="Region count size"),
    Param("label_fontsize", float, 6.0, unit="pt", range=(0, None), role="Set label size"),
    Param("both_label", str, "linked", role="Word above the intersection count"),
    Param("both_note", str, None, role="Extra line in the intersection (e.g. 'core 41')"),
    Param("both_text_color", "color", "white", unit="color", role="Text colour inside the intersection"),
    Param("neither_label", str, "neither", role="Label of the genes outside both circles"),
    Param("total_label", str, "all genes", role="Label of the total"),
    # [Small regions: labels moved outside]
    Param("min_region_frac", float, 0.28, unit="x the larger radius", role="A region narrower than this gets its count outside"),
    Param("both_min_width_frac", float, 0.45, unit="x the larger radius",
          role="A lens narrower than this gets its label outside the circles"),
    Param("both_outside_offset", list, [0.35, 0.45], unit="[dx, dy] in radii", role="Position of the outside intersection label"),
    Param("both_outside_color", "color", "#1e3a8a", unit="hex color", role="Colour of the outside intersection label"),
    # [Title]
    Param("labels_title", str, None, role="Panel title (none = no title)"),
    Param("title_size", float, 8.0, unit="pt", role="Panel title font size"),
    Param("title_pad", float, 4, unit="pt", role="Gap between title and diagram"),
])


def _lens_area(r1: float, r2: float, d: float) -> float:
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = r1 ** 2 * math.acos((d ** 2 + r1 ** 2 - r2 ** 2) / (2 * d * r1))
    a2 = r2 ** 2 * math.acos((d ** 2 + r2 ** 2 - r1 ** 2) / (2 * d * r2))
    a3 = 0.5 * math.sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0.0))
    return a1 + a2 - a3


def _center_distance(r1: float, r2: float, overlap: float) -> float:
    """Distance between circle centres whose lens area equals ``overlap`` (bisection)."""
    lo, hi = abs(r1 - r2), r1 + r2
    if overlap <= 0:
        return hi
    if overlap >= math.pi * min(r1, r2) ** 2:
        return lo
    for _ in range(80):
        mid = (lo + hi) / 2
        if _lens_area(r1, r2, mid) > overlap:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@uses_schema(SCHEMA)
def render_two_set_euler(ax, n_total: int, n_a_only: int, n_b_only: int, n_both: int, params: dict):
    """Draw the diagram onto ``ax`` (axis off, equal aspect).

    params: a_label, b_label (set names, printed above their circle with n),
      a_color ('#93c5fd'), b_color ('#fcd34d'), both_color ('#2563eb'),
      fill_alpha (0.55), edge_color ('#334155'), edge_width (0.6),
      frame_color ('#94a3b8'), frame_width (0.6), frame_pad (0.12, of the larger
      radius), frame_top_room (0.55, room above the circles for set labels, in
      radii), count_fontsize (6.0), label_fontsize (6.0), both_text_color ('white'),
      both_label ('linked'), both_note (extra line in the intersection, e.g.
      'core 41'), neither_label ('neither'), total_label ('all genes'),
      min_region_frac (0.28: a region narrower than this share of the larger
      radius gets its count outside the circle with a leader line),
      both_min_width_frac (0.45: a lens narrower than this share of the larger
      radius gets its label outside, offset by both_outside_offset [dx, dy] in
      radii, colour both_outside_color),
      labels_title, title_size, title_pad
    """
    a_n, b_n = n_a_only + n_both, n_b_only + n_both
    ra, rb = math.sqrt(max(a_n, 1) / math.pi), math.sqrt(max(b_n, 1) / math.pi)
    d = _center_distance(ra, rb, float(n_both))
    xa, xb = 0.0, d
    y = 0.0
    rmax = max(ra, rb)

    fs = float(params.get("count_fontsize", 6.0))
    lfs = float(params.get("label_fontsize", 6.0))
    alpha = float(params.get("fill_alpha", 0.55))
    ec, ew = params.get("edge_color", "#334155"), float(params.get("edge_width", 0.6))

    # Frame = the population
    pad = float(params.get("frame_pad", 0.12)) * rmax
    x0, x1 = min(xa - ra, xb - rb) - pad, max(xa + ra, xb + rb) + pad
    y0 = -max(ra, rb) - pad - float(params.get("frame_bottom_room", 0.30)) * rmax
    y1 = max(ra, rb) + float(params.get("frame_top_room", 0.55)) * rmax
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False,
                           edgecolor=params.get("frame_color", "#94a3b8"),
                           linewidth=float(params.get("frame_width", 0.6))))

    # Circles, then the intersection re-filled with the emphasis colour
    ca = Circle((xa, y), ra, facecolor=params.get("a_color", "#93c5fd"), alpha=alpha, edgecolor="none")
    cb = Circle((xb, y), rb, facecolor=params.get("b_color", "#fcd34d"), alpha=alpha, edgecolor="none")
    ax.add_patch(ca)
    ax.add_patch(cb)
    lens = Circle((xb, y), rb, facecolor=params.get("both_color", "#2563eb"), edgecolor="none")
    ax.add_patch(lens)
    lens.set_clip_path(Circle((xa, y), ra, transform=ax.transData))
    for cx, r in ((xa, ra), (xb, rb)):
        ax.add_patch(Circle((cx, y), r, fill=False, edgecolor=ec, linewidth=ew))

    # Region label positions along the centre line
    a_left, a_right, b_left, b_right = xa - ra, xa + ra, xb - rb, xb + rb
    min_w = float(params.get("min_region_frac", 0.28)) * rmax

    def _put(xc, width, text, color="#111827", weight="normal", outside_dy=None):
        if width >= min_w or outside_dy is None:
            ax.text(xc, y, text, ha="center", va="center", fontsize=fs, color=color, fontweight=weight)
        else:
            ty = y + outside_dy
            ax.annotate(text, xy=(xc, y), xytext=(xc, ty), ha="center", va="center", fontsize=fs,
                        color="#111827", fontweight=weight,
                        arrowprops=dict(arrowstyle="-", color=ec, lw=ew * 0.8, shrinkA=1, shrinkB=0))

    # A only (left crescent), B only (right crescent), both (lens)
    _put((a_left + min(b_left, a_right)) / 2, min(b_left, a_right) - a_left, f"{n_a_only:,}",
         outside_dy=-(rmax + 0.18 * rmax))
    _put((max(a_right, b_left) + b_right) / 2, b_right - max(a_right, b_left), f"{n_b_only:,}",
         outside_dy=-(rmax + 0.18 * rmax))
    both_txt = f"{params.get('both_label', 'linked')}\n{n_both:,}"
    if params.get("both_note"):
        both_txt += f"\n{params['both_note']}"
    lens_l, lens_r = max(a_left, b_left), min(a_right, b_right)
    lens_x = (lens_l + lens_r) / 2
    if lens_r - lens_l >= float(params.get("both_min_width_frac", 0.45)) * rmax:
        ax.text(lens_x, y, both_txt, ha="center", va="center", fontsize=fs,
                color=params.get("both_text_color", "white"), fontweight="bold", linespacing=1.15)
    else:
        # Lens too narrow for its text: label beside it with a leader line
        dx, dy = (float(v) * rmax for v in params.get("both_outside_offset", [0.35, 0.45]))
        ax.annotate(both_txt, xy=(lens_x, y), xytext=(lens_x + dx, y + dy), ha="left", va="center",
                    fontsize=fs, color=params.get("both_outside_color", "#1e3a8a"), fontweight="bold",
                    linespacing=1.15,
                    arrowprops=dict(arrowstyle="-", color=ec, lw=ew * 0.8, shrinkA=1, shrinkB=0))

    # Set labels above the circles, 'neither' and total inside the frame
    lab_y = max(ra, rb) + 0.12 * rmax
    ax.text(a_left, lab_y, f"{params.get('a_label', 'A')}\n(n = {a_n:,})", ha="left", va="bottom",
            fontsize=lfs, color=ec, linespacing=1.1)
    ax.text(b_right, lab_y, f"{params.get('b_label', 'B')}\n(n = {b_n:,})", ha="right", va="bottom",
            fontsize=lfs, color=ec, linespacing=1.1)
    n_neither = n_total - n_a_only - n_b_only - n_both
    ax.text(x0 + 0.04 * rmax, y0 + 0.06 * rmax,
            f"{params.get('neither_label', 'neither')}: {n_neither:,}", ha="left", va="bottom", fontsize=fs, color=ec)
    ax.text(x1 - 0.04 * rmax, y0 + 0.06 * rmax,
            f"{params.get('total_label', 'all genes')}: {n_total:,}", ha="right", va="bottom", fontsize=fs, color=ec)

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    if params.get("labels_title"):
        ax.set_title(params["labels_title"], fontsize=float(params.get("title_size", 8.0)), fontweight="bold",
                     pad=float(params.get("title_pad", 4)))
    return {"a": a_n, "b": b_n, "both": n_both, "neither": n_neither}
