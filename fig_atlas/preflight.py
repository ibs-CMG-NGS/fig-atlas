"""Pre-publication checks on a rendered matplotlib figure (roadmap Phase 3).

``preflight(fig, ...)`` draws the figure once, records every text and axes
actually drawn, and returns a list of ``Finding``s. Implemented checks
(the design notes, check families C2-C8):

C2 text overlap
    tick_label_collision      two tick labels of the same axis overlap          error
    cross_panel_text_overlap  texts of two different panels overlap            error
    text_overlap              any other pair of texts overlaps                 warn
    Rotated texts are compared as rotated rectangles (separating-axis test),
    not as their axis-aligned bounding boxes, and each text box is shrunk
    vertically by ``text_ink_shrink`` because a text extent includes the full
    line height, not just the ink.

C3 clipping and intrusion
    clipped_by_saved_area     a drawn text/axes extends past the saved area    error
    legend_overlaps_panel     a legend covers another panel's plot area        error
    legend_covers_data        a legend lies on its own panel's data (bars,
                              points or lines under it)                        warn
    panel_overlap             two panels' plot areas overlap                   error
    panel_intrusion           a text of one panel lies on another panel's
                              plot area (e.g. tick labels or an axis title
                              running into the neighbour)                      error
    Outer boxes may overlap harmlessly (a wide title above a neighbour's
    whitespace), so they are not compared directly.

C5 fonts (on the saved files / while rendering)
    pdf_type3_font            a PDF embeds a Type 3 font                       error
    pdf_font_not_embedded     a PDF font is referenced but not embedded        error
    pdf_font_not_allowed      a PDF font outside ``allowed_fonts`` (if set)    warn
    font_fallback             a requested font family was not found and
                              matplotlib substituted another one               error
    missing_glyph             a character the font cannot draw                 warn

C6 resolution
    png_dpi_low               a PNG's pixels per printed inch < ``min_dpi``    error
    raster_dpi_low            rasterized artists / images inside a vector
                              file saved at < ``min_raster_dpi``               error

C7/C8 layout rules and consistency
    tick_labels_touching      neighbouring tick labels < ``min_tick_gap_mm``
                              apart (they read as one label)                   warn
    panel_tag_misaligned      tags stacked in one column don't share a plumb
                              line (AGENTS.md rule 1.5)                          warn
    panel_tag_inconsistent    tags differ in size / weight / case              warn
    panel_tag_style           tag case or size differs from the journal preset warn
    font_size_outlier         a few texts of one role (tick labels, axis
                              titles, tags, legend) in an odd size -- usually
                              a hardcoded fontsize                             warn

C4 colour
    cvd_indistinct            two colours a reader must tell apart (legend
                              entries, categorical scatter groups) fall
                              below ``min_cvd_delta_e`` under simulated
                              colour-vision deficiency                         warn
    cmap_rainbow              jet / rainbow-like colormap                      warn
    cmap_red_green            red-green diverging colormap (RdYlGn, ...)       warn
    cmap_nonuniform           colormap whose lightness goes up and down        warn
    low_text_contrast         text vs. what is drawn behind it below
                              ``min_text_contrast`` (WCAG ratio)               warn
    CVD is simulated with Machado et al. (2009) matrices at full severity on
    linear RGB; colour difference is CIELAB delta-E (1976).

A "panel" groups an axes with its colorbars, insets and twin axes, so
overlaps between those are never reported. All geometry is reported in mm
on the figure canvas (origin bottom-left).

Allowed defects
    A figure that shows a defect on purpose (a teaching figure, a "before"
    panel) marks the axes with ``ax.set_gid("fa-allow:<name>")`` and the
    config gives the reason: ``preflight: {allow: {<name>: "<reason>"}}``.
    Findings whose box centre lies in such an axes' outer box are reported
    as info, with the reason. A gid with no reason in the config allows
    nothing and is itself reported:
    allow_without_reason      ``fa-allow:<name>`` with no reason in config     warn
"""
from __future__ import annotations

import itertools
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

import numpy as np
from matplotlib.colors import to_hex, to_rgba

MM_PER_INCH = 25.4
PANEL_TAG_GID = "panel-tag"   # set by fig_atlas.renderers.panels on every panel tag

DEFAULTS = {
    "min_overlap_mm2": 0.10,     # ignore text overlaps smaller than this area
    "min_overlap_frac": 0.05,    # ...or smaller than this fraction of the smaller text
    "text_ink_shrink": 0.12,     # trim this fraction of a text box's height off top and bottom
    "canvas_tol_mm": 0.2,        # how far past the saved area counts as clipped
    "legend_overlap_frac": 0.02, # legend area share overlapping another panel's plot area
    "legend_data_frac": 0.03,    # legend area share covering its own panel's bars or filled areas
    "legend_data_points": 1,     # scatter points (or line samples, 1 mm apart) under a legend before it is reported
    "panel_overlap_mm2": 0.5,    # plot-area overlap between two panels
    "min_dpi": 300,              # PNG pixels per printed inch
    "min_raster_dpi": 300,       # dpi of rasterized content inside PDF/SVG
    "allowed_fonts": [],         # PDF font names a journal accepts; empty = any
    "min_cvd_delta_e": 10.0,     # CIELAB delta-E between colours a reader must tell apart
    "cvd_types": ["deuteranomaly", "protanomaly", "tritanomaly"],
    "min_text_contrast": 3.0,    # WCAG contrast ratio of text against what is behind it
    "muted_text_min_contrast": 2.0,  # grey-on-white text at or above this is deliberate de-emphasis (info)
    "min_tick_gap_mm": 0.3,      # neighbouring tick labels closer than this read as one word
    "panel_tag_align_tol_mm": 0.3,   # tags in one column must share x within this
    "panel_tag_column_mm": 6.0,  # tags whose left edges are this close form a column
    "panel_tag_case": None,      # "lower" | "upper" (journal presets set it)
    "panel_tag_size_pt": None,   # required tag size (journal presets set it)
    "font_size_outlier_frac": 0.25,  # a role's sizes differing from its mode in at most this share
    "muted_max_chroma": 16.0,    # CIELAB chroma up to which a text colour counts as grey (slate greys 7-15, pastels 30+)
    "allow": {},                 # name -> reason: defects shown on purpose in axes with gid "fa-allow:<name>"
}
ALLOW_GID = "fa-allow:"


@dataclass
class Finding:
    check: str
    severity: str                    # "error" | "warn" | "info"
    message: str
    bbox_mm: list[float]             # [x0, y0, x1, y1] on the canvas
    panel: str = ""
    measured: float | None = None
    threshold: float | None = None
    hint: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _Text:
    text: str
    axes: object                     # matplotlib Axes or None (figure-level text)
    corners_mm: list[tuple[float, float]]  # rotated rectangle, counter-clockwise
    bbox_mm: list[float]             # axis-aligned extent
    tick_axis: str | None = None     # "x"/"y" + id when the text is a tick label
    is_legend: bool = False
    obj_id: int = 0
    color: tuple = (0.0, 0.0, 0.0, 1.0)   # RGBA
    fontsize: float = 0.0
    weight: str = "normal"
    gid: str | None = None
    role: str = "other"      # tick | axis_label | title | panel_tag | legend | colorbar_tick | colorbar_label | other


@dataclass
class _Record:
    texts: list[_Text] = field(default_factory=list)
    legends: list[tuple[object, list[float]]] = field(default_factory=list)   # (axes, bbox_mm)
    errors: list[str] = field(default_factory=list)   # artists the recorder failed on


# ---------------------------------------------------------------- geometry --
def _bbox_mm(bb, dpi: float) -> list[float]:
    k = MM_PER_INCH / dpi
    return [bb.x0 * k, bb.y0 * k, bb.x1 * k, bb.y1 * k]


def _rect_corners(cx, cy, w, h, angle_deg):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def _clip(subject, clipper):
    """Sutherland-Hodgman: intersection polygon of two convex CCW polygons."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def cross(p1, p2, a, b):
        x1, y1, x2, y2 = *p1, *p2
        x3, y3, x4, y4 = *a, *b
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0:
            return p2
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    out = list(subject)
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break
        s = inp[-1]
        for e in inp:
            if inside(e, a, b):
                if not inside(s, a, b):
                    out.append(cross(s, e, a, b))
                out.append(e)
            elif inside(s, a, b):
                out.append(cross(s, e, a, b))
            s = e
    return out


def _area(poly) -> float:
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) / 2 if len(poly) >= 3 else 0.0


def _box_area(b) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _box_overlap(a, b) -> list[float] | None:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return [x0, y0, x1, y1] if x1 > x0 and y1 > y0 else None


# ------------------------------------------------------------------ panels --
def panel_of(ax, fig) -> object:
    """The axes a figure element belongs to as a *panel*: a colorbar maps to
    the axes of its mappable, an inset to its parent, a twin to the first
    axes at the same position."""
    if ax is None:
        return None
    cb = getattr(ax, "_colorbar", None)
    if cb is not None and getattr(cb, "mappable", None) is not None and getattr(cb.mappable, "axes", None):
        return panel_of(cb.mappable.axes, fig)
    for parent in fig.get_axes():
        if ax in getattr(parent, "child_axes", []):
            return panel_of(parent, fig)
    # Where the axes sits on the whole canvas (display units): get_position()
    # is relative to the axes' own subfigure, so panels in different
    # subfigures (bundle_figure.draw_plots) would all look like twins.
    pos = tuple(round(v, 2) for v in ax.bbox.bounds)
    for other in fig.get_axes():
        if other is ax:
            break
        if tuple(round(v, 2) for v in other.bbox.bounds) == pos and not hasattr(other, "_colorbar"):
            return other
    return ax


def _panel_label(ax, fig) -> str:
    if ax is None:
        return "figure"
    i = next((n for n, a in enumerate(fig.get_axes()) if a is ax), None)
    title = ax.get_title() or ax.get_ylabel() or ax.get_xlabel()
    return f"axes[{i}]" + (f" '{title[:30]}'" if title else "")


# ---------------------------------------------------------------- recording --
@contextmanager
def _hook_texts(fig, rec: _Record, dpi_holder: dict):
    from matplotlib.legend import Legend
    from matplotlib.text import Text

    orig_text, orig_leg = Text.draw, Legend.draw

    def text_draw(self, renderer, *a, **k):
        out = orig_text(self, renderer, *a, **k)
        try:
            s = self.get_text()
            if self.get_visible() and s and s.strip():
                dpi = renderer.dpi
                bb = self.get_window_extent(renderer)
                rot = self.get_rotation() % 180
                w, h = bb.width, bb.height
                if rot not in (0.0, 90.0):
                    # Unrotated size from a clone; the rotated box shares the
                    # AABB's center, so (center, w, h, angle) gives its corners.
                    clone = Text(0, 0, s, fontproperties=self.get_fontproperties(),
                                 linespacing=getattr(self, "_linespacing", 1.2))
                    clone.set_figure(self.get_figure() if hasattr(self, "get_figure") else self.figure)
                    ub = clone.get_window_extent(renderer)
                    w, h = ub.width, ub.height
                elif rot == 90.0:
                    w, h = bb.height, bb.width
                k_ = MM_PER_INCH / dpi
                cx, cy = (bb.x0 + bb.x1) / 2 * k_, (bb.y0 + bb.y1) / 2 * k_
                rec.texts.append(_Text(
                    text=s, axes=getattr(self, "axes", None),
                    corners_mm=_rect_corners(cx, cy, w * k_, h * k_ * (1 - 2 * dpi_holder["shrink"]), rot),
                    bbox_mm=_bbox_mm(bb, dpi), obj_id=id(self),
                    color=tuple(to_rgba(self.get_color(), self.get_alpha())),
                    fontsize=float(self.get_fontsize()), weight=str(self.get_fontweight()),
                    gid=self.get_gid(),
                    is_legend=isinstance(getattr(self, "_fa_parent_legend", None), Legend)))
        except Exception as exc:   # never break the draw, but don't hide it either
            rec.errors.append(f"{type(self).__name__} {self.get_text()[:30]!r}: {exc!r}")
        return out

    def legend_draw(self, renderer, *a, **k):
        for t in self.get_texts():
            t._fa_parent_legend = self
        out = orig_leg(self, renderer, *a, **k)
        try:
            if self.get_visible():
                rec.legends.append((self.axes, _bbox_mm(self.get_window_extent(renderer), renderer.dpi)))
        except Exception as exc:
            rec.errors.append(f"Legend: {exc!r}")
        return out

    Text.draw, Legend.draw = text_draw, legend_draw
    try:
        yield
    finally:
        Text.draw, Legend.draw = orig_text, orig_leg
    # Tick label objects can be (re)created during the draw, so map them only
    # now. Tick labels, axis titles and offset texts don't carry .axes, so
    # their owning axes comes from this map too.
    tick_of: dict[int, str] = {}
    owner: dict[int, object] = {}
    role: dict[int, str] = {}
    for ax in fig.get_axes() + [c for a in fig.get_axes() for c in getattr(a, "child_axes", [])]:
        for title in (ax.title, getattr(ax, "_left_title", None), getattr(ax, "_right_title", None)):
            if title is not None:
                role[id(title)] = "title"
        # A colorbar's label and ticks are their own roles: they are often
        # deliberately smaller than the plot's axis titles and tick labels.
        cbar = "colorbar_" if hasattr(ax, "_colorbar") else ""
        for name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            owner[id(axis.label)] = ax
            role[id(axis.label)] = "colorbar_label" if cbar else "axis_label"
            owner[id(axis.offsetText)] = ax
            role[id(axis.offsetText)] = cbar + "tick"
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                for lab in (tick.label1, tick.label2):
                    tick_of[id(lab)] = f"{name}{id(ax)}"
                    owner[id(lab)] = ax
                    role[id(lab)] = cbar + "tick"
    # A text drawn more than once (e.g. a layout pass) keeps its last record.
    rec.texts = list({t.obj_id: t for t in rec.texts}.values())
    for t in rec.texts:
        t.tick_axis = tick_of.get(t.obj_id)
        if t.axes is None:
            t.axes = owner.get(t.obj_id)
        if t.gid == PANEL_TAG_GID or (t.axes is None and len(t.text.strip()) == 1
                                      and t.text.strip().isalpha() and str(t.weight) in ("bold", "700", "heavy")):
            t.role = "panel_tag"      # tagged by place_panel_tags, or a lone bold figure-level letter
        elif t.is_legend:
            t.role = "legend"
        else:
            t.role = role.get(t.obj_id, "other")


# ------------------------------------------------------------------- checks --
def _check_text_overlap(fig, texts: list[_Text], p: dict) -> list[Finding]:
    out = []
    items = sorted(texts, key=lambda t: t.bbox_mm[0])
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if b.bbox_mm[0] > a.bbox_mm[2]:
                break                                  # sweep: no x-overlap with later items
            if b.bbox_mm[1] > a.bbox_mm[3] or b.bbox_mm[3] < a.bbox_mm[1]:
                continue
            if a.is_legend and b.is_legend:
                continue
            inter = _clip(a.corners_mm, b.corners_mm)
            area = _area(inter)
            smaller = min(_area(a.corners_mm), _area(b.corners_mm)) or 1e-9
            if area < p["min_overlap_mm2"] or area / smaller < p["min_overlap_frac"]:
                continue
            pa, pb = panel_of(a.axes, fig), panel_of(b.axes, fig)
            if a.tick_axis and a.tick_axis == b.tick_axis:
                check, sev = "tick_label_collision", "error"
                hint = "fewer ticks, a smaller tick label size, or rotate the labels"
            elif pa is not None and pb is not None and pa is not pb:
                check, sev = "cross_panel_text_overlap", "error"
                hint = "increase the spacing between these panels (wspace/hspace or panel positions)"
            else:
                check, sev = "text_overlap", "warn"
                hint = "move or shorten one of the texts"
            xs = [x for x, _ in inter]
            ys = [y for _, y in inter]
            out.append(Finding(check, sev, f"{a.text[:40]!r} overlaps {b.text[:40]!r}",
                               [min(xs), min(ys), max(xs), max(ys)],
                               panel=_panel_label(pa or pb, fig), measured=round(area, 3),
                               threshold=p["min_overlap_mm2"], hint=hint))
    return out


def _check_clipping(fig, texts: list[_Text], saved_mm: list[float] | None, renderer, p: dict) -> list[Finding]:
    if saved_mm is None:
        return []
    tol = p["canvas_tol_mm"]
    out = []
    for t in texts:
        b = t.bbox_mm
        over = max(saved_mm[0] - b[0], saved_mm[1] - b[1], b[2] - saved_mm[2], b[3] - saved_mm[3])
        if over > tol:
            out.append(Finding("clipped_by_saved_area", "error",
                               f"text {t.text[:40]!r} extends {over:.1f} mm past the saved area", b,
                               panel=_panel_label(panel_of(t.axes, fig), fig), measured=round(over, 2),
                               threshold=tol, hint="enlarge the figure margins in the config or move the text inward"))
    for ax in fig.get_axes():
        if not ax.get_visible():
            continue
        b = _bbox_mm(ax.get_window_extent(renderer), renderer.dpi)
        over = max(saved_mm[0] - b[0], saved_mm[1] - b[1], b[2] - saved_mm[2], b[3] - saved_mm[3])
        if over > tol:
            out.append(Finding("clipped_by_saved_area", "error",
                               f"plot area extends {over:.1f} mm past the saved area", b,
                               panel=_panel_label(panel_of(ax, fig), fig), measured=round(over, 2), threshold=tol,
                               hint="the axes position is outside the canvas; adjust the layout"))
    return out


def _check_legends(fig, legends, renderer, p: dict) -> list[Finding]:
    out = []
    for leg_ax, lb in legends:
        own = panel_of(leg_ax, fig) if leg_ax is not None else None
        la = _box_area(lb) or 1e-9
        for ax in fig.get_axes():
            if not ax.get_visible() or not ax.axison or panel_of(ax, fig) is own:
                continue
            ov = _box_overlap(lb, _bbox_mm(ax.get_window_extent(renderer), renderer.dpi))
            if ov and _box_area(ov) / la >= p["legend_overlap_frac"]:
                out.append(Finding("legend_overlaps_panel", "error",
                                   f"legend of {_panel_label(own, fig)} covers {_box_area(ov) / la:.0%} "
                                   f"of itself inside {_panel_label(panel_of(ax, fig), fig)}", ov,
                                   panel=_panel_label(own, fig), measured=round(_box_area(ov) / la, 3),
                                   threshold=p["legend_overlap_frac"],
                                   hint="move the legend (loc / bbox_to_anchor) into free space"))
        if own is not None:
            f = _legend_on_data(fig, own, lb, la, renderer, p)
            if f:
                out.append(f)
    return out


def _legend_on_data(fig, own, lb, la, renderer, p) -> Finding | None:
    """A legend lying on the data of its own panel: the bars or filled areas
    under it (area share), and the scatter points or line samples (1 mm apart)
    inside it."""
    from matplotlib.collections import PathCollection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    k = MM_PER_INCH / renderer.dpi
    x0, y0, x1, y1 = lb
    inside = lambda x, y: x0 <= x <= x1 and y0 <= y <= y1          # noqa: E731
    covered, hits = 0.0, 0
    for ax in fig.get_axes():
        if panel_of(ax, fig) is not own or not ax.get_visible():
            continue
        for a in ax.patches:
            if isinstance(a, Rectangle) and a.get_visible() and a.get_fill():
                ov = _box_overlap(lb, _bbox_mm(a.get_window_extent(renderer), renderer.dpi))
                covered += _box_area(ov) if ov else 0.0
        for c in ax.collections:
            if isinstance(c, PathCollection) and c.get_visible() and len(c.get_offsets()):
                offs = np.ma.filled(np.ma.asarray(c.get_offsets(), dtype=float), np.nan)
                pts = c.get_offset_transform().transform(offs) * k      # missing points stay NaN
                ok = np.isfinite(pts).all(axis=1)
                hits += int(np.sum(ok & (pts[:, 0] >= x0) & (pts[:, 0] <= x1) & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)))
        for line in ax.lines:
            if not line.get_visible() or line.get_linestyle() in ("None", "none", "", " "):
                continue
            if not all(line.get_transform().contains_branch_seperately(ax.transData)):
                continue                         # a reference line across the axes (axhline, axvline)
            xy = line.get_transform().transform(line.get_xydata()) * k
            for (ax_, ay), (bx, by) in zip(xy[:-1], xy[1:]):
                n = max(1, int(math.hypot(bx - ax_, by - ay)))          # about one sample per mm
                hits += sum(inside(ax_ + (bx - ax_) * i / n, ay + (by - ay) * i / n) for i in range(n + 1))
    if covered / la < p["legend_data_frac"] and hits < p["legend_data_points"]:
        return None
    what = []
    if covered / la >= p["legend_data_frac"]:
        what.append(f"{covered / la:.0%} of it over bars or areas")
    if hits >= p["legend_data_points"]:
        what.append(f"{hits} point(s) or line sample(s) under it")
    return Finding("legend_covers_data", "warn", f"legend of {_panel_label(own, fig)} lies on its data: " + ", ".join(what),
                   lb, panel=_panel_label(own, fig), measured=round(covered / la, 3), threshold=p["legend_data_frac"],
                   hint="move the legend to free space (loc, bbox_to_anchor), outside the axes, or widen the axis range")


def _plot_areas(fig, renderer) -> list[tuple[object, object, list[float]]]:
    """(axes, panel, plot-area box in mm) for every visible axes with its axis on."""
    out = []
    for ax in fig.get_axes():
        if ax.get_visible() and ax.axison:
            out.append((ax, panel_of(ax, fig), _bbox_mm(ax.get_window_extent(renderer), renderer.dpi)))
    return out


def _check_panel_overlap(fig, texts: list[_Text], renderer, p: dict) -> list[Finding]:
    """Real intrusion, not bounding-box proximity: two panels' plot areas
    overlapping (panel_overlap), or a text of one panel lying on another
    panel's plot area (panel_intrusion). Panels' *outer* boxes may overlap
    harmlessly -- e.g. a wide title above a neighbouring axes' whitespace."""
    areas = _plot_areas(fig, renderer)
    out = []
    for i, (ax_a, pa, ba) in enumerate(areas):
        for ax_b, pb, bb in areas[i + 1:]:
            if pa is pb:
                continue
            ov = _box_overlap(ba, bb)
            if ov and _box_area(ov) >= p["panel_overlap_mm2"]:
                out.append(Finding("panel_overlap", "error",
                                   f"plot areas of {_panel_label(pa, fig)} and {_panel_label(pb, fig)} overlap "
                                   f"({_box_area(ov):.1f} mm²)", ov, panel=_panel_label(pa, fig),
                                   measured=round(_box_area(ov), 2), threshold=p["panel_overlap_mm2"],
                                   hint="the panels' positions overlap; adjust the GridSpec / axes positions"))
    for t in texts:
        if t.axes is None or t.is_legend:
            continue
        pt = panel_of(t.axes, fig)
        t_area = _area(t.corners_mm) or 1e-9
        for ax, pan, box in areas:
            if pan is pt:
                continue
            clip_box = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
            inter = _clip(t.corners_mm, clip_box)
            area = _area(inter)
            if area >= p["min_overlap_mm2"] and area / t_area >= p["min_overlap_frac"]:
                xs, ys = [x for x, _ in inter], [y for _, y in inter]
                out.append(Finding("panel_intrusion", "error",
                                   f"text {t.text[:40]!r} of {_panel_label(pt, fig)} lies on the plot area of "
                                   f"{_panel_label(pan, fig)}", [min(xs), min(ys), max(xs), max(ys)],
                                   panel=_panel_label(pt, fig), measured=round(area, 3),
                                   threshold=p["min_overlap_mm2"],
                                   hint="increase the spacing between these panels (wspace/hspace or positions)"))
    return out


# --------------------------------------------------------------------- colour --
# Machado, Oliveira & Fernandes (2009), severity 1.0, applied to linear sRGB.
_CVD = {
    "deuteranomaly": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413],
                               [-0.011820, 0.042940, 0.968881]]),
    "protanomaly": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216],
                             [-0.003882, -0.048116, 1.051998]]),
    "tritanomaly": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602],
                             [0.004733, 0.691367, 0.303900]]),
}
_RGB2XYZ = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
_RAINBOW = {"jet", "rainbow", "gist_rainbow", "hsv", "nipy_spectral", "gist_ncar", "gist_stern", "prism", "flag"}
_RED_GREEN = {"RdYlGn", "brg"}


def _linear(rgb) -> np.ndarray:
    c = np.asarray(rgb, dtype=float)[..., :3]
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lab(lin_rgb) -> np.ndarray:
    xyz = (np.clip(lin_rgb, 0, 1) @ _RGB2XYZ.T) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def _luminance(rgb) -> float:
    return float(_linear(rgb) @ np.array([0.2126, 0.7152, 0.0722]))


def _legend_colors(leg) -> list:
    """The colour each legend entry shows (its key a reader matches by colour)."""
    from matplotlib.collections import Collection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    out = []
    for h in getattr(leg, "legend_handles", None) or getattr(leg, "legendHandles", []):
        c = None
        if isinstance(h, Line2D):
            c = h.get_color() if h.get_linestyle() not in ("None", "none", "", " ") else h.get_markerfacecolor()
        elif isinstance(h, Patch):
            c = h.get_facecolor() if h.get_facecolor()[3] > 0 else h.get_edgecolor()
        elif isinstance(h, Collection):
            fc = h.get_facecolor()
            c = fc[0] if len(fc) else (h.get_edgecolor()[0] if len(h.get_edgecolor()) else None)
        if c is not None and to_rgba(c)[3] > 0:
            out.append(to_rgba(c))
    return out


def _categorical_sets(fig) -> list[tuple[str, list, object]]:
    """Colour sets a reader has to tell apart: each legend's entries, and the
    distinct single colours of scatter groups drawn in one axes -- each with
    the artist that shows them (the legend, or the axes), for its location."""
    from matplotlib.collections import PathCollection
    from matplotlib.legend import Legend
    sets = []
    for leg in fig.findobj(Legend):
        if leg.get_visible():
            cols = _legend_colors(leg)
            if len(cols) >= 2:
                sets.append((f"legend of {_panel_label(leg.axes, fig) if leg.axes else 'figure'}", cols, leg))
    for ax in fig.get_axes():
        cols = []
        for c in ax.collections:
            if isinstance(c, PathCollection) and c.get_visible() and c.get_array() is None:
                fc = {tuple(np.round(x, 4)) for x in c.get_facecolor()}
                if len(fc) == 1:
                    cols.append(next(iter(fc)))
        cols = list(dict.fromkeys(cols))
        if len(cols) >= 2 and not ax.get_legend():
            sets.append((f"scatter groups in {_panel_label(ax, fig)}", cols, ax))
    return sets


def _check_cvd(fig, p: dict) -> list[Finding]:
    out = []
    thr = p["min_cvd_delta_e"]
    renderer = fig.canvas.get_renderer()
    k = MM_PER_INCH / fig.dpi
    for where, cols, artist in _categorical_sets(fig):
        try:
            b = artist.get_window_extent(renderer)
            box = [b.x0 * k, b.y0 * k, b.x1 * k, b.y1 * k]
        except Exception:       # an artist that cannot report its extent: no location
            box = _no_box()
        lin = _linear(np.array(cols))
        normal = _lab(lin)
        for kind in p["cvd_types"]:
            sim = _lab(lin @ _CVD[kind].T)
            worst = None
            for i, j in itertools.combinations(range(len(cols)), 2):
                if np.linalg.norm(normal[i] - normal[j]) < thr:
                    continue        # not meant to be told apart (or already alike for everyone)
                de = float(np.linalg.norm(sim[i] - sim[j]))
                if de < thr and (worst is None or de < worst[0]):
                    worst = (de, i, j)
            if worst:
                de, i, j = worst
                out.append(Finding("cvd_indistinct", "warn",
                                   f"{where}: {to_hex(cols[i])} and {to_hex(cols[j])} look alike with {kind} "
                                   f"(delta-E {de:.1f})", box, measured=round(de, 1), threshold=thr,
                                   hint="use a colour-blind-safe palette (e.g. Okabe-Ito) or add marker/line-style differences"))
    return out


def _check_colormaps(fig, p: dict) -> list[Finding]:
    from matplotlib.cm import ScalarMappable
    cmaps = {}
    for a in fig.findobj(lambda a: isinstance(a, ScalarMappable)):
        if getattr(a, "get_visible", lambda: True)() and (a.get_array() is not None):
            cmaps.setdefault(a.get_cmap().name, a.get_cmap())
    out = []
    for name, cmap in sorted(cmaps.items()):
        base = name[:-2] if name.endswith("_r") else name
        if base in _RAINBOW:
            out.append(Finding("cmap_rainbow", "warn", f"colormap '{name}' is rainbow-like: its lightness jumps, "
                               f"creating false boundaries and hiding real ones", _no_box(),
                               hint="use a perceptually uniform map (viridis, cividis, magma) or a diverging one (RdBu_r)"))
            continue
        if base in _RED_GREEN:
            out.append(Finding("cmap_red_green", "warn", f"colormap '{name}' separates its ends by red vs. green, "
                               f"which red-green colour-blind readers can't distinguish", _no_box(),
                               hint="use RdBu_r, PuOr or BrBG"))
            continue
        if getattr(cmap, "N", 256) < 16:
            continue                              # a few discrete categories, not a scale
        L = _lab(_linear(cmap(np.linspace(0, 1, 64))))[:, 0]
        d = np.diff(L)
        d = d[np.abs(d) > 0.5]                    # ignore flat stretches / rounding
        turns = int(np.sum(np.diff(np.sign(d)) != 0)) if len(d) > 1 else 0
        if turns > 1:                             # sequential: 0 turns; diverging: 1
            out.append(Finding("cmap_nonuniform", "warn", f"colormap '{name}' gets lighter and darker "
                               f"{turns + 1} times along its range", _no_box(), measured=float(turns),
                               threshold=1.0, hint="use a sequential or diverging colormap with monotonic lightness"))
    return out


def _check_text_contrast(fig, texts: list[_Text], p: dict) -> list[Finding]:
    """Contrast of each text against what is drawn behind it: render once
    with every text hidden and take the median background colour under it."""
    from matplotlib.text import Text
    if not texts:
        return []
    # Hide the glyphs but keep a text's own background box (bbox patch): a label
    # on a dark box is read against the box, not against the image beneath it.
    shown = [t for t in fig.findobj(Text) if t.get_visible()]
    boxed = {id(t): t.get_color() for t in shown if t.get_bbox_patch() is not None}
    for t in shown:
        if id(t) in boxed:
            t.set_color((0, 0, 0, 0))
        else:
            t.set_visible(False)
    try:
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())[..., :3].astype(float) / 255.0
    finally:
        for t in shown:
            if id(t) in boxed:
                t.set_color(boxed[id(t)])
            else:
                t.set_visible(True)
    h, w = buf.shape[:2]
    k = fig.dpi / MM_PER_INCH
    groups: dict[tuple, list] = {}
    for t in texts:
        x0, y0, x1, y1 = t.bbox_mm
        c0, c1 = max(0, int(x0 * k)), min(w, int(math.ceil(x1 * k)))
        r0, r1 = max(0, int(h - y1 * k)), min(h, int(math.ceil(h - y0 * k)))
        if c1 - c0 < 1 or r1 - r0 < 1:
            continue
        bg = np.median(buf[r0:r1, c0:c1].reshape(-1, 3), axis=0)
        r, g, b, a = t.color
        fg = np.array([r, g, b]) * a + bg * (1 - a)
        l1, l2 = sorted((_luminance(fg), _luminance(bg)), reverse=True)
        ratio = (l1 + 0.05) / (l2 + 0.05)
        if ratio >= p["min_text_contrast"]:
            continue
        # Grey text on a white background, still readable, is a deliberate
        # de-emphasis ("not significant", placeholders): info, not a warning.
        fg_lab, bg_lab = _lab(_linear(fg)), _lab(_linear(bg))
        muted = (math.hypot(fg_lab[1], fg_lab[2]) <= p["muted_max_chroma"] and bg_lab[0] > 92
                 and ratio >= p["muted_text_min_contrast"])
        panel = _panel_label(panel_of(t.axes, fig), fig)
        groups.setdefault((muted, to_hex(fg), panel), []).append((t, bg, ratio))

    # One finding per text colour and panel: a heatmap's 80 grey "-" cells
    # are one design decision, not 80 problems.
    out = []
    for (muted, fg_hex, panel), items in groups.items():
        ratios = [r for _, _, r in items]
        boxes = [t.bbox_mm for t, _, _ in items]
        box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        examples = ", ".join(repr(t.text[:20]) for t, _, _ in items[:3])
        bgs = sorted({to_hex(bg) for _, bg, _ in items})
        span = f"{min(ratios):.1f}:1" if len(items) == 1 else f"{min(ratios):.1f}-{max(ratios):.1f}:1"
        what = f"{len(items)} texts" if len(items) > 1 else "text"
        msg = f"{what} in {fg_hex} on {', '.join(bgs[:2])}{'...' if len(bgs) > 2 else ''} have contrast {span} (e.g. {examples})"
        if muted:
            out.append(Finding("low_text_contrast", "info", msg + " -- grey on white, read as deliberate de-emphasis",
                               box, panel=panel, measured=round(min(ratios), 2),
                               threshold=p["min_text_contrast"],
                               hint="fine if these are meant to recede; darken them if readers must read them"))
        else:
            out.append(Finding("low_text_contrast", "warn", msg, box, panel=panel, measured=round(min(ratios), 2),
                               threshold=p["min_text_contrast"],
                               hint="switch text colour by cell value (white on dark, black on light) or change the background"))
    return out


# ---------------------------------------------------- layout rules & sizes --
def _poly_distance(a, b) -> float:
    """Distance between two convex polygons (0 if they intersect)."""
    if _area(_clip(a, b)) > 0:
        return 0.0

    def pt_seg(p, s0, s1):
        dx, dy = s1[0] - s0[0], s1[1] - s0[1]
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - s0[0]) * dx + (p[1] - s0[1]) * dy) / L))
        return math.hypot(p[0] - (s0[0] + t * dx), p[1] - (s0[1] + t * dy))

    return min(min(pt_seg(pt, q[i], q[(i + 1) % len(q)]) for pt in pp for i in range(len(q)))
               for pp, q in ((a, b), (b, a)))


def _check_tick_gaps(fig, texts: list[_Text], p: dict) -> list[Finding]:
    """Neighbouring tick labels of one axis that don't overlap but nearly
    touch ("24h48h" reads as one label)."""
    by_axis: dict[str, list[_Text]] = {}
    for t in texts:
        if t.tick_axis:
            by_axis.setdefault(t.tick_axis, []).append(t)
    out = []
    for axis_key, labels in by_axis.items():
        along = 0 if axis_key.startswith("x") else 1
        labels = sorted(labels, key=lambda t: (t.bbox_mm[along] + t.bbox_mm[along + 2]) / 2)
        close = []
        for a, b in zip(labels, labels[1:]):
            inter = _area(_clip(a.corners_mm, b.corners_mm))
            smaller = min(_area(a.corners_mm), _area(b.corners_mm)) or 1e-9
            if inter >= p["min_overlap_mm2"] and inter / smaller >= p["min_overlap_frac"]:
                continue          # a real overlap: reported as tick_label_collision
            # A sliver of overlap below that threshold has distance 0 and
            # touches just the same -- don't let it fall between the checks.
            gap = _poly_distance(a.corners_mm, b.corners_mm)
            if gap < p["min_tick_gap_mm"]:
                close.append((a, b, gap))
        if close:
            boxes = [t.bbox_mm for a, b, _ in close for t in (a, b)]
            box = [min(x[0] for x in boxes), min(x[1] for x in boxes), max(x[2] for x in boxes), max(x[3] for x in boxes)]
            ex = ", ".join(f"{a.text!r}|{b.text!r}" for a, b, _ in close[:3])
            out.append(Finding("tick_labels_touching", "warn",
                               f"{len(close)} pair(s) of neighbouring tick labels are {min(g for *_, g in close):.2f} mm "
                               f"or less apart (e.g. {ex})", box,
                               panel=_panel_label(panel_of(close[0][0].axes, fig), fig),
                               measured=round(min(g for *_, g in close), 3), threshold=p["min_tick_gap_mm"],
                               hint="shorten or rotate the labels, use fewer ticks, or widen the panel"))
    return out


def _check_panel_tags(texts: list[_Text], p: dict) -> list[Finding]:
    """AGENTS.md rule 1.5 and journal tag style: tags stacked in one column
    share one plumb line; all tags share size, weight and case."""
    tags = [t for t in texts if t.role == "panel_tag"]
    out = []
    if not tags:
        return out
    styles = {(round(t.fontsize, 1), t.weight, "upper" if t.text.isupper() else "lower") for t in tags}
    if len(styles) > 1:
        out.append(Finding("panel_tag_inconsistent", "warn",
                           "panel tags differ in style: " + "; ".join(f"{s} pt {w} {c}" for s, w, c in sorted(styles)),
                           _no_box(), hint="place all tags with one place_panel_tags call / the same config values"))
    case, size = p.get("panel_tag_case"), p.get("panel_tag_size_pt")
    for t in tags:
        wrong = []
        if case == "lower" and not t.text.islower() or case == "upper" and not t.text.isupper():
            wrong.append(f"{case}case expected")
        if size and abs(t.fontsize - float(size)) > 0.05:
            wrong.append(f"{size} pt expected, is {t.fontsize:g} pt")
        if wrong:
            out.append(Finding("panel_tag_style", "warn", f"panel tag {t.text!r}: " + ", ".join(wrong), t.bbox_mm,
                               hint="set subpanel_label_size / the tag letters to the journal's style"))
    # Columns: tags whose left edges are close belong to one stacked column.
    tags = sorted(tags, key=lambda t: t.bbox_mm[0])
    column = [tags[0]]
    for t in tags[1:] + [None]:
        if t is not None and t.bbox_mm[0] - column[0].bbox_mm[0] <= p["panel_tag_column_mm"]:
            column.append(t)
            continue
        xs = [c.bbox_mm[0] for c in column]
        if len(column) > 1 and max(xs) - min(xs) > p["panel_tag_align_tol_mm"]:
            out.append(Finding("panel_tag_misaligned", "warn",
                               f"tags {', '.join(repr(c.text) for c in column)} stand in one column but their left "
                               f"edges differ by {max(xs) - min(xs):.2f} mm",
                               [min(xs), min(c.bbox_mm[1] for c in column), max(c.bbox_mm[2] for c in column),
                                max(c.bbox_mm[3] for c in column)],
                               measured=round(max(xs) - min(xs), 2), threshold=p["panel_tag_align_tol_mm"],
                               hint="place the tags with place_panel_tags so stacked panels share one plumb line"))
        column = [t] if t is not None else []
    return out


_SIZE_ROLES = ("tick", "axis_label", "panel_tag", "legend")


def font_size_profile(texts: list[_Text]) -> dict[str, dict[float, int]]:
    """{role: {font size pt: count}} for the roles compared within and across figures."""
    prof: dict[str, dict[float, int]] = {}
    for t in texts:
        if t.role in _SIZE_ROLES:
            sizes = prof.setdefault(t.role, {})
            sizes[round(t.fontsize, 2)] = sizes.get(round(t.fontsize, 2), 0) + 1
    return prof


def _check_font_sizes(fig, texts: list[_Text], p: dict) -> list[Finding]:
    """Within one role, a few texts in a size different from all the others
    usually means a hardcoded size somewhere (AGENTS.md rule 1.2)."""
    out = []
    for role, sizes in font_size_profile(texts).items():
        total = sum(sizes.values())
        mode = max(sizes, key=sizes.get)
        odd = {s: n for s, n in sizes.items() if s != mode}
        if total >= 4 and odd and sum(odd.values()) / total <= p["font_size_outlier_frac"]:
            ex = [t for t in texts if t.role == role and round(t.fontsize, 2) in odd][:3]
            out.append(Finding("font_size_outlier", "warn",
                               f"{role.replace('_', ' ')}s are {mode:g} pt except "
                               + ", ".join(f"{n} at {s:g} pt" for s, n in sorted(odd.items()))
                               + f" (e.g. {', '.join(repr(t.text[:20]) for t in ex)})",
                               ex[0].bbox_mm if ex else _no_box(), measured=float(min(odd)),
                               threshold=float(mode), hint="look for a hardcoded fontsize; take it from the config"))
    return out


def _check_raster_content(fig, save_dpi: float | None, p: dict) -> list[Finding]:
    """Rasterized artists and images are embedded in PDF/SVG at the savefig
    dpi, so a low dpi there blurs them even in a "vector" file."""
    if save_dpi is None:
        return []
    from matplotlib.image import AxesImage
    raster = [a for a in fig.findobj(lambda a: isinstance(a, AxesImage)
                                     or bool(getattr(a, "get_rasterized", None) and a.get_rasterized()))
              if a.get_visible()]
    if raster and save_dpi < p["min_raster_dpi"]:
        return [Finding("raster_dpi_low", "error",
                        f"{len(raster)} rasterized element(s) (images, rasterized=True artists) would be "
                        f"embedded at {save_dpi:.0f} dpi in vector output", [0.0, 0.0, 0.0, 0.0],
                        measured=float(save_dpi), threshold=float(p["min_raster_dpi"]),
                        hint="save with a higher dpi (figures.dpi in the config) or don't rasterize")]
    return []


def _merge_repeats(findings: list[Finding]) -> list[Finding]:
    """Identical findings from several panels of one figure (the same issue
    in each of 7 mini-panels) become one, noting how many panels."""
    groups: dict[tuple, list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.check, f.severity, f.message), []).append(f)
    out = []
    for (_, _, _), fs in groups.items():
        f = fs[0]
        if len(fs) > 1:
            boxes = [x.bbox_mm for x in fs]
            f.bbox_mm = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                         max(b[2] for b in boxes), max(b[3] for b in boxes)]
            f.message += f" -- in {len(fs)} panels"
        out.append(f)
    return out


# ---------------------------------------------------------------------- API --
def preflight(fig, saved_bbox_in=None, params: dict | None = None,
              save_dpi: float | None = None, profile: dict | None = None) -> list[Finding]:
    """Run the checks on ``fig``.

    ``saved_bbox_in``: the region that will be saved, in inches as
    ``(x0, y0, x1, y1)`` -- the canvas (``None`` -> whole canvas) for a plain
    ``savefig``, the tight box for ``bbox_inches="tight"`` (pass ``"tight"``:
    nothing can be clipped then), or the box ``fig_atlas.page.save_page_figure``
    uses. ``save_dpi``: the dpi the figure is saved with, for raster content
    in vector output (``None`` skips that check). ``profile``: if given, it is
    filled with the figure's font sizes per text role (``font_size_profile``)
    so a caller can compare figures with each other.
    """
    p = {**DEFAULTS, **(params or {})}
    rec = _Record()
    with _hook_texts(fig, rec, {"shrink": p["text_ink_shrink"]}):
        fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    if saved_bbox_in == "tight":
        saved_mm = None
    elif saved_bbox_in is None:
        w, h = fig.get_size_inches()
        saved_mm = [0.0, 0.0, w * MM_PER_INCH, h * MM_PER_INCH]
    else:
        saved_mm = [v * MM_PER_INCH for v in saved_bbox_in]

    findings = (_check_text_overlap(fig, rec.texts, p)
                + _check_clipping(fig, rec.texts, saved_mm, renderer, p)
                + _check_legends(fig, rec.legends, renderer, p)
                + _check_panel_overlap(fig, rec.texts, renderer, p)
                + _check_raster_content(fig, save_dpi, p)
                + _check_cvd(fig, p)
                + _check_colormaps(fig, p)
                + _check_text_contrast(fig, rec.texts, p)
                + _check_tick_gaps(fig, rec.texts, p)
                + _check_panel_tags(rec.texts, p)
                + _check_font_sizes(fig, rec.texts, p))
    findings = _apply_allow(fig, _merge_repeats(findings), renderer, p)
    if profile is not None:
        profile.update(font_size_profile(rec.texts))
    if rec.errors:
        findings.append(Finding("recorder_error", "warn",
                                f"{len(rec.errors)} element(s) could not be measured, so they were not checked: "
                                + "; ".join(rec.errors[:3]), [0.0, 0.0, 0.0, 0.0],
                                hint="report this as a fig_atlas.preflight bug"))
    order = {"error": 0, "warn": 1, "info": 2}
    return sorted(findings, key=lambda f: (order[f.severity], f.check))


def _apply_allow(fig, findings: list[Finding], renderer, p: dict) -> list[Finding]:
    """Turn findings inside axes marked ``fa-allow:<name>`` into info, with the
    reason the config gives for <name> (module docstring, "Allowed defects")."""
    reasons = p.get("allow") or {}
    regions, out = [], []
    k = MM_PER_INCH / fig.dpi
    for ax in fig.get_axes():
        gid = ax.get_gid() or ""
        if not gid.startswith(ALLOW_GID):
            continue
        name = gid[len(ALLOW_GID):]
        if not reasons.get(name):
            out.append(Finding("allow_without_reason", "warn",
                               f"axes marked {gid!r} but the config gives no reason for {name!r}, so nothing is allowed",
                               _no_box(), panel=_panel_label(ax, fig),
                               hint=f"add preflight.allow.{name}: \"<why this defect is shown on purpose>\" to the config"))
            continue
        b = ax.get_tightbbox(renderer)
        regions.append((name, reasons[name], [b.x0 * k, b.y0 * k, b.x1 * k, b.y1 * k]))
    for f in findings:
        x0, y0, x1, y1 = f.bbox_mm
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hit = next((r for r in regions if f.bbox_mm != _no_box()
                    and r[2][0] <= cx <= r[2][2] and r[2][1] <= cy <= r[2][3]), None)
        if hit:
            f = Finding(f.check, "info", f"allowed ({hit[0]}: {hit[1]}) -- {f.message}", f.bbox_mm,
                        panel=f.panel, measured=f.measured, threshold=f.threshold, hint=f.hint)
        out.append(f)
    return out


def draw_overlay(fig, findings: list[Finding], path, dpi: int = 150) -> None:
    """Save ``fig`` with each finding outlined and numbered (red = error,
    orange = warn), for a person or an agent to see where the problem is."""
    from matplotlib.patches import Rectangle

    # Boxes are placed in inches on the canvas, not in pixels: savefig(dpi=...)
    # redraws at the overlay's dpi, and pixel positions taken at the figure's
    # own dpi put every box in the wrong place when the two differ.
    k = 1 / MM_PER_INCH
    w_in, h_in = fig.get_size_inches()
    added = []
    for n, f in enumerate(findings, 1):
        x0, y0, x1, y1 = f.bbox_mm
        color = "#dc2626" if f.severity == "error" else "#f59e0b"
        pad = 0.4
        r = Rectangle(((x0 - pad) * k, (y0 - pad) * k), (x1 - x0 + 2 * pad) * k, (y1 - y0 + 2 * pad) * k,
                      transform=fig.dpi_scale_trans, fill=False, edgecolor=color, linewidth=1.0, zorder=1e6)
        t = fig.text((x1 + pad) * k / w_in, (y1 + pad) * k / h_in,
                     str(n), color=color, fontsize=6, fontweight="bold", zorder=1e6)
        fig.add_artist(r)
        added += [r, t]
    try:
        fig.savefig(path, dpi=dpi)
    finally:
        for a in added:
            a.remove()


# ----------------------------------------------------------- saved files --
def _no_box() -> list[float]:
    return [0.0, 0.0, 0.0, 0.0]


def check_pdf(path, params: dict | None = None) -> list[Finding]:
    """Font checks on a saved PDF: Type 3 fonts, fonts not embedded, and fonts
    outside ``allowed_fonts``. Each page / Form XObject resource dict is
    visited once (figures can hold thousands of marker XObjects sharing one)."""
    from pypdf import PdfReader

    p = {**DEFAULTS, **(params or {})}
    allowed = {f.lower() for f in p.get("allowed_fonts") or []}
    seen: set = set()
    fonts: dict[str, tuple[str, bool]] = {}   # font name -> (subtype, embedded)

    def walk(res):
        if res is None:
            return
        key = getattr(res, "idnum", None)
        res = res.get_object()
        key = key if key is not None else id(res)
        if key in seen:
            return
        seen.add(key)
        for _, ref in (res.get("/Font") or {}).items():
            f = ref.get_object()
            sub = str(f.get("/Subtype"))
            desc = f.get("/FontDescriptor")
            if sub == "/Type0" and f.get("/DescendantFonts"):
                desc = f["/DescendantFonts"][0].get_object().get("/FontDescriptor")
            desc = desc.get_object() if desc is not None else None
            embedded = sub == "/Type3" or (desc is not None and any(
                k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")))
            name = str(f.get("/BaseFont", f.get("/Name", "?"))).lstrip("/")
            fonts[name.split("+", 1)[-1]] = (sub, embedded)
        for _, ref in (res.get("/XObject") or {}).items():
            x = ref.get_object()
            if x.get("/Subtype") == "/Form":
                walk(x.get("/Resources"))

    for page in PdfReader(str(path)).pages:
        walk(page.get("/Resources"))
    out = []
    for name, (sub, embedded) in sorted(fonts.items()):
        if sub == "/Type3":
            out.append(Finding("pdf_type3_font", "error", f"font {name} is embedded as Type 3", _no_box(),
                               hint="set pdf.fonttype: 42 (repo matplotlibrc) and run from the repository root"))
        elif not embedded:
            out.append(Finding("pdf_font_not_embedded", "error",
                               f"font {name} ({sub.lstrip('/')}) is not embedded", _no_box(),
                               hint="don't use pdf.use14corefonts; let matplotlib embed the font"))
        if allowed and name.lower() not in allowed and name.split("-")[0].lower() not in allowed:
            out.append(Finding("pdf_font_not_allowed", "warn", f"font {name} is not in allowed_fonts", _no_box(),
                               hint="use one of: " + ", ".join(sorted(allowed))))
    return out


def check_png(path, params: dict | None = None, printed_width_in: float | None = None) -> list[Finding]:
    """Effective resolution of a saved PNG at its printed size: pixel width over
    the printed width. ``printed_width_in`` is used when the print size is
    known (a figure scaled to fit a page); otherwise the PNG's own width from
    its dpi tag."""
    from PIL import Image

    p = {**DEFAULTS, **(params or {})}
    # Our own outputs can legitimately exceed Pillow's decompression-bomb
    # pixel limit (large exploratory canvases); only the header is read.
    limit, Image.MAX_IMAGE_PIXELS = Image.MAX_IMAGE_PIXELS, None
    try:
        with Image.open(path) as im:
            px_w = im.size[0]
            tag = (im.info.get("dpi") or (None,))[0]
    finally:
        Image.MAX_IMAGE_PIXELS = limit
    width_in = printed_width_in or ((px_w / float(tag)) if tag else None)
    if not width_in:
        return []
    eff = px_w / width_in
    if eff + 0.5 < p["min_dpi"]:
        return [Finding("png_dpi_low", "error", f"{eff:.0f} pixels per printed inch", _no_box(),
                        measured=round(eff, 1), threshold=float(p["min_dpi"]),
                        hint="raise figures.dpi in the config")]
    return []


@contextmanager
def capture_font_issues():
    """Collect font problems raised while rendering: font families matplotlib
    could not find (it silently substitutes another font -- the usual reason a
    figure looks different on another machine) and glyphs the font lacks.
    Yields a list that is filled with ``Finding``s when the block exits."""
    import logging
    import re
    import warnings

    found: list[Finding] = []
    families: set[str] = set()
    glyphs: set[str] = set()

    class _Handler(logging.Handler):
        def emit(self, record):
            m = re.search(r"Font family '([^']+)' not found", record.getMessage())
            if m:
                families.add(m.group(1))

    handler = _Handler(level=logging.WARNING)
    logger = logging.getLogger("matplotlib.font_manager")
    logger.addHandler(handler)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            yield found
        for w in caught:
            m = re.search(r"Glyph \d+ \((.+?)\) missing from font\(s\) (.+?)\.?$", str(w.message))
            if m:
                glyphs.add(f"{m.group(1)} in {m.group(2)}")
    finally:
        logger.removeHandler(handler)
    for fam in sorted(families):
        found.append(Finding("font_fallback", "error",
                             f"font family '{fam}' was not found; matplotlib substituted another font",
                             _no_box(), hint="install the font, or set font_family in the config to an available one"))
    for g in sorted(glyphs):
        found.append(Finding("missing_glyph", "warn", f"missing glyph {g} (drawn as a box)", _no_box(),
                             hint="use a font that has this character, or replace the character"))


# ---------------------------------------------------------- print size (C1) --
def check_print_size(fig, page, min_font_pt: float = 5.0, min_line_pt: float = 0.25,
                     allow: dict | None = None) -> list[Finding]:
    """C1 as findings: how ``fig`` prints on ``page`` (a ``fig_atlas.page.PageSpec``),
    measured by ``fig_atlas.print_check.audit_figure``.

    print_font_too_small   texts print below ``min_font_pt``         error
    print_line_too_thin    lines print thinner than ``min_line_pt``  warn
    print_exceeds_page     the figure needs more than one page       warn

    ``allow`` (name -> reason, the config's ``preflight.allow``): text and lines
    in axes marked ``fa-allow:<name>`` are measured apart and reported as info
    with the reason (module docstring, "Allowed defects"); the page size is
    measured on the whole figure.
    """
    from .print_check import audit_figure

    reasons = allow or {}
    marked = [(ax, (ax.get_gid() or "")[len(ALLOW_GID):]) for ax in fig.get_axes()
              if (ax.get_gid() or "").startswith(ALLOW_GID)]
    marked = [(ax, name) for ax, name in marked if reasons.get(name)]
    whole = audit_figure(fig, page, min_font_pt, min_line_pt)
    a, allowed = whole, []
    if marked:
        shown = [ax.get_visible() for ax, _ in marked]
        try:
            for ax, _ in marked:
                ax.set_visible(False)
            a = audit_figure(fig, page, min_font_pt, min_line_pt)
        finally:
            for (ax, _), v in zip(marked, shown):
                ax.set_visible(v)
        a = {**a, "fits_one_page": whole["fits_one_page"], "printed_height_mm": whole["printed_height_mm"],
             "pages_needed": whole["pages_needed"]}
        names = sorted({name for _, name in marked})
        why = "; ".join(f"{nm}: {reasons[nm]}" for nm in names)
        if whole["n_texts_below_min"] > a["n_texts_below_min"]:
            allowed.append(Finding("print_font_too_small", "info",
                                   f"allowed ({why}) -- {whole['n_texts_below_min'] - a['n_texts_below_min']} text(s) "
                                   f"below {min_font_pt:g} pt in marked axes", _no_box(),
                                   measured=whole["min_font_printed_pt"], threshold=min_font_pt))
        if whole["n_lines_below_min"] > a["n_lines_below_min"]:
            allowed.append(Finding("print_line_too_thin", "info",
                                   f"allowed ({why}) -- {whole['n_lines_below_min'] - a['n_lines_below_min']} line(s) "
                                   f"thinner than {min_line_pt:g} pt in marked axes", _no_box(),
                                   measured=whole["min_line_printed_pt"], threshold=min_line_pt))
    out = allowed
    scale = a["scale_to_page_width"]
    scaled = f" (scaled to {scale:.0%} to fit the page width)" if scale < 0.999 else ""
    if not a["font_ok"]:
        ex = ", ".join(f"{s['text']!r} {s['printed_pt']:g} pt" for s in a["smallest_texts"][:3])
        out.append(Finding("print_font_too_small", "error",
                           f"{a['n_texts_below_min']} text(s) print below {min_font_pt:g} pt{scaled}: {ex}",
                           _no_box(), measured=a["min_font_printed_pt"], threshold=min_font_pt,
                           hint="raise the font sizes in the config, or draw the figure at final size so nothing is scaled"))
    if not a["line_ok"]:
        kinds = ", ".join(f"{k} x{n}" for k, n in a["thin_line_kinds"].items())
        out.append(Finding("print_line_too_thin", "warn",
                           f"{a['n_lines_below_min']} line(s) print thinner than {min_line_pt:g} pt{scaled} ({kinds})",
                           _no_box(), measured=a["min_line_printed_pt"], threshold=min_line_pt,
                           hint="raise line widths (axis_width, linewidth params) in the config"))
    if not a["fits_one_page"]:
        out.append(Finding("print_exceeds_page", "warn",
                           f"prints {a['printed_height_mm']:.0f} mm tall: {a['pages_needed']} pages of {a['page']}",
                           _no_box(), measured=float(a["pages_needed"]), threshold=1.0,
                           hint="split the figure, reduce its content, or move detail to a supplementary table"))
    return out
