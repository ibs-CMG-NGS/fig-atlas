"""Grouped scatter with a fitted line: one point per item (e.g. per library),
coloured by group, with a least-squares line and Pearson r. Styling from ``params``."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr


from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("group_scatter", params=[
    # [Groups and points]
    Param("group_order", list, None, role="Group draw order (default: order in the data)"),
    Param("group_colors", dict, {}, open_keys=True, role="Point colour per group (unlisted groups are grey)"),
    Param("group_labels", dict, {}, open_keys=True, role="Legend label per group"),
    Param("marker_size", float, 14, unit="pt^2 (marker area)", range=(0, None), role="Point size"),
    Param("edgecolor", "color", "white", unit="color", role="Point outline colour"),
    Param("edgewidth", float, 0.4, unit="pt", range=(0, None), role="Point outline width"),
    Param("point_labels", bool, None, role="Write the label column next to each point"),
    Param("point_label_offset", list, [2, 1], unit="points (dx, dy)", role="Offset of the point labels"),
    Param("point_label_fontsize", float, 4.6, unit="pt", range=(0, None), role="Point label size"),
    # [Fit and correlation]
    Param("fit", bool, True, role="Draw a least-squares line over all points"),
    Param("fit_color", "color", "#374151", unit="hex color", role="Fit line colour"),
    Param("fit_width", float, 0.7, unit="pt", range=(0, None), role="Fit line width"),
    Param("fit_style", str, "-", role="Fit line style (matplotlib linestyle)"),
    Param("annotate_r", bool, True, role="Print the Pearson r and P"),
    Param("r_fmt", str, "r = {r:+.2f}, P = {p:.1g}", role="Format of the r text; fields r, p, n"),
    Param("r_xy", list, [0.03, 0.97], unit="axes fraction (x, y)", role="Top-left corner of the r text"),
    Param("r_fontsize", float, 5.5, unit="pt", range=(0, None), role="r text size"),
    # [Axes]
    Param("xlim", list, None, unit="data coords [min, max]", role="x-axis range (default: data)"),
    Param("ylim", list, None, unit="data coords [min, max]", role="y-axis range (default: data)"),
    Param("zero_line", bool, True, role="Draw the y = 0 line"),
    Param("zero_line_color", "color", "#9ca3af", unit="hex color", role="Zero line colour"),
    Param("zero_line_width", float, 0.4, unit="pt", range=(0, None), role="Zero line width"),
    Param("spine_width", float, 0.6, unit="pt", range=(0, None), role="Axis spine width"),
    # [Legend]
    Param("legend", bool, None, role="Show the group legend"),
    Param("legend_loc", str, "lower right", role="Legend location (matplotlib loc string)"),
    Param("legend_fontsize", float, 5.0, unit="pt", range=(0, None), role="Legend font size"),
    # [Labels]
    Param("title", str, None, role="Panel title"),
    Param("xlabel", str, None, role="x-axis title"),
    Param("ylabel", str, None, role="y-axis title"),
    Param("title_pad", float, 3.0, unit="pt", range=(0, None), role="Gap between title and axes"),
    Param("title_size", float, 6.5, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 6.0, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 5.5, unit="pt", range=(0, None), role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_group_scatter(ax, df: pd.DataFrame, params: dict):
    """``df`` columns: x, y, group, and optional label (text beside the point).

    params: group_order, group_colors, group_labels, marker_size (14), edgecolor ('white'),
      edgewidth (0.4), fit (True), fit_color ('#374151'), fit_width (0.7), fit_style ('-'),
      zero_line (True), zero_line_color ('#9ca3af'), zero_line_width (0.4),
      annotate_r (True), r_fmt ('r = {r:+.2f}, P = {p:.1g}'), r_xy ([0.03, 0.97]),
      r_fontsize (5.5), point_labels (False), point_label_fontsize (4.6),
      point_label_offset ([2, 1] points), xlabel, ylabel, xlim, ylim,
      axes_label_size (6.0), tick_label_size (5.5), title, title_size (6.5),
      title_pad (3.0), legend (False), legend_fontsize (5.0), legend_loc ('lower right'),
      spine_width (0.6)
    """
    order = params.get("group_order") or list(pd.unique(df["group"]))
    colors, labels = params.get("group_colors", {}), params.get("group_labels", {})
    if params.get("zero_line", True):
        ax.axhline(0, color=params.get("zero_line_color", "#9ca3af"), lw=float(params.get("zero_line_width", 0.4)), zorder=1)
    if params.get("fit", True) and len(df) > 2:
        b, a = np.polyfit(df["x"], df["y"], 1)
        xs = np.linspace(df["x"].min(), df["x"].max(), 50)
        ax.plot(xs, a + b * xs, color=params.get("fit_color", "#374151"), lw=float(params.get("fit_width", 0.7)),
                ls=params.get("fit_style", "-"), zorder=2)
    for g in order:
        d = df[df["group"] == g]
        ax.scatter(d["x"], d["y"], s=float(params.get("marker_size", 14)), color=colors.get(g, "#6b7280"),
                   edgecolors=params.get("edgecolor", "white"), linewidths=float(params.get("edgewidth", 0.4)),
                   label=labels.get(g, g), zorder=3)
        if params.get("point_labels") and "label" in d:
            dx, dy = params.get("point_label_offset", [2, 1])
            for _, r in d.iterrows():
                ax.annotate(str(r["label"]), (r["x"], r["y"]), xytext=(dx, dy), textcoords="offset points",
                            fontsize=float(params.get("point_label_fontsize", 4.6)), color=colors.get(g, "#6b7280"))
    if params.get("annotate_r", True) and len(df) > 2:
        r, p = pearsonr(df["x"], df["y"])
        x0, y0 = params.get("r_xy", [0.03, 0.97])
        ax.text(x0, y0, params.get("r_fmt", "r = {r:+.2f}, P = {p:.1g}").format(r=r, p=p, n=len(df)),
                transform=ax.transAxes, ha="left", va="top", fontsize=float(params.get("r_fontsize", 5.5)))
    for k, setter in (("xlim", ax.set_xlim), ("ylim", ax.set_ylim)):
        if params.get(k) is not None:
            setter(*params[k])
    a_sz = float(params.get("axes_label_size", 6.0))
    if params.get("xlabel"):
        ax.set_xlabel(params["xlabel"], fontsize=a_sz)
    if params.get("ylabel"):
        ax.set_ylabel(params["ylabel"], fontsize=a_sz)
    ax.tick_params(labelsize=float(params.get("tick_label_size", 5.5)), length=2)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(float(params.get("spine_width", 0.6)))
    if params.get("legend"):
        ax.legend(fontsize=float(params.get("legend_fontsize", 5.0)), loc=params.get("legend_loc", "lower right"),
                  frameon=False, handletextpad=0.2, borderaxespad=0.2)
    if params.get("title"):
        ax.set_title(params["title"], fontsize=float(params.get("title_size", 6.5)), fontweight="bold",
                     pad=float(params.get("title_pad", 3.0)))
    return ax
