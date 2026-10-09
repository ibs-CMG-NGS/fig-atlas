"""Per-cluster mean z-score trajectory ("spaghetti") plot.

Companion to ``render_multi_group_heatmap``: takes the same z-scored gene x
sample matrix that renderer already computes (its ``zdata`` return value) and
draws one thin line per gene across the same sample columns, plus a bold
mean trajectory, with vertical dividers between condition groups. Meant to
sit directly under its cluster's heatmap so the two read as one unit with no
separate legend/color-matching needed.
"""

from __future__ import annotations

import ast

import numpy as np
import pandas as pd


from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("ts_profile", params=[
    # [Samples]
    Param("sample_groups", dict, None, open_keys=True, role="Group name -> sample columns, for dividers and group labels"),
    Param("profile_show_group_labels", bool, True, role="Label each sample group above the profile"),
    Param("profile_group_divider_color", "color", "#999999", unit="hex color", role="Colour of the lines between groups"),
    # [Profiles]
    Param("profile_line_color", "color", "#f39c12", unit="hex color", role="Colour of the per-gene lines"),
    Param("profile_line_width", float, 0.6, unit="pt", range=(0, None), role="Per-gene line width"),
    Param("profile_line_alpha", float, 0.25, unit="alpha [0-1]", range=(0, 1), role="Per-gene line opacity",
          tune="lower when many genes are drawn"),
    Param("profile_mean_line_color", "color", "#c0392b", unit="hex color", role="Colour of the mean line"),
    Param("profile_mean_line_width", float, 2.0, unit="pt", range=(0, None), role="Mean line width"),
    Param("profile_grid", bool, True, role="Draw a background grid"),
    Param("profile_y_min", float, CODE_DEFAULT, unit="data coords", role="Lower y limit (default z_min, else data)"),
    Param("profile_y_max", float, CODE_DEFAULT, unit="data coords", role="Upper y limit (default z_max, else data)"),
    Param("z_min", float, None, unit="z-score", role="Shared lower limit, used when profile_y_min is not set"),
    Param("z_max", float, None, unit="z-score", role="Shared upper limit, used when profile_y_max is not set"),
    # [Labels]
    Param("profile_labels_title", str, None, role="Panel title"),
    Param("profile_labels_ylabel", str, "Z-score", role="y-axis title"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


def _as_obj(v, default):
    if isinstance(v, str):
        try:
            return ast.literal_eval(v)
        except Exception:
            return default
    return v if v is not None else default


@uses_schema(SCHEMA)
def render_ts_profile(ax, zdata, params):
    """Draw a per-gene z-score trajectory plot onto ``ax``.

    params: sample_groups (dict of group -> [columns], for divider lines and
            x-tick group labels), profile_line_color, profile_line_alpha,
            profile_line_width, profile_mean_line_color,
            profile_mean_line_width, profile_show_group_labels (bool),
            profile_group_divider_color, profile_y_min, profile_y_max
            (default to z_min/z_max so the axis matches the heatmap's color
            scale), profile_labels_title, profile_labels_ylabel,
            profile_grid, axes_label_size, tick_label_size, title_size
    """
    a_sz = params.get("axes_label_size", 11)
    tick_sz = params.get("tick_label_size", 8)
    title_sz = params.get("title_size", 13)

    if zdata is None or len(zdata) == 0:
        ax.text(0.5, 0.5, "No profile data", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return

    columns = list(zdata.columns)
    n_samples = len(columns)
    x = np.arange(n_samples)

    line_color = params.get("profile_line_color", "#f39c12")
    line_alpha = float(params.get("profile_line_alpha", 0.25))
    line_width = float(params.get("profile_line_width", 0.6))
    for _, row in zdata.iterrows():
        ax.plot(x, row.to_numpy(), color=line_color, alpha=line_alpha,
                linewidth=line_width, zorder=2)

    mean_vals = zdata.mean(axis=0).to_numpy()
    ax.plot(x, mean_vals, color=params.get("profile_mean_line_color", "#c0392b"),
            linewidth=float(params.get("profile_mean_line_width", 2.0)), zorder=3)

    sample_groups = _as_obj(params.get("sample_groups"), {})
    if sample_groups:
        pos = 0
        centers, names = [], []
        for gname, gcols in sample_groups.items():
            n = len([c for c in gcols if c in columns])
            if n == 0:
                continue
            centers.append(pos + (n - 1) / 2)
            names.append(gname)
            pos += n
            if pos < n_samples:
                ax.axvline(pos - 0.5, color=params.get("profile_group_divider_color", "#999999"),
                          linewidth=0.8, linestyle="--", zorder=1)
        if params.get("profile_show_group_labels", True):
            ax.set_xticks(centers)
            ax.set_xticklabels(names, fontsize=tick_sz)
        else:
            ax.set_xticks([])
    else:
        ax.set_xticks([])

    ax.set_xlim(-0.5, n_samples - 0.5)
    y_min = params.get("profile_y_min", params.get("z_min"))
    y_max = params.get("profile_y_max", params.get("z_max"))
    if y_min is not None and y_max is not None:
        ax.set_ylim(float(y_min), float(y_max))
    ax.axhline(0, color="#333333", linewidth=0.6, zorder=1)
    ax.tick_params(axis="y", labelsize=tick_sz)

    ax.set_ylabel(params.get("profile_labels_ylabel", "Z-score"), fontsize=a_sz, fontweight="bold")
    title = params.get("profile_labels_title")
    if title:
        ax.set_title(title, fontsize=title_sz, fontweight="bold")
    if params.get("profile_grid", True):
        ax.grid(axis="y", alpha=0.2, linestyle="--", zorder=0)
