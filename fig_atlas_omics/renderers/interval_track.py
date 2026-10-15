"""interval_track: genomic intervals and point events over a window --
deletions, SV calls, junctions -- packed into rows, coloured by kind.

An interval is drawn as a box, or as a bracket for kinds in ``bracket_kinds``.
Kinds in ``open_kinds`` have edges that are not known to be the real ends, e.g.
a segment bounded only by its last informative site. They lose their end
ticks and continue past both ends as a dotted line.
anything shorter than ``point_frac`` of the window is drawn as a triangle.

Data: one row per interval with the columns named by start_col, end_col and
kind_col (label_col optional). Returns the rows drawn with their row index,
ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from fig_atlas.params import text_param
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, typography, uses_schema

from ._tracks import pack_rows, text_span

SCHEMA = Schema("interval_track", params=[
    # [Data]
    Param("start_col", str, "start", role="Column with the interval start (bp, 1-based)"),
    Param("end_col", str, "end", role="Column with the interval end (bp)"),
    Param("kind_col", str, "kind", role="Column with the kind (sets colour and legend entry)"),
    Param("label_col", str, "label", role="Column with the text beside an interval (none: no text)"),
    Param("kind_order", list, None, role="Kinds in legend order (default: order in the data)"),
    # [Window]
    Param("x_min", float, None, unit="bp", role="Left end of the window (both x_min and x_max; none: the data extent)"),
    Param("x_max", float, None, unit="bp", role="Right end of the window"),
    # [Rows]
    Param("max_rows", int, 3, unit="rows", range=(1, None), role="Most rows", tune="raise if labels overlap on one row"),
    Param("row_gap_frac", float, 0.01, unit="fraction of the window", range=(0, None),
          role="Smallest gap between two intervals (with their labels) on one row"),
    # [Marks]
    Param("kind_colors", dict, {}, open_keys=True, unit="hex color", role="Colour per kind"),
    Param("kind_labels", dict, {}, open_keys=True, role="Legend text per kind"),
    Param("default_color", "color", "#6b7280", unit="hex color", role="Colour of kinds without one"),
    Param("bar_height", float, 0.45, unit="fraction of a row", range=(0, 1), role="Box height"),
    Param("bar_alpha", float, 0.85, unit="[0-1] opacity", range=(0, 1), role="Box opacity"),
    Param("bracket_kinds", list, [], role="Kinds drawn as a bracket (a line with end ticks) instead of a box"),
    Param("bracket_width", float, 0.8, unit="pt", range=(0, None), role="Bracket line width"),
    Param("open_kinds", list, [], role="Kinds whose edges are open: no end ticks, a dotted line past both ends"),
    Param("open_extend_frac", float, 0.04, unit="fraction of the window", range=(0, None),
          role="Length of that dotted line past each end", tune="raise to stress that the edge is uncertain"),
    Param("open_style", str, ":", role="Line style of that dotted line (matplotlib)"),
    Param("point_frac", float, 0.002, unit="fraction of the window", range=(0, None),
          role="Intervals shorter than this are drawn as a triangle"),
    Param("point_edge_width", float, 0.0, unit="pt", range=(0, None), role="Triangle outline width (0: filled only)"),
    Param("point_size", float, 4.0, unit="pt", range=(0, None), role="Triangle marker size"),
    # [Labels and legend]
    Param("label_size", float, 5.5, unit="pt", range=(0, None), role="Label size"),
    Param("label_pad_frac", float, 0.005, unit="fraction of the window", range=(0, None),
          role="Gap between an interval and its label (label right of it)"),
    Param("label_char_em", float, 0.6, unit="em per character", range=(0, None),
          role="Estimated text width per character (packing only)", tune="raise if labels on one row touch"),
    Param("text_color", "color", "#111827", unit="hex color", role="Label colour"),
    Param("show_legend", bool, True, role="Show a legend of the kinds drawn"),
    Param("legend_loc", str, "upper left", role="Legend location (matplotlib loc)"),
    Param("legend_anchor", list, [1.0, 1.0], unit="axes fraction [x, y]", role="Legend anchor point"),
    Param("legend_frameon", bool, False, role="Draw a frame around the legend"),
    *typography(legend_fontsize=CODE_DEFAULT),
    Param("labels_ylabel", str, None, role="Track name left of the track (none: no name)"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Track name size (default: rcParams)"),
])


@uses_schema(SCHEMA)
def render_interval_track(ax, df, params):
    """Draw the intervals onto ``ax``; returns them with their row."""
    a_col, b_col = params.get("start_col", "start"), params.get("end_col", "end")
    k_col, l_col = params.get("kind_col", "kind"), params.get("label_col", "label")
    data = df.sort_values(a_col).reset_index(drop=True).copy()
    lo, hi = params.get("x_min"), params.get("x_max")
    x0, x1 = (float(lo), float(hi)) if lo is not None and hi is not None \
        else (float(data[a_col].min()) - 1, float(data[b_col].max()))
    data = data[(data[b_col] >= x0) & (data[a_col] - 1 <= x1)].reset_index(drop=True)
    span = x1 - x0
    size = float(params.get("label_size", 5.5))
    em = float(params.get("label_char_em", 0.6))
    pad = float(params.get("label_pad_frac", 0.005)) * span
    has_label = bool(l_col) and l_col in data
    extents = []
    for _, r in data.iterrows():
        a, b = max(float(r[a_col]) - 1, x0), min(float(r[b_col]), x1)
        w = text_span(ax, str(r[l_col]), size, em, span) + pad if has_label and str(r[l_col]) not in ("", "nan") else 0.0
        extents.append((a, b + w))
    rows = pack_rows(extents, float(params.get("row_gap_frac", 0.01)) * span, int(params.get("max_rows", 3)))
    data["row"] = rows
    n_rows = max(rows) + 1 if rows else 1

    colors = params.get("kind_colors", {})
    brackets = set(params.get("bracket_kinds", []))
    opens = set(params.get("open_kinds", []))
    bh = float(params.get("bar_height", 0.45))
    point_w = float(params.get("point_frac", 0.002)) * span
    for _, r in data.iterrows():
        y = n_rows - 1 - r["row"] + 0.5
        kind = str(r[k_col])
        c = colors.get(kind, params.get("default_color", "#6b7280"))
        a, b = max(float(r[a_col]) - 1, x0), min(float(r[b_col]), x1)
        if b - a < point_w:
            ax.plot([(a + b) / 2], [y], linestyle="none", marker="v", color=c,
                    markersize=float(params.get("point_size", 4.0)), markeredgewidth=float(params.get("point_edge_width", 0.0)))
        elif kind in brackets and kind in opens:
            ax.plot([a, b], [y, y], color=c, linewidth=float(params.get("bracket_width", 0.8)))
        elif kind in brackets:
            ax.plot([a, a, b, b], [y + bh / 2, y, y, y + bh / 2], color=c,
                    linewidth=float(params.get("bracket_width", 0.8)))
        else:
            ax.add_patch(Rectangle((a, y - bh / 2), b - a, bh, facecolor=c, edgecolor="none",
                                   alpha=float(params.get("bar_alpha", 0.85))))
        if kind in opens and b - a >= point_w:
            ext = float(params.get("open_extend_frac", 0.04)) * span
            for lo_, hi_ in ((max(a - ext, x0), a), (b, min(b + ext, x1))):
                if hi_ > lo_:
                    ax.plot([lo_, hi_], [y, y], color=c, linestyle=params.get("open_style", ":"),
                            linewidth=float(params.get("bracket_width", 0.8)))
        if has_label and str(r[l_col]) not in ("", "nan"):
            ax.text(b + pad, y, str(r[l_col]), ha="left", va="center", fontsize=size,
                    color=params.get("text_color", "#111827"))

    ax.set_xlim(x0, x1)
    ax.set_ylim(0, n_rows)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ylabel = text_param(params, "labels_ylabel", None)
    if ylabel:
        a_sz = params.get("axes_label_size")
        ax.set_ylabel(ylabel, **({} if a_sz is None else {"fontsize": a_sz}))
    if params.get("show_legend", True) and len(data):
        order = params.get("kind_order") or list(dict.fromkeys(data[k_col].astype(str)))
        shown = [k for k in order if k in set(data[k_col].astype(str))]
        names = params.get("kind_labels", {})
        handles = []
        for k in shown:
            c = colors.get(k, params.get("default_color", "#6b7280"))
            handles.append(Line2D([], [], color=c, linewidth=float(params.get("bracket_width", 0.8)), label=names.get(k, k))
                           if k in brackets else Patch(facecolor=c, label=names.get(k, k)))
        fs = params.get("legend_fontsize", size)
        ax.legend(handles=handles, loc=params.get("legend_loc", "upper left"),
                  bbox_to_anchor=tuple(params.get("legend_anchor", [1.0, 1.0])),
                  frameon=bool(params.get("legend_frameon", False)), fontsize=fs)
    return data
