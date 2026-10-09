"""Narrowing funnel bar chart (target gene discovery).

Synthesized (Case C) from final_target_summary_figure: a small number of
monotonic-decreasing steps (e.g. mouse reversal -> intersection -> final
targets) drawn as descending horizontal bars with value labels. All visual
attributes come from ``params``.
"""

from __future__ import annotations

import pandas as pd

from ..params import text_param


from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("funnel", params=[
    # [Bars]
    Param("bar_color", "color", "#3b73b9", unit="hex color", role="Fill colour of the funnel bars"),
    Param("bar_edgecolor", "color", "black", unit="color", role="Bar outline colour"),
    Param("bar_width", float, 0.5, unit="fraction of the category spacing", range=(0, 1),
          role="Bar width", tune="lower to separate the steps more"),
    # [Value labels]
    Param("show_value_labels", bool, True, role="Print the count on each bar"),
    Param("value_position", ("top", "inside"), "top", role="Count above the bar ('top') or centred inside it"),
    Param("value_color", "color", "black", unit="color", role="Count label colour"),
    Param("value_fontsize", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Count label size (default axes_label_size)"),
    # [Labels]
    Param("labels_title", str, "Target narrowing", role="Panel title"),
    Param("labels_subtitle", str, None, role="Second line under the title"),
    Param("labels_ylabel", str, "count", role="y-axis title"),
    Param("title_pad", float, 12.0, unit="pt", range=(0, None), role="Gap between title and axes",
          tune="raise if the title touches the value labels"),
    Param("xtick_rotation", float, 0, unit="degrees", role="Step label rotation (non-zero labels are right-aligned)"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("subtitle_size", float, 9, unit="pt", range=(0, None), role="Subtitle font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_funnel(ax, steps, params):
    """Draw a narrowing funnel onto ``ax``.

    ``steps`` is an ordered list of (label, value) tuples, largest first.
    params: bar_color, bar_edgecolor, bar_width, value_color, value_fontsize,
            show_value_labels, labels_title, labels_subtitle, xtick_rotation,
            xlabel_pad, axes_label_size, tick_label_size, title_size,
            subtitle_size
    """
    title_sz = params.get("title_size", 13)
    sub_sz = params.get("subtitle_size", 9)
    a_sz = params.get("axes_label_size", 11)
    t_sz = params.get("tick_label_size", 8)

    labels = [str(s[0]) for s in steps]
    values = [float(s[1]) for s in steps]

    bar_color = params.get("bar_color", "#3b73b9")
    bar_width = float(params.get("bar_width", 0.5))
    edge = params.get("bar_edgecolor", "black")

    x = list(range(len(steps)))
    ax.bar(x, values, width=bar_width, color=bar_color, edgecolor=edge,
           linewidth=0.8, zorder=2)

    if params.get("show_value_labels", True):
        vc = params.get("value_color", "black")
        fs = float(params.get("value_fontsize", a_sz))
        v_pos = params.get("value_position", "top")
        for xi, v in zip(x, values):
            if v_pos == "top":
                ax.text(xi, v + max(values) * 0.015, f"{v:,.0f}", ha="center", va="bottom",
                        fontsize=fs, color=vc, fontweight="bold", zorder=3)
            else:
                ax.text(xi, v / 2, f"{v:,.0f}", ha="center", va="center",
                        fontsize=fs, color=vc, fontweight="bold", zorder=3)

    rotation = float(params.get("xtick_rotation", 0))
    ha = "center" if rotation == 0 else "right"
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=rotation, ha=ha, fontsize=t_sz)
    ax.tick_params(axis="y", labelsize=t_sz)
    ax.set_ylim(0, max(values) * 1.18)
    ax.grid(True, linestyle="-", color="#e8e8e8", alpha=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylabel(text_param(params, "labels_ylabel", "count"),
                  fontsize=a_sz, fontweight="bold")

    title = text_param(params, "labels_title", "Target narrowing")
    subtitle = params.get("labels_subtitle")
    if subtitle:
        ax.set_title(title, fontsize=title_sz, fontweight="bold",
                     pad=float(params.get("title_pad", 12.0)))
        ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=sub_sz, color="gray")
    else:
        ax.set_title(title, fontsize=title_sz, fontweight="bold", pad=8)

    return pd.DataFrame({"label": labels, "value": values})
