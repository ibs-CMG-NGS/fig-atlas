"""Paired-response scatter: one gene pair per point, x = species A, y = species B.

Draws, for each ortholog pair tested in both species, its response in one
species against the other (e.g. human vs mouse log2 fold change), coloured by
where it is significant (both, same direction / both, opposite / A only /
B only / neither). Values beyond +/-lim are drawn on the edge. All styling from
``params``.
"""
from __future__ import annotations

FAMILY = "xy"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd


from fig_atlas.schema import Param, Schema, uses_schema

SCHEMA = Schema("species_response_scatter", params=[
    # [Points]
    Param("category_order", list, None, role="Drawing order of the categories (later on top)"),
    Param("colors", dict, {}, open_keys=True, unit="hex color per category", role="Point colour per category"),
    Param("sizes", dict, {}, open_keys=True, unit="pt^2 per category", role="Point size per category"),
    Param("alphas", dict, {}, open_keys=True, unit="[0-1] per category", role="Point opacity per category"),
    Param("default_size", float, 1.0, unit="pt^2 (marker area)", range=(0, None), role="Size of categories without one"),
    Param("default_alpha", float, 0.5, unit="[0-1] opacity", range=(0, 1), role="Opacity of categories without one"),
    Param("edgecolor", "color", "none", unit="color", role="Point outline"),
    Param("rasterized", bool, True, role="Rasterize the points (smaller PDF for tens of thousands of points)"),
    # [Axes and guides]
    Param("lim", float, 6.0, unit="log2 fold change (data coords)", range=(0, None),
          role="Both axes run -lim..+lim", tune="raise if many points pile on the edge"),
    Param("ticks", list, None, unit="data coords", role="Tick positions on both axes"),
    Param("zero_line_color", "color", "#9ca3af", unit="hex color", role="Colour of the x = 0 and y = 0 lines"),
    Param("zero_line_width", float, 0.4, unit="pt", range=(0, None), role="Width of the zero lines"),
    Param("diagonal", bool, True, role="Draw the y = x line"),
    Param("diagonal_color", "color", "#6b7280", unit="hex color", role="Colour of the y = x line"),
    Param("diagonal_width", float, 0.4, unit="pt", range=(0, None), role="Width of the y = x line"),
    Param("diagonal_style", str, "--", role="Line style of the y = x line (matplotlib)"),
    Param("spine_width", float, 0.6, unit="pt", range=(0, None), role="Axis line and tick width"),
    # [Text]
    Param("xlabel", str, None, role="x-axis title"),
    Param("ylabel", str, None, role="y-axis title"),
    Param("axes_label_size", float, 6.5, unit="pt", role="Axis title font size"),
    Param("tick_label_size", float, 5.5, unit="pt", role="Tick label font size"),
    Param("title", str, None, role="Panel title"),
    Param("title_size", float, 7.0, unit="pt", role="Panel title font size"),
    Param("title_weight", str, "bold", role="Panel title font weight"),
    Param("title_pad", float, 2.0, unit="pt", role="Gap between title and plot"),
    Param("annotations", list, [], role="Lines of text at the top left (e.g. rho, n)"),
    Param("annotation_fontsize", float, 5.5, unit="pt", range=(0, None), role="Annotation text size"),
    Param("annotation_xy", list, [0.03, 0.97], unit="axes fraction (x, y)", role="Position of the first annotation line"),
    Param("annotation_line_step", float, 0.075, unit="axes fraction", role="Spacing between annotation lines"),
    Param("annotation_color", "color", "#111827", unit="hex color", role="Annotation text colour"),
])


@uses_schema(SCHEMA)
def render_species_response_scatter(ax, df: pd.DataFrame, params: dict):
    """``df`` columns: x, y, category. Categories are drawn in ``category_order``
    (later on top).

    params: category_order, colors (category -> colour), sizes (category -> pt^2),
      alphas (category -> alpha), default_size (1.0), default_alpha (0.5),
      lim (6.0), ticks, edgecolor ('none'), rasterized (True),
      zero_line_color ('#9ca3af'), zero_line_width (0.4),
      diagonal (True), diagonal_color ('#6b7280'), diagonal_width (0.4), diagonal_style ('--'),
      xlabel, ylabel, axes_label_size (6.5), tick_label_size (5.5),
      title, title_size (7.0), title_weight ('bold'), title_pad (2.0),
      annotations (list of str, top-left), annotation_fontsize (5.5),
      annotation_xy ([0.03, 0.97]), annotation_line_step (0.075), annotation_color ('#111827'),
      spine_width (0.6)
    """
    lim = float(params.get("lim", 6.0))
    order = params.get("category_order") or list(pd.unique(df["category"]))
    colors, sizes, alphas = params.get("colors", {}), params.get("sizes", {}), params.get("alphas", {})
    raster = bool(params.get("rasterized", True))
    for cat in order:
        d = df[df["category"] == cat]
        if d.empty:
            continue
        ax.scatter(np.clip(d["x"], -lim, lim), np.clip(d["y"], -lim, lim),
                   s=float(sizes.get(cat, params.get("default_size", 1.0))),
                   c=colors.get(cat, "#9ca3af"), alpha=float(alphas.get(cat, params.get("default_alpha", 0.5))),
                   edgecolors=params.get("edgecolor", "none"), linewidths=0, rasterized=raster, zorder=2)
    zc, zw = params.get("zero_line_color", "#9ca3af"), float(params.get("zero_line_width", 0.4))
    ax.axhline(0, color=zc, lw=zw, zorder=1)
    ax.axvline(0, color=zc, lw=zw, zorder=1)
    if params.get("diagonal", True):
        ax.plot([-lim, lim], [-lim, lim], ls=params.get("diagonal_style", "--"),
                color=params.get("diagonal_color", "#6b7280"), lw=float(params.get("diagonal_width", 0.4)), zorder=1)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ticks = params.get("ticks")
    if ticks is not None:
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
    a_sz, t_sz = float(params.get("axes_label_size", 6.5)), float(params.get("tick_label_size", 5.5))
    if params.get("xlabel"):
        ax.set_xlabel(params["xlabel"], fontsize=a_sz)
    if params.get("ylabel"):
        ax.set_ylabel(params["ylabel"], fontsize=a_sz)
    ax.tick_params(labelsize=t_sz, width=float(params.get("spine_width", 0.6)), length=2)
    for sp in ax.spines.values():
        sp.set_linewidth(float(params.get("spine_width", 0.6)))
    if params.get("title"):
        ax.set_title(params["title"], fontsize=float(params.get("title_size", 7.0)),
                     fontweight=params.get("title_weight", "bold"), pad=float(params.get("title_pad", 2.0)))
    x0, y0 = params.get("annotation_xy", [0.03, 0.97])
    step = float(params.get("annotation_line_step", 0.075))
    for i, line in enumerate(params.get("annotations", [])):
        ax.text(x0, y0 - i * step, line, transform=ax.transAxes, ha="left", va="top",
                fontsize=float(params.get("annotation_fontsize", 5.5)),
                color=params.get("annotation_color", "#111827"), zorder=3)
    return ax
