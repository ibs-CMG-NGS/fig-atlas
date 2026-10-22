"""segment_array: an ordered row of linear segments -- a transgene array between
its host flanks, or a construct map -- drawn left to right in row order.

Each row is one segment: its length sets its width (linear, square-root or log
scale, with a minimum width so short pieces stay visible), its kind sets the
colour, and a strand of "+" / "-" turns it into an arrow pointing right / left.
A segment's name (``inner_label_col``) is written inside it, in a dark or
light colour by the fill, or under it when it does not fit. Consecutive rows
sharing a ``span_col`` value get one arrow above them, pointing along their
strand, with ``span_label_col`` (e.g. source coordinates) over it -- the R6
transgene figure style.
Kinds listed in ``gap_kinds`` are drawn as a thin line (unmapped linkers),
kinds in ``flank_kinds`` as fixed-width host flanks with their label at the
outer end. Consecutive rows sharing a ``group_col`` value get one bracket and
label above them (e.g. one transgene copy split into pieces).

Data: one row per segment, in drawing order, with the columns named by
length_col and kind_col (label_col, sublabel_col, strand_col, group_col optional).
Returns the rows with their drawn extent (x0, x1 in axes data units, y the bar
centre) so a script can attach connectors; ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.patches import Polygon

from fig_atlas.params import text_param
from fig_atlas.schema import Param, Schema, typography, uses_schema

SCHEMA = Schema("segment_array", params=[
    # [Data]
    Param("length_col", str, "length_bp", role="Column with each segment's length (bp)"),
    Param("kind_col", str, "kind", role="Column with each segment's kind (sets its colour)"),
    Param("label_col", str, "label", role="Column with the text above a segment (none: no labels)"),
    Param("sublabel_col", str, None, role="Column with the text below a segment, e.g. source coordinates"),
    Param("strand_col", str, "strand", role="Column with + / - (an arrow pointing right / left); other values: a box"),
    Param("group_col", str, None, role="Column grouping consecutive segments under one bracket and label"),
    Param("inner_label_col", str, None, role="Column with the name written inside a segment (under it if it does not fit)"),
    Param("span_col", str, None, role="Column grouping consecutive segments under one direction arrow"),
    Param("span_label_col", str, None, role="Column with the text over a span arrow, e.g. source coordinates"),
    Param("span_strand_col", str, None, role="Column with + / - for the span arrow direction (default: strand_col)"),
    # [Widths]
    Param("scale", ("linear", "sqrt", "log"), "linear", role="How length maps to width",
          tune="sqrt or log when one segment is far longer than the rest (e.g. a BAC next to a linker)"),
    Param("min_frac", float, 0.012, unit="fraction of the row width", range=(0, 1),
          role="Smallest width a segment is drawn at", tune="raise if short pieces disappear"),
    Param("flank_kinds", list, ["host"], role="Kinds drawn as host flanks at a fixed width (length ignored)"),
    Param("flank_frac", float, 0.12, unit="fraction of the row width", range=(0, 1),
          role="Width of each host flank"),
    Param("gap_kinds", list, ["copy_gap"], role="Kinds drawn as a thin line instead of a box (unmapped linkers)"),
    Param("x_pad_frac", float, 0.01, unit="fraction of the row width", range=(0, None),
          role="Blank margin left and right of the row"),
    # [Marks]
    Param("kind_colors", dict, {}, open_keys=True, unit="hex color", role="Fill colour per kind"),
    Param("default_color", "color", "#9ca3af", unit="hex color", role="Fill of kinds without a colour"),
    Param("edge_color", "color", "#1f2937", unit="hex color", role="Segment outline colour"),
    Param("edge_width", float, 0.4, unit="pt", range=(0, None), role="Segment outline width (0: none)"),
    Param("bar_height", float, 0.28, unit="axes data units (row is 0-1 high)", range=(0, 1),
          role="Height of a segment box", tune="raise for a bolder row"),
    Param("bar_y", float, 0.45, unit="axes data units (0-1)", range=(0, 1), role="Height of the row centre"),
    Param("arrow_head_frac", float, 0.3, unit="fraction of the segment width", range=(0, 1),
          role="Length of an arrow head on stranded segments"),
    Param("arrow_head_max_frac", float, 0.025, unit="fraction of the row width", range=(0, 1),
          role="Longest an arrow head may be", tune="lower for blunter arrows on long segments"),
    Param("gap_color", "color", "#6b7280", unit="hex color", role="Colour of gap lines"),
    Param("gap_width", float, 0.8, unit="pt", range=(0, None), role="Width of gap lines"),
    Param("gap_style", str, ":", role="Line style of gap lines (matplotlib)"),
    Param("separator_width", float, 0.6, unit="pt", range=(0, None),
          role="Width of the tick drawn between adjacent segments (0: none)"),
    Param("separator_color", "color", "#111827", unit="hex color", role="Colour of the ticks between segments"),
    # [Names inside segments]
    Param("inner_label_size", float, 6.0, unit="pt", range=(0, None), role="Size of the names inside segments"),
    Param("inner_label_weight", str, "normal", role="Font weight of the names inside segments"),
    Param("inner_text_dark", "color", "#111827", unit="hex color", role="Name colour on light fills"),
    Param("inner_text_light", "color", "#ffffff", unit="hex color", role="Name colour on dark fills"),
    Param("inner_luminance_cut", float, 0.5, unit="relative luminance [0-1]", range=(0, 1),
          role="Fills darker than this get the light name colour"),
    Param("inner_label_margin", float, 0.9, unit="fraction of the segment width", range=(0, 1),
          role="Share of a segment's width a name may use before it moves under the segment"),
    Param("inner_fallback", ("above", "below"), "below",
          role="Where a name too wide for its segment goes: above the bar, or under it (after any label there)"),
    Param("label_char_em", float, 0.6, unit="em per character", range=(0, None),
          role="Estimated text width per character (fit test only)", tune="raise if names spill over their segment"),
    # [Span arrows above segments]
    Param("span_pad", float, 0.07, unit="axes data units", range=(0, None), role="Gap between the bar and the span arrows"),
    Param("span_inset_frac", float, 0.003, unit="fraction of the row width", range=(0, None),
          role="Gap left at each end of a span arrow so neighbouring arrows do not touch"),
    Param("span_color", "color", "#111827", unit="hex color", role="Span arrow colour"),
    Param("span_line_width", float, 0.6, unit="pt", range=(0, None), role="Span arrow line width"),
    Param("span_head", float, 5.0, unit="pt", range=(0, None), role="Span arrow head size"),
    Param("span_label_size", float, 5.0, unit="pt", range=(0, None), role="Size of the text over span arrows"),
    Param("span_label_pad", float, 0.02, unit="axes data units", range=(0, None), role="Gap between a span arrow and its text"),
    # [Labels]
    Param("label_size", float, 6.0, unit="pt", range=(0, None), role="Size of the labels above segments"),
    Param("label_pad", float, 0.04, unit="axes data units", range=(0, None), role="Gap between a bar and its label"),
    Param("label_min_frac", float, 0.0, unit="fraction of the row width", range=(0, 1),
          role="Segments narrower than this get no label above", tune="raise to thin out crowded labels"),
    Param("sublabel_size", float, 5.0, unit="pt", range=(0, None), role="Size of the labels below segments"),
    Param("sublabel_rotation", float, 0.0, unit="degrees", role="Rotation of the labels below segments"),
    Param("sublabel_stagger", float, 0.0, unit="axes data units", range=(0, None),
          role="Drop every second label below the bar by this much (0: one line)",
          tune="raise when labels of neighbouring narrow segments touch"),
    Param("sublabel_min_frac", float, 0.0, unit="fraction of the row width", range=(0, 1),
          role="Segments narrower than this get no label below"),
    Param("flank_label_size", float, 6.0, unit="pt", range=(0, None), role="Size of the host flank labels"),
    Param("flank_label_style", str, "italic", role="Font style of the host flank labels"),
    Param("flank_label_pad", float, 0.04, unit="axes data units", range=(0, None),
          role="Gap between a host flank and its label"),
    Param("group_bracket", bool, True, role="Draw a bracket over each group"),
    Param("group_bracket_pad", float, 0.06, unit="axes data units", range=(0, None),
          role="Gap between the bars and a group bracket"),
    Param("group_bracket_height", float, 0.05, unit="axes data units", range=(0, None),
          role="Height of the bracket ends"),
    Param("group_bracket_width", float, 0.5, unit="pt", range=(0, None), role="Bracket line width"),
    Param("group_bracket_color", "color", "#374151", unit="hex color", role="Bracket colour"),
    Param("group_label_size", float, 6.0, unit="pt", range=(0, None), role="Size of the group labels"),
    Param("group_label_weight", str, "bold", role="Font weight of the group labels"),
    Param("text_color", "color", "#111827", unit="hex color", role="Colour of all labels"),
    Param("labels_title", str, None, role="Row title, at the top left (none: no title)"),
    *typography(title_size=8.0),
    Param("title_loc", str, "left", role="Title alignment (matplotlib loc)"),
    Param("title_pad", float, 2.0, unit="pt", range=(0, None), role="Gap between the title and the row"),
])


def _widths(lengths: np.ndarray, flank: np.ndarray, params) -> np.ndarray:
    """Display width per segment as a fraction of the row (sums to 1)."""
    scale = params.get("scale", "linear")
    v = np.clip(lengths.astype(float), 1.0, None)
    v = {"linear": v, "sqrt": np.sqrt(v), "log": np.log10(v + 1.0)}[scale]
    flank_frac = float(params.get("flank_frac", 0.12))
    body = 1.0 - flank_frac * flank.sum()
    w = np.where(flank, 0.0, v)
    w = w / w.sum() * body if w.sum() > 0 else w
    lo = float(params.get("min_frac", 0.012))
    small = (~flank) & (w < lo)
    if small.any() and (~flank & ~small).any():           # lift short pieces, take it from the long ones
        need = (lo - w[small]).sum()
        big = (~flank) & ~small
        w[big] -= need * w[big] / w[big].sum()
        w[small] = lo
    return np.where(flank, flank_frac, w)


@uses_schema(SCHEMA)
def render_segment_array(ax, df, params):
    """Draw the segments onto ``ax``; returns them with their drawn extent."""
    len_col, kind_col = params.get("length_col", "length_bp"), params.get("kind_col", "kind")
    lab_col, sub_col = params.get("label_col", "label"), params.get("sublabel_col")
    strand_col, grp_col = params.get("strand_col", "strand"), params.get("group_col")
    data = df.reset_index(drop=True).copy()
    kinds = data[kind_col].astype(str)
    flank = kinds.isin(params.get("flank_kinds", ["host"])).to_numpy()
    gaps = kinds.isin(params.get("gap_kinds", ["copy_gap"])).to_numpy()
    lengths = pd.to_numeric(data[len_col], errors="coerce").fillna(0).to_numpy()
    w = _widths(lengths, flank, params)
    x1 = np.cumsum(w)
    x0 = x1 - w
    data["x0"], data["x1"] = x0, x1

    y, h = float(params.get("bar_y", 0.45)), float(params.get("bar_height", 0.28))
    data["y"] = y
    colors = params.get("kind_colors", {})
    edge, ew = params.get("edge_color", "#1f2937"), float(params.get("edge_width", 0.4))
    head_frac = float(params.get("arrow_head_frac", 0.3))
    head_max = float(params.get("arrow_head_max_frac", 0.025))
    txt = params.get("text_color", "#111827")
    for i, row in data.iterrows():
        a, b = x0[i], x1[i]
        if gaps[i]:
            ax.plot([a, b], [y, y], color=params.get("gap_color", "#6b7280"),
                    linewidth=float(params.get("gap_width", 0.8)), linestyle=params.get("gap_style", ":"))
            continue
        fill = colors.get(kinds[i], params.get("default_color", "#9ca3af"))
        strand = str(row[strand_col]) if strand_col and strand_col in data else ""
        head = min((b - a) * head_frac, head_max) if strand in "+-" and strand and not flank[i] else 0.0
        lo_y, hi_y = y - h / 2, y + h / 2
        if strand == "+" and head:
            pts = [(a, lo_y), (b - head, lo_y), (b, y), (b - head, hi_y), (a, hi_y)]
        elif strand == "-" and head:
            pts = [(b, lo_y), (a + head, lo_y), (a, y), (a + head, hi_y), (b, hi_y)]
        else:
            pts = [(a, lo_y), (b, lo_y), (b, hi_y), (a, hi_y)]
        ax.add_patch(Polygon(pts, closed=True, facecolor=fill, edgecolor=edge if ew else "none", linewidth=ew))

    sep_w = float(params.get("separator_width", 0.6))
    if sep_w:
        for i in range(1, len(data)):
            if not (gaps[i] or gaps[i - 1]):
                ax.plot([x0[i], x0[i]], [y - h / 2, y + h / 2], color=params.get("separator_color", "#111827"),
                        linewidth=sep_w, solid_capstyle="butt")

    # Names inside segments; a name too wide for its segment goes under it instead.
    below = data[sub_col].copy().astype(object) if sub_col and sub_col in data else pd.Series([None] * len(data), dtype=object)
    in_col = params.get("inner_label_col")
    if in_col and in_col in data:
        from matplotlib.colors import to_rgb

        from ._tracks import text_span
        size = float(params.get("inner_label_size", 6.0))
        em = float(params.get("label_char_em", 0.6))
        span = 1 + 2 * float(params.get("x_pad_frac", 0.01))
        for i in np.flatnonzero(~flank & ~gaps):
            name = data.at[i, in_col]
            if pd.isna(name) or str(name) == "":
                continue
            if text_span(ax, str(name), size, em, span) <= w[i] * float(params.get("inner_label_margin", 0.9)):
                r, g_, b_ = to_rgb(colors.get(kinds[i], params.get("default_color", "#9ca3af")))
                lum = 0.2126 * r + 0.7152 * g_ + 0.0722 * b_
                ink = params.get("inner_text_light", "#ffffff") if lum < float(params.get("inner_luminance_cut", 0.5)) \
                    else params.get("inner_text_dark", "#111827")
                ax.text((x0[i] + x1[i]) / 2, y, str(name), ha="center", va="center", color=ink, fontsize=size,
                        fontweight=params.get("inner_label_weight", "normal"))
            elif params.get("inner_fallback", "below") == "above":
                ax.text((x0[i] + x1[i]) / 2, y + h / 2 + float(params.get("label_pad", 0.04)), str(name),
                        ha="center", va="bottom", color=txt, fontsize=size,
                        fontweight=params.get("inner_label_weight", "normal"))
            else:
                below[i] = name if pd.isna(below[i]) else "\n".join([str(below[i]), str(name)])

    # Span arrows: one arrow over consecutive rows sharing a span value, pointing along their strand.
    sp_col = params.get("span_col")
    if sp_col and sp_col in data:
        sl_col = params.get("span_label_col")
        ss_col = params.get("span_strand_col") or strand_col
        ys = y + h / 2 + float(params.get("span_pad", 0.07))
        inset = float(params.get("span_inset_frac", 0.003))
        sv = data[sp_col]
        run = (sv != sv.shift()).cumsum()
        for _, rows in data[sv.notna() & ~flank].groupby(run[sv.notna() & ~flank], sort=False):
            a, b = rows["x0"].min() + inset, rows["x1"].max() - inset
            minus = ss_col in data and str(rows[ss_col].iloc[0]) == "-"
            ax.annotate("", xy=(a if minus else b, ys), xytext=(b if minus else a, ys),
                        arrowprops=dict(arrowstyle="-|>", mutation_scale=float(params.get("span_head", 5.0)),
                                        color=params.get("span_color", "#111827"),
                                        linewidth=float(params.get("span_line_width", 0.6)),
                                        shrinkA=0, shrinkB=0))
            text = rows[sl_col].iloc[0] if sl_col and sl_col in data else None
            if text is not None and not pd.isna(text):
                ax.text((a + b) / 2, ys + float(params.get("span_label_pad", 0.02)), str(text), ha="center",
                        va="bottom", color=txt, fontsize=float(params.get("span_label_size", 5.0)))

    # Host flanks: label at the outer end, below the bar.
    fpad = float(params.get("flank_label_pad", 0.04))
    for i in np.flatnonzero(flank):
        if not lab_col or lab_col not in data or pd.isna(data.at[i, lab_col]):
            continue
        left = i < len(data) / 2
        ax.text(x0[i] if left else x1[i], y + h / 2 + fpad, str(data.at[i, lab_col]),
                ha="left" if left else "right", va="bottom", color=txt,
                fontsize=float(params.get("flank_label_size", 6.0)), style=params.get("flank_label_style", "italic"))

    # Groups: one bracket + label over consecutive rows sharing a value; else a label per segment.
    top = y + h / 2 + float(params.get("label_pad", 0.04))
    grouped = np.zeros(len(data), dtype=bool)
    if grp_col and grp_col in data:
        g = data[grp_col]
        run = (g != g.shift()).cumsum()
        for _, rows in data[g.notna() & ~flank].groupby(run[g.notna() & ~flank], sort=False):
            a, b = rows["x0"].min(), rows["x1"].max()
            grouped[rows.index] = True
            yb = y + h / 2 + float(params.get("group_bracket_pad", 0.06))
            if params.get("group_bracket", True):
                bh = float(params.get("group_bracket_height", 0.05))
                ax.plot([a, a, b, b], [yb, yb + bh, yb + bh, yb],
                        color=params.get("group_bracket_color", "#374151"),
                        linewidth=float(params.get("group_bracket_width", 0.5)))
                yb += bh
            ax.text((a + b) / 2, yb + float(params.get("label_pad", 0.04)), str(rows[grp_col].iloc[0]),
                    ha="center", va="bottom", color=txt, fontsize=float(params.get("group_label_size", 6.0)),
                    fontweight=params.get("group_label_weight", "bold"))
    lab_min = float(params.get("label_min_frac", 0.0))
    if lab_col and lab_col in data:
        for i in np.flatnonzero(~flank & ~grouped):
            if pd.isna(data.at[i, lab_col]) or w[i] < lab_min:
                continue
            ax.text((x0[i] + x1[i]) / 2, top, str(data.at[i, lab_col]), ha="center", va="bottom", color=txt,
                    fontsize=float(params.get("label_size", 6.0)))
    sub_min = float(params.get("sublabel_min_frac", 0.0))
    if below.notna().any():
        rot = float(params.get("sublabel_rotation", 0.0))
        stagger = float(params.get("sublabel_stagger", 0.0))
        n_drawn = 0
        for i in np.flatnonzero(~flank):
            if pd.isna(below[i]) or w[i] < sub_min:
                continue
            drop = stagger * (n_drawn % 2)
            n_drawn += 1
            ax.text((x0[i] + x1[i]) / 2, y - h / 2 - float(params.get("label_pad", 0.04)) - drop,
                    str(below[i]),
                    ha="right" if rot else "center", va="top", rotation=rot, rotation_mode="anchor", color=txt,
                    fontsize=float(params.get("sublabel_size", 5.0)))

    pad = float(params.get("x_pad_frac", 0.01))
    ax.set_xlim(-pad, 1 + pad)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    title = text_param(params, "labels_title", None)
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0), loc=params.get("title_loc", "left"),
                     pad=float(params.get("title_pad", 2.0)))
    return data
