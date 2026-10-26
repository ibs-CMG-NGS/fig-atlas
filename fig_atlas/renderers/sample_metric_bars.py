"""Per-sample metric bars: one bar per library, grouped and coloured by condition,
with optional reference lines (e.g. QC thresholds). All styling from ``params``."""
from __future__ import annotations

FAMILY = "column"    # gallery family (fig_atlas/family.py): the shape this module draws

import pandas as pd


from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("sample_metric_bars", params=[
    # [Groups and bars]
    Param("group_order", list, None, role="Group order, left to right (default: order in the data)"),
    Param("group_colors", dict, {}, open_keys=True, role="Bar colour per group (unlisted groups are grey)"),
    Param("group_labels", dict, {}, open_keys=True, role="Display label per group"),
    Param("bar_width", float, 0.8, unit="x units (one sample = 1)", range=(0, None), role="Bar width"),
    Param("group_gap", float, 0.6, unit="x units", range=(0, None), role="Extra gap between groups",
          tune="raise to separate the groups more"),
    Param("edgecolor", "color", "none", unit="color", role="Bar outline colour"),
    Param("ylim", list, None, unit="data coords [min, max]", role="y-axis range (default: data)"),
    Param("spine_width", float, 0.6, unit="pt", range=(0, None), role="Axis spine width"),
    # [Reference lines and values]
    Param("ref_lines", list, [], role="Horizontal reference lines: list of {y, label, color, style, width}"),
    Param("ref_label_x", float, 1.0, unit="axes fraction", role="x position of the reference line labels"),
    Param("ref_label_fontsize", float, 5.0, unit="pt", range=(0, None), role="Reference line label size"),
    Param("show_values", bool, None, role="Print each bar's value above it"),
    Param("value_fmt", str, "{:.2f}", role="Format string of the printed values"),
    Param("value_fontsize", float, 4.8, unit="pt", range=(0, None), role="Printed value size"),
    # [Labels]
    Param("title", str, None, role="Panel title"),
    Param("ylabel", str, None, role="y-axis title"),
    Param("group_label_rotation", float, 0, unit="degrees", role="Group label rotation"),
    Param("title_pad", float, 3.0, unit="pt", range=(0, None), role="Gap between title and axes"),
    Param("title_size", float, 6.5, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 6.0, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 5.5, unit="pt", range=(0, None), role="y tick label font size"),
    Param("group_label_fontsize", float, 5.5, unit="pt", range=(0, None), role="Group label font size"),
])


@uses_schema(SCHEMA)
def render_sample_metric_bars(ax, df: pd.DataFrame, params: dict):
    """``df`` columns: sample, group, value (rows in display order).

    params: group_order, group_colors, group_labels, bar_width (0.8), group_gap (0.6: extra
      space between groups, in bar units), edgecolor ('none'),
      ref_lines (list of {y, label, color, style, width}), ref_label_fontsize (5.0),
      ref_label_x (axes fraction, 1.0), ylabel, ylim, axes_label_size (6.0),
      tick_label_size (5.5), group_label_fontsize (5.5), group_label_rotation (0),
      show_values (False), value_fmt ('{:.2f}'), value_fontsize (4.8), title,
      title_size (6.5), title_pad (3.0), spine_width (0.6)
    """
    order = params.get("group_order") or list(pd.unique(df["group"]))
    colors, labels = params.get("group_colors", {}), params.get("group_labels", {})
    gap, w = float(params.get("group_gap", 0.6)), float(params.get("bar_width", 0.8))
    x, ticks, centers = 0.0, [], []
    for g in order:
        d = df[df["group"] == g]
        xs = [x + i for i in range(len(d))]
        ax.bar(xs, d["value"], width=w, color=colors.get(g, "#9ca3af"), edgecolor=params.get("edgecolor", "none"), zorder=2)
        if params.get("show_values"):
            for xi, v in zip(xs, d["value"]):
                ax.text(xi, v, params.get("value_fmt", "{:.2f}").format(v), ha="center", va="bottom",
                        fontsize=float(params.get("value_fontsize", 4.8)))
        ticks += xs
        centers.append((sum(xs) / len(xs) if xs else x, g))
        x += len(d) + gap
    for ref in params.get("ref_lines", []):
        ax.axhline(float(ref["y"]), color=ref.get("color", "#b91c1c"), ls=ref.get("style", "--"),
                   lw=float(ref.get("width", 0.6)), zorder=1)
        if ref.get("label"):
            ax.text(float(params.get("ref_label_x", 1.0)), float(ref["y"]), " " + ref["label"],
                    transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=float(params.get("ref_label_fontsize", 5.0)), color=ref.get("color", "#b91c1c"))
    ax.set_xticks([c for c, _ in centers])
    ax.set_xticklabels([labels.get(g, g) for _, g in centers], fontsize=float(params.get("group_label_fontsize", 5.5)),
                       rotation=float(params.get("group_label_rotation", 0)))
    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="y", labelsize=float(params.get("tick_label_size", 5.5)), length=2)
    if params.get("ylim") is not None:
        ax.set_ylim(*params["ylim"])
    if params.get("ylabel"):
        ax.set_ylabel(params["ylabel"], fontsize=float(params.get("axes_label_size", 6.0)))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(float(params.get("spine_width", 0.6)))
    if params.get("title"):
        ax.set_title(params["title"], fontsize=float(params.get("title_size", 6.5)), fontweight="bold",
                     pad=float(params.get("title_pad", 3.0)))
    return ax
