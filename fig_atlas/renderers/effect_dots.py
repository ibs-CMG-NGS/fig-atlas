"""Effect estimates with confidence intervals: one row per item, one dot +
whisker per series (e.g. unadjusted vs adjusted), dodged vertically. Styling
from ``params``."""
from __future__ import annotations

import pandas as pd


from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("effect_dots", params=[
    # [Rows and series]
    Param("item_order", list, None, role="Row order, top to bottom (default: order in the data)"),
    Param("item_labels", dict, {}, open_keys=True, role="Display label per item"),
    Param("series_order", list, None, role="Series order (default: order in the data)"),
    Param("series_colors", dict, {}, open_keys=True, role="Colour per series"),
    Param("series_labels", dict, {}, open_keys=True, role="Legend label per series"),
    Param("dodge", float, 0.18, unit="row units", range=(0, None), role="Vertical offset between series within a row",
          tune="raise if the series' intervals overlap"),
    # [Marks]
    Param("marker_size", float, 16, unit="pt^2 (marker area)", range=(0, None), role="Point estimate marker size"),
    Param("ci_width", float, 0.8, unit="pt", range=(0, None), role="Confidence interval line width"),
    Param("zero_line", bool, True, role="Draw the no-effect line at x = 0"),
    Param("zero_line_color", "color", "#6b7280", unit="hex color", role="No-effect line colour"),
    Param("zero_line_width", float, 0.5, unit="pt", range=(0, None), role="No-effect line width"),
    Param("xlim", list, None, unit="data coords [min, max]", role="x-axis range (default: data)"),
    Param("spine_width", float, 0.6, unit="pt", range=(0, None), role="Axis spine width"),
    # [Legend]
    Param("legend", bool, True, role="Show the series legend"),
    Param("legend_loc", str, "lower right", role="Legend location (matplotlib loc string)"),
    Param("legend_anchor", list, None, unit="axes fraction (x, y)", role="bbox_to_anchor for the legend"),
    Param("legend_ncol", int, 1, unit="columns", range=(1, None), role="Legend columns"),
    Param("legend_fontsize", float, 5.0, unit="pt", range=(0, None), role="Legend font size"),
    # [Labels]
    Param("title", str, None, role="Panel title"),
    Param("xlabel", str, None, role="x-axis title"),
    Param("title_pad", float, 3.0, unit="pt", range=(0, None), role="Gap between title and axes"),
    Param("title_size", float, 6.5, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 6.0, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 5.5, unit="pt", range=(0, None), role="Tick and row label font size"),
])


@uses_schema(SCHEMA)
def render_effect_dots(ax, df: pd.DataFrame, params: dict):
    """``df`` columns: item, series, estimate, ci_low, ci_high.

    params: item_order, item_labels, series_order, series_colors, series_labels,
      dodge (0.18: vertical offset between series, row units), marker_size (16),
      ci_width (0.8), zero_line (True), zero_line_color ('#6b7280'), zero_line_width (0.5),
      xlabel, xlim, axes_label_size (6.0), tick_label_size (5.5),
      legend (True), legend_fontsize (5.0), legend_loc ('lower right'), legend_anchor (None:
      axes-fraction anchor for legend_loc), legend_ncol (1),
      title, title_size (6.5), title_pad (3.0), spine_width (0.6)
    """
    items = params.get("item_order") or list(pd.unique(df["item"]))
    series = params.get("series_order") or list(pd.unique(df["series"]))
    colors, s_lab = params.get("series_colors", {}), params.get("series_labels", {})
    dodge = float(params.get("dodge", 0.18))
    if params.get("zero_line", True):
        ax.axvline(0, color=params.get("zero_line_color", "#6b7280"), lw=float(params.get("zero_line_width", 0.5)), zorder=1)
    for si, s in enumerate(series):
        off = (si - (len(series) - 1) / 2) * dodge
        d = df[df["series"] == s].set_index("item").reindex(items)
        ys = [i + off for i in range(len(items))]
        c = colors.get(s, "#374151")
        ax.hlines(ys, d["ci_low"], d["ci_high"], color=c, lw=float(params.get("ci_width", 0.8)), zorder=2)
        ax.scatter(d["estimate"], ys, s=float(params.get("marker_size", 16)), color=c, zorder=3, label=s_lab.get(s, s))
    lab = params.get("item_labels", {})
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([lab.get(i, i) for i in items], fontsize=float(params.get("tick_label_size", 5.5)))
    ax.invert_yaxis()
    if params.get("xlim") is not None:
        ax.set_xlim(*params["xlim"])
    if params.get("xlabel"):
        ax.set_xlabel(params["xlabel"], fontsize=float(params.get("axes_label_size", 6.0)))
    ax.tick_params(axis="x", labelsize=float(params.get("tick_label_size", 5.5)), length=2)
    ax.tick_params(axis="y", length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(float(params.get("spine_width", 0.6)))
    if params.get("legend", True):
        anchor = params.get("legend_anchor")
        ax.legend(fontsize=float(params.get("legend_fontsize", 5.0)), loc=params.get("legend_loc", "lower right"),
                  bbox_to_anchor=tuple(anchor) if anchor else None, ncol=int(params.get("legend_ncol", 1)),
                  frameon=False, handletextpad=0.2)
    if params.get("title"):
        ax.set_title(params["title"], fontsize=float(params.get("title_size", 6.5)), fontweight="bold",
                     pad=float(params.get("title_pad", 3.0)))
    return ax
