"""Violin plot: the distribution of a value per category, with the median and
quartiles inside and, optionally, every value as a point. With ``hue_col`` a
second factor draws its violins side by side inside each category.

Data: one row per observation -- ``x_col`` (the category) and ``y_col`` (the
value), optionally ``hue_col`` (the factor split inside each category).
Categories are ordered by ``x_order`` (default: order in the data) and coloured
by ``group_colors`` keyed by category (with a hue, by ``hue_colors`` keyed by
hue value). Returns per-violin n, median and quartiles, ready for
``fig_atlas.source_data.add``.
"""
from __future__ import annotations

FAMILY = "column"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd

from ..schema import Param, Schema, uses_schema
from ._basic import TEXT, Y_AXIS, finish

SCHEMA = Schema("violin", extends=[Y_AXIS, TEXT], params=[
    # [Data]
    Param("x_col", str, "group", role="Column with the categories (x axis)"),
    Param("y_col", str, "value", role="Column with the values"),
    Param("x_order", list, None, role="Category order on x (default: order in the data)"),
    Param("x_labels", dict, {}, open_keys=True, role="Shown name per category (default: the category)"),
    # [Second factor]
    Param("hue_col", str, None,
          role="Second factor: draw one violin per category and hue value, side by side (default: not used)"),
    Param("hue_order", list, None, role="Hue order inside each category (default: order in the data)"),
    Param("hue_colors", dict, {}, open_keys=True, unit="hex color",
          role="Fill colour per hue value (default: matplotlib colour cycle)"),
    Param("hue_labels", dict, {}, open_keys=True, role="Legend label per hue value (default: the hue value)"),
    # [Violins]
    Param("group_colors", dict, {}, open_keys=True, unit="hex color",
          role="Fill colour per category (default: matplotlib colour cycle)"),
    Param("violin_width", float, 0.8, unit="x units (categories are 1 apart)", range=(0, 1),
          role="Width of each violin", tune="lower for more space between categories"),
    Param("violin_alpha", float, 0.6, unit="[0-1] opacity", range=(0, 1), role="Violin fill opacity"),
    Param("violin_edge_color", "color", "#374151", unit="hex color", role="Violin outline colour"),
    Param("violin_edge_width", float, 0.6, unit="pt", range=(0, None), role="Violin outline width"),
    Param("bandwidth", float, None, unit="fraction of the data's spread (scipy gaussian_kde bw_method)",
          range=(0, None), role="Smoothing of the violin outline (default: Scott's rule)",
          tune="lower to follow the data more closely, raise for a smoother outline"),
    Param("show_quartiles", bool, True, role="Draw the median (dot) and quartiles (thick line) inside each violin"),
    Param("median_color", "color", "#ffffff", unit="hex color", role="Median dot colour"),
    Param("median_size", float, 12.0, unit="pt^2 (marker area)", range=(0, None), role="Median dot size"),
    Param("quartile_color", "color", "#111827", unit="hex color", role="Quartile bar colour"),
    Param("quartile_width", float, 3.0, unit="pt", range=(0, None), role="Quartile bar width"),
    # [Points]
    Param("show_points", bool, False, role="Overlay every value as a point"),
    Param("point_color", "color", "#111827", unit="hex color", role="Point colour"),
    Param("point_size", float, 6.0, unit="pt^2 (marker area)", range=(0, None), role="Point size"),
    Param("point_alpha", float, 0.6, unit="[0-1] opacity", range=(0, 1), role="Point opacity"),
    Param("point_edge_width", float, 0.0, unit="pt", range=(0, None), role="Point outline width (0: none)"),
    Param("point_jitter", float, 0.08, unit="x units", range=(0, None), role="Horizontal scatter of the points"),
    Param("point_seed", int, 0, unit="random seed", role="Seed of the jitter (fixed for reproducible output)"),
])


@uses_schema(SCHEMA)
def render_violin(ax, df, params):
    """Draw one violin per category (or per category and hue value) onto ``ax``;
    returns the per-violin summary drawn."""
    import matplotlib
    from matplotlib.patches import Patch
    x_col, y_col = params.get("x_col", "group"), params.get("y_col", "value")
    order = params.get("x_order") or list(dict.fromkeys(df[x_col].dropna()))
    colors, names = params.get("group_colors", {}), params.get("x_labels", {})
    cycle = matplotlib.rcParams["axes.prop_cycle"].by_key().get("color", [None])
    hue_col = params.get("hue_col")
    hues = (params.get("hue_order") or list(dict.fromkeys(df[hue_col].dropna()))) if hue_col else []
    hue_colors, hue_labels = params.get("hue_colors", {}), params.get("hue_labels", {})
    total_width = float(params.get("violin_width", 0.8))
    width = total_width / (len(hues) or 1)

    # One slot per violin: (category, hue or None, x position, values, colour)
    slots = []
    for i, c in enumerate(order):
        rows_c = df[df[x_col] == c]
        if hue_col:
            for j, h in enumerate(hues):
                v = pd.to_numeric(rows_c.loc[rows_c[hue_col] == h, y_col], errors="coerce").dropna().to_numpy()
                pos = i - total_width / 2 + width * (j + 0.5)
                slots.append((c, h, pos, v, hue_colors.get(h) or cycle[j % len(cycle)]))
        else:
            v = pd.to_numeric(rows_c[y_col], errors="coerce").dropna().to_numpy()
            slots.append((c, None, float(i), v, colors.get(c) or cycle[i % len(cycle)]))

    keep = [k for k, s in enumerate(slots) if s[3].size > 1]
    parts = ax.violinplot([slots[k][3] for k in keep], positions=[slots[k][2] for k in keep], widths=width,
                          bw_method=params.get("bandwidth"), showmeans=False, showmedians=False,
                          showextrema=False)
    for k, body in zip(keep, parts["bodies"]):
        body.set_facecolor(slots[k][4])
        body.set_alpha(params.get("violin_alpha", 0.6))
        body.set_edgecolor(params.get("violin_edge_color", "#374151"))
        body.set_linewidth(params.get("violin_edge_width", 0.6))

    rows = []
    rng = np.random.default_rng(int(params.get("point_seed", 0)))
    for c, h, pos, v, _color in slots:
        if v.size == 0:
            continue
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        row = {"category": c, "n": int(v.size), "median": med, "q1": q1, "q3": q3}
        if hue_col:
            row["group"] = h
        rows.append(row)
        if params.get("show_quartiles", True):
            ax.vlines(pos, q1, q3, color=params.get("quartile_color", "#111827"),
                      linewidth=params.get("quartile_width", 3.0), zorder=3)
            ax.scatter([pos], [med], s=params.get("median_size", 12.0), color=params.get("median_color", "#ffffff"),
                       zorder=4)
        if params.get("show_points", False):
            jit = params.get("point_jitter", 0.08)
            ax.scatter(pos + rng.uniform(-jit, jit, v.size), v, s=params.get("point_size", 6.0),
                       color=params.get("point_color", "#111827"), alpha=params.get("point_alpha", 0.6),
                       linewidths=params.get("point_edge_width", 0.0), zorder=2)
    ax.set_xticks(range(len(order)), [str(names.get(c, c)) for c in order])
    if hue_col and hues and params.get("show_legend", True):
        handles = [Patch(facecolor=hue_colors.get(h) or cycle[j % len(cycle)],
                         alpha=params.get("violin_alpha", 0.6), label=str(hue_labels.get(h, h)))
                   for j, h in enumerate(hues)]
        size = params.get("legend_fontsize")
        ax.legend(handles=handles, loc=params.get("legend_loc", "best"),
                  frameon=params.get("legend_frameon", False),
                  fontsize=size if size is not None else params.get("tick_label_size"))
    finish(ax, params, x_col, y_col, numeric_x=False)
    return pd.DataFrame(rows)
