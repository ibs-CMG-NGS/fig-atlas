"""Stacked share bars: one horizontal bar per group, split into categories.

Each bar is 100% of its group (e.g. the gene pairs that are DEGs in at least
one species) and is divided into category shares; the group's total is printed
beside the bar. All styling from ``params``.
"""
from __future__ import annotations

import pandas as pd

from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("stacked_share_hbar", params=[
    # [Groups and categories]
    Param("group_order", list, None, role="Bar order top to bottom (default: the rows of counts)"),
    Param("category_order", list, None, role="Segment order left to right (default: the columns of counts)"),
    Param("group_labels", dict, {}, open_keys=True, role="Display label per group (bar)"),
    Param("colors", dict, {}, open_keys=True, unit="hex color per category", role="Segment colour per category"),
    # [Bars]
    Param("bar_height", float, 0.7, unit="data units (rows are 1 apart)", range=(0, 1), role="Bar thickness"),
    Param("edgecolor", "color", "white", unit="color", role="Line between segments"),
    Param("edgewidth", float, 0.4, unit="pt", range=(0, None), role="Width of the line between segments"),
    Param("spine_width", float, 0.6, unit="pt", range=(0, None), role="Axis line width"),
    # [Percent labels inside segments]
    Param("show_pct", bool, True, role="Print each segment's share inside it"),
    Param("pct_min", float, 8.0, unit="% share", role="Smallest share that gets a label", tune="raise if labels crowd narrow segments"),
    Param("pct_fmt", str, "{:.0f}%", role="Python format of the share label"),
    Param("pct_fontsize", float, 5.0, unit="pt", range=(0, None), role="Share label size"),
    Param("dark_categories", list, [], role="Categories (dark fills) whose labels use pct_color_dark"),
    Param("pct_color_dark", "color", "white", unit="color", role="Label colour on dark segments"),
    Param("pct_color_light", "color", "#111827", unit="hex color", role="Label colour on light segments"),
    # [Totals right of the bars]
    Param("show_total", bool, True, role="Print each bar's total at its right end"),
    Param("total_fmt", str, "n = {:,}", role="Python format of the total"),
    Param("total_fontsize", float, 5.5, unit="pt", range=(0, None), role="Total label size"),
    Param("total_pad", float, 0.01, unit="fraction of the 100% width", role="Gap between bar end and total"),
    # [Axes]
    Param("xlabel", str, "Share (%)", role="x-axis title"),
    Param("axes_label_size", float, 6.5, unit="pt", role="Axis title font size"),
    Param("tick_label_size", float, 5.5, unit="pt", role="Tick and group label font size"),
    # [Legend]
    Param("legend", bool, True, role="Show the category legend"),
    Param("legend_labels", dict, {}, open_keys=True, role="Legend text per category"),
    Param("legend_ncol", int, 2, unit="columns", range=(1, None), role="Legend columns"),
    Param("legend_fontsize", float, 5.5, unit="pt", role="Legend text size"),
    Param("legend_loc", str, "upper center", role="Legend anchor point (matplotlib loc)"),
    Param("legend_anchor", list, [0.5, -0.3], unit="axes fraction (x, y)", role="Where legend_loc is placed",
          tune="lower y if the legend overlaps the x-axis title"),
])


@uses_schema(SCHEMA)
def render_stacked_share_hbar(ax, counts: pd.DataFrame, params: dict):
    """``counts``: rows = groups (top to bottom in ``group_order``), columns =
    categories (left to right in ``category_order``), values = counts.

    params: group_order, category_order, colors, group_labels (group -> label),
      bar_height (0.7), edgecolor ('white'), edgewidth (0.4),
      show_pct (True), pct_min (8.0: smallest share labelled inside), pct_fmt ('{:.0f}%'),
      pct_fontsize (5.0), pct_color_dark ('white'), pct_color_light ('#111827'),
      dark_categories (categories whose labels use pct_color_dark),
      show_total (True), total_fmt ('n = {:,}'), total_fontsize (5.5), total_pad (0.01),
      xlabel ('Share (%)'), axes_label_size (6.5), tick_label_size (5.5),
      legend (True), legend_labels (category -> label), legend_ncol (2),
      legend_fontsize (5.5), legend_loc ('upper center'), legend_anchor ([0.5, -0.3]),
      spine_width (0.6)
    """
    groups = params.get("group_order") or list(counts.index)
    cats = params.get("category_order") or list(counts.columns)
    c = counts.reindex(index=groups, columns=cats).fillna(0)
    tot = c.sum(axis=1)
    share = c.div(tot.where(tot > 0, 1), axis=0) * 100
    colors = params.get("colors", {})
    h = float(params.get("bar_height", 0.7))
    dark = set(params.get("dark_categories", []))
    pct_min = float(params.get("pct_min", 8.0))
    leg_lab = params.get("legend_labels", {})
    for gi, g in enumerate(groups):
        left = 0.0
        for cat in cats:
            w = float(share.at[g, cat])
            ax.barh(gi, w, left=left, height=h, color=colors.get(cat, "#9ca3af"),
                    edgecolor=params.get("edgecolor", "white"), linewidth=float(params.get("edgewidth", 0.4)),
                    label=leg_lab.get(cat, cat) if gi == 0 else None)
            if params.get("show_pct", True) and w >= pct_min:
                ax.text(left + w / 2, gi, params.get("pct_fmt", "{:.0f}%").format(w), ha="center", va="center",
                        fontsize=float(params.get("pct_fontsize", 5.0)),
                        color=params.get("pct_color_dark", "white") if cat in dark else params.get("pct_color_light", "#111827"))
            left += w
        if params.get("show_total", True):
            ax.text(100 * (1 + float(params.get("total_pad", 0.01))), gi,
                    params.get("total_fmt", "n = {:,}").format(int(tot[g])), ha="left", va="center",
                    fontsize=float(params.get("total_fontsize", 5.5)))
    lab = params.get("group_labels", {})
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([lab.get(g, g) for g in groups], fontsize=float(params.get("tick_label_size", 5.5)))
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel(params.get("xlabel", "Share (%)"), fontsize=float(params.get("axes_label_size", 6.5)))
    ax.tick_params(axis="x", labelsize=float(params.get("tick_label_size", 5.5)), length=2)
    ax.tick_params(axis="y", length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_linewidth(float(params.get("spine_width", 0.6)))
    if params.get("legend", True):
        ax.legend(loc=params.get("legend_loc", "upper center"), bbox_to_anchor=tuple(params.get("legend_anchor", [0.5, -0.3])),
                  ncol=int(params.get("legend_ncol", 2)), fontsize=float(params.get("legend_fontsize", 5.5)),
                  frameon=False, handlelength=1.0, columnspacing=0.8, handletextpad=0.4)
    return ax
