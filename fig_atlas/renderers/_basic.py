"""Shared parameters and helpers of the basic shapes (violin, histogram,
dose_response, survival, stacked_bar).

Each basic renderer extends the fragments it uses -- groups and colours, a
numeric x axis, the y axis, text and legend -- so its config block lists only
keys that change its drawing. The helpers read only keys of the fragments the
caller names.
"""
from __future__ import annotations

import matplotlib
import pandas as pd

from ..params import text_param
from ..schema import CODE_DEFAULT, Param, Schema

GROUPS = Schema("basic_groups", params=[
    Param("group_col", str, None, role="Column splitting the data into coloured groups (default: one group)"),
    Param("group_order", list, None, role="Group order in drawing and legend (default: order in the data)"),
    Param("group_colors", dict, {}, open_keys=True, unit="hex color",
          role="Colour per group (default: matplotlib colour cycle)"),
    Param("group_labels", dict, {}, open_keys=True, role="Legend label per group (default: the group value)"),
    Param("color", "color", "#4b5563", unit="hex color", role="Colour when there is no group_col"),
])

X_AXIS = Schema("basic_x_axis", params=[
    Param("x_log", bool, False, role="Log-scaled x axis"),
    Param("x_min", float, None, unit="data coords", role="Lower x limit (both x_min and x_max needed)"),
    Param("x_max", float, None, unit="data coords", role="Upper x limit"),
])

Y_AXIS = Schema("basic_y_axis", params=[
    Param("y_log", bool, False, role="Log-scaled y axis"),
    Param("y_min", float, None, unit="data coords", role="Lower y limit (both y_min and y_max needed)"),
    Param("y_max", float, None, unit="data coords", role="Upper y limit"),
    Param("grid", bool, False, role="Draw horizontal grid lines"),
    Param("grid_alpha", float, 0.3, unit="[0-1] opacity", range=(0, 1), role="Grid opacity"),
    Param("spine_width", float, None, unit="pt", range=(0, None), role="Axis line width (default: rcParams)"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
])

TEXT = Schema("basic_text", params=[
    Param("labels_title", str, None, role="Panel title (none: no title)"),
    Param("labels_xlabel", str, CODE_DEFAULT, role="x-axis title (default: the x column's name)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default: the y column's name)"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Tick label size (default: rcParams)"),
    Param("show_legend", bool, True, role="Show the group legend (only with a group_col)"),
    Param("legend_loc", str, "best", role="Legend location (matplotlib loc)"),
    Param("legend_fontsize", float, None, unit="pt", range=(0, None),
          role="Legend font size (none: tick_label_size)"),
    Param("legend_frameon", bool, False, role="Draw a frame around the legend"),
])

SCHEMA = Schema("basic", extends=[GROUPS, X_AXIS, Y_AXIS, TEXT])


def groups(df: pd.DataFrame, params, col: str | None = None):
    """[(group value or None, its rows, colour or None, legend label)] in drawing order."""
    g_col = col if col is not None else params.get("group_col")
    if not g_col:
        return [(None, df, params.get("color", "#4b5563"), None)]
    order = params.get("group_order") or list(dict.fromkeys(df[g_col].dropna()))
    colors, labels = params.get("group_colors", {}), params.get("group_labels", {})
    cycle = matplotlib.rcParams["axes.prop_cycle"].by_key().get("color", [None])
    return [(g, df[df[g_col] == g], colors.get(g) or cycle[i % len(cycle)], str(labels.get(g, g)))
            for i, g in enumerate(order)]


def finish(ax, params, xlabel: str, ylabel: str, numeric_x: bool = True) -> None:
    """Axis limits, scales, grid, spines and titles from the shared fragments."""
    if numeric_x:
        if params.get("x_log", False):
            ax.set_xscale("log")
        if params.get("x_min") is not None and params.get("x_max") is not None:
            ax.set_xlim(params.get("x_min"), params.get("x_max"))
    if params.get("y_log", False):
        ax.set_yscale("log")
    if params.get("y_min") is not None and params.get("y_max") is not None:
        ax.set_ylim(params.get("y_min"), params.get("y_max"))
    if params.get("grid", False):
        ax.grid(axis="y", alpha=params.get("grid_alpha", 0.3))
        ax.set_axisbelow(True)
    if params.get("spine_width") is not None:
        for s in ax.spines.values():
            s.set_linewidth(params.get("spine_width"))
    if params.get("hide_top_right", True):
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0))
    ax.set_xlabel(text_param(params, "labels_xlabel", xlabel), fontsize=params.get("axes_label_size"))
    ax.set_ylabel(text_param(params, "labels_ylabel", ylabel), fontsize=params.get("axes_label_size"))
    if params.get("tick_label_size") is not None:
        ax.tick_params(labelsize=params.get("tick_label_size"))


def legend(ax, params, grouped: bool) -> None:
    if grouped and params.get("show_legend", True) and ax.get_legend_handles_labels()[0]:
        size = params.get("legend_fontsize")
        ax.legend(loc=params.get("legend_loc", "best"), frameon=params.get("legend_frameon", False),
                  fontsize=size if size is not None else params.get("tick_label_size"))
