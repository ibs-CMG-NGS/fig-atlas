"""Grouped (multi-series) horizontal bar chart.

One category per row, N side-by-side bars per row (e.g. a gene count per
concordance class for the same GO term) instead of a single stacked or
single-series bar. All visual attributes come from ``params``.
"""

from __future__ import annotations

import textwrap

import pandas as pd

from ..params import text_param
from ..schema import CODE_DEFAULT, Param, Schema, typography, uses_schema

SCHEMA = Schema("grouped_hbar", params=[
    *typography(title_size=13, axes_label_size=11, tick_label_size=8, legend_fontsize=CODE_DEFAULT),
    Param("category_col", str, "category", role="Column of df holding the row categories (y axis)"),
    Param("series", list, None, role="Columns of df drawn as side-by-side bars, in this order (required)"),
    Param("series_labels", dict, {}, open_keys=True, role="Legend label per series column", tune="map column -> text"),
    Param("series_colors", dict, {}, open_keys=True, unit="hex color per series",
          role="Bar colour per series column; unset series cycle indigo / amber / teal"),
    Param("category_order", list, None, role="Row order top to bottom; default: order of first appearance"),
    Param("bar_height", float, 0.36, unit="data units (row spacing = 1)", range=(0, 1),
          role="Height of each bar; a group of n bars spans n x this", tune="raise for thicker bars, lower for gaps"),
    Param("ylabel_wrap_width", int, 0, unit="characters", range=(0, None),
          role="Wrap row labels at this width (0 = no wrap)", tune="lower if row labels push the plot right"),
    Param("xlim", list, None, unit="data coords [min, max]",
          role="x-axis range; the axis starts at 0 unless min is negative (bars below zero)",
          tune="default: 1.15 x the largest bar (and the most negative one, if any)"),
    Param("show_value_labels", bool, True, role="Print each bar's count at its end"),
    Param("value_label_fontsize", float, CODE_DEFAULT, unit="pt", role="Count label size (default: tick label size)",
          tune="lower if labels overlap the next bar"),
    Param("value_label_offset", float, 0.012, unit="fraction of x range", role="Gap between bar end and its count",
          tune="raise if labels touch the bars"),
    Param("xlabel", str, "count", role="x-axis title"),
    Param("labels_title", str, "", role="Panel title (empty = none)"),
    Param("show_legend", bool, True, role="Show the series legend"),
    Param("legend_loc", str, "lower right", role="Legend anchor (matplotlib loc)", tune="move it off the bars"),
])


@uses_schema(SCHEMA)
def render_grouped_hbar(ax, df, params):
    """Draw a grouped horizontal bar chart onto ``ax``.

    ``df`` is wide-format: one row per category, with one numeric column per
    series (see ``series``).
    params: category_col('category'), series(list of column names, required),
            series_labels(dict col -> legend label), series_colors(dict col -> color),
            category_order(list), bar_height(0.36), show_value_labels(True),
            value_label_fontsize, value_label_offset, xlabel, xlim,
            ylabel_wrap_width(0 = no wrap), legend_loc, legend_fontsize,
            show_legend(True), labels_title, axes_label_size, tick_label_size,
            title_size
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
    series = params.get("series") or []
    if not series:
        ax.text(0.5, 0.5, "No series specified", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    order = params.get("category_order") or list(pd.unique(df[cat_col]))
    df = df.set_index(cat_col).loc[order].reset_index()

    n_series = len(series)
    bar_h = float(params.get("bar_height", 0.36))
    series_colors = params.get("series_colors", {})
    default_colors = ["#4F46E5", "#D97706", "#0D9488"]
    series_labels = params.get("series_labels", {})

    y_base = list(range(len(order)))
    # Center the group of n_series bars on each integer row position.
    offsets = [(i - (n_series - 1) / 2.0) * bar_h for i in range(n_series)]

    all_vals = []
    for s_idx, col in enumerate(series):
        vals = df[col].tolist()
        all_vals.extend(vals)
        ys = [yb + offsets[s_idx] for yb in y_base]
        color = series_colors.get(col, default_colors[s_idx % len(default_colors)])
        label = series_labels.get(col, col)
        ax.barh(ys, vals, height=bar_h * 0.92, color=color, edgecolor="none",
                zorder=2, label=label)

    ax.set_yticks(y_base)
    wrap_w = int(params.get("ylabel_wrap_width", 0))
    labels = [str(c) for c in order]
    if wrap_w > 0:
        labels = [textwrap.fill(lbl, width=wrap_w) for lbl in labels]
    ax.set_yticklabels(labels, fontsize=t_sz)
    ax.invert_yaxis()
    ax.tick_params(axis="x", labelsize=t_sz)
    ax.grid(True, axis="x", linestyle="-", color="#e8e8e8", alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    xlim = params.get("xlim")
    maxv = max(all_vals) if all_vals else 1
    minv = min(all_vals) if all_vals else 0
    lim = float(xlim[1]) if xlim else maxv * 1.15
    lo = min(0.0, float(xlim[0])) if xlim else min(0.0, minv * 1.15)
    ax.set_xlim(lo, lim)
    if lo < 0:
        ax.axvline(0, color="#111827", linewidth=0.6, zorder=3)

    if params.get("show_value_labels", True):
        fs = float(params.get("value_label_fontsize", t_sz))
        off = float(params.get("value_label_offset", 0.012)) * (lim - lo)
        for s_idx, col in enumerate(series):
            ys = [yb + offsets[s_idx] for yb in y_base]
            for yi, v in zip(ys, df[col].tolist()):
                ax.text(v + off if v >= 0 else v - off, yi, f"{int(v):,}", va="center",
                        ha="left" if v >= 0 else "right", fontsize=fs, color="black")

    ax.set_xlabel(text_param(params, "xlabel", "count"), fontsize=a_sz, fontweight="bold")
    title = text_param(params, "labels_title", "")
    if title:
        ax.set_title(title, fontsize=title_sz, fontweight="bold")

    if params.get("show_legend", True):
        ax.legend(loc=params.get("legend_loc", "lower right"),
                   fontsize=float(params.get("legend_fontsize", t_sz)),
                   frameon=True, facecolor="white", edgecolor="#cccccc")

    return df
