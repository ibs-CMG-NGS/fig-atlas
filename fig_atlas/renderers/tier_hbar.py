"""Tier-count horizontal bar chart.

Synthesized (Case C) from final_target_summary_figure panel B: one horizontal
bar per tier showing how many target genes it contains, colored by tier. All
visual attributes come from ``params``.
"""

from __future__ import annotations

import pandas as pd

from ..params import text_param
from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("tier_hbar", params=[
    Param("category_col", str, "category", role="Column of df with the bar categories (tiers)"),
    Param("count_col", str, "count", role="Column of df with the bar lengths"),
    Param("order", list, None, role="Bar order top to bottom (default: order of first appearance)"),
    Param("label_rename_map", dict, {}, open_keys=True, role="Display label per category"),
    Param("bar_colors", dict, {}, open_keys=True, unit="hex color per category", role="Colour per category"),
    Param("default_bar_color", "color", "#3b73b9", unit="hex color", role="Colour of categories without one"),
    Param("show_value_labels", bool, True, role="Print each bar's count at its end"),
    Param("value_label_fontsize", float, CODE_DEFAULT, unit="pt", role="Count label size (default axes_label_size)"),
    Param("value_label_offset", float, 0.015, unit="fraction of x range", role="Gap between bar end and its count",
          tune="raise if labels touch the bars"),
    Param("xlim", list, None, unit="data coords [min, max]", role="x range; only the max is used"),
    Param("xlim_headroom", float, 1.12, unit="x the largest count", range=(1, None),
          role="x range when xlim is unset", tune="raise if value labels clip at the right"),
    Param("xlabel", str, "n genes", role="x-axis title"),
    Param("labels_title", str, "Final target genes by tier", role="Panel title"),
    Param("title_size", float, 13, unit="pt", role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_tier_hbar(ax, df, params):
    """Draw a horizontal count bar chart onto ``ax``.

    ``df`` is long-format with ``category`` (tier label) and ``count`` columns,
    ordered as given by ``order``.
    params: category_col('category'), count_col('count'), order(list),
            label_rename_map, bar_colors (dict category -> color),
            default_bar_color, show_value_labels, value_label_fontsize,
            value_label_offset, xlim_headroom (x range = max count x this
            when xlim is unset, leaving room for value labels), xlabel (str), xlim, labels_title,
            axes_label_size, tick_label_size, title_size
    """
    title_sz = params.get("title_size", 13)
    a_sz = params.get("axes_label_size", 11)
    t_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    cat_col = params.get("category_col", "category")
    cnt_col = params.get("count_col", "count")
    order = params.get("order") or list(pd.unique(df[cat_col]))
    counts = {c: int(df[df[cat_col] == c][cnt_col].iloc[0]) for c in order}

    colors = params.get("bar_colors", {})
    default_color = params.get("default_bar_color", "#3b73b9")
    bar_colors = [colors.get(c, default_color) for c in order]

    y = list(range(len(order)))
    vals = [counts[c] for c in order]
    ax.barh(y, vals, color=bar_colors, edgecolor="none", zorder=2)
    ax.set_yticks(y)
    rename = params.get("label_rename_map", {})
    ax.set_yticklabels([rename.get(c, c) for c in order], fontsize=t_sz)
    ax.invert_yaxis()
    ax.tick_params(axis="x", labelsize=t_sz)
    ax.grid(True, linestyle="-", color="#e8e8e8", alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    if params.get("show_value_labels", True):
        fs = float(params.get("value_label_fontsize", a_sz))
        off = float(params.get("value_label_offset", 0.015))
        xmax = params.get("xlim")
        maxv = max(vals) if vals else 1
        lim = float(xmax[1]) if xmax else maxv * float(params.get("xlim_headroom", 1.12))
        ax.set_xlim(0, lim)
        for yi, v in zip(y, vals):
            ax.text(v + off * lim, yi, f"{v:,}", va="center", fontsize=fs, color="black")

    ax.set_xlabel(text_param(params, "xlabel", "n genes"),
                  fontsize=a_sz, fontweight="bold")
    title = text_param(params, "labels_title", "Final target genes by tier")
    ax.set_title(title, fontsize=title_sz, fontweight="bold")

    return pd.DataFrame({"category": order, "count": vals})
