"""Signed-value heatmap (rows x columns, diverging colour, NaN = not tested).

A small general-purpose matrix heatmap for signed statistics such as signed
-log10(FDR): rows are features (genes, motifs), columns are conditions, and
columns can be grouped under shared headers (e.g. an ATAC block and an RNA
block, each over the same time points). Values beyond +/-vmax are drawn
saturated; missing values (not tested) get their own neutral colour.

Draws onto an existing Axes so it can serve both as a stand-alone panel and
as a narrow side strip aligned to another plot's rows.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd
from matplotlib import colormaps
from matplotlib.colors import Normalize

from ..schema import Param, Schema, uses_schema
from .text_color import readable_text_color

SCHEMA = Schema("signed_heatmap", params=[
    # [Colour scale]
    Param("cmap", "cmap", "RdBu_r", role="Diverging colormap for the signed values", tune="any registered diverging map"),
    Param("vmax", float, 10.0, unit="value units (e.g. signed -log10 FDR)", range=(0, None),
          role="Colour scale runs -vmax..+vmax; beyond is drawn saturated", tune="lower to stretch contrast for weak values"),
    Param("nan_color", "color", "#e5e7eb", unit="hex color", role="Colour of missing (not tested) cells"),
    # [Geometry]
    Param("origin", ("upper", "lower"), "upper",
          role="'upper': first row on top; 'lower': first row at the bottom (to align with a 0..n-1 scatter)"),
    Param("ylim", list, None, unit="data coords [lo, hi]", role="Row range, to line up with another axes' rows"),
    Param("cell_edgecolor", "color", "white", unit="hex color", role="Cell border colour"),
    Param("cell_edgewidth", float, 0.5, unit="pt", range=(0, None), role="Cell border width", tune="0 for no borders"),
    Param("frame_width", float, 0.6, unit="pt", range=(0, None), role="Outer frame (spine) width"),
    # [Values printed in cells]
    Param("show_values", bool, False, role="Print each cell's value"),
    Param("value_fmt", str, "{:+.1f}", role="Python format for the printed values"),
    Param("value_fontsize", float, 5.0, unit="pt", range=(0, None), role="Cell value font size", tune="lower if values overflow cells"),
    Param("value_text_color_mode", ("threshold", "contrast"), "threshold",
          role="'threshold': white text above value_dark_threshold; 'contrast': white or dark by contrast with the cell colour"),
    Param("value_dark_threshold", float, 0.6, unit="fraction of vmax", range=(0, 1),
          role="|value|/vmax above which text turns light (threshold mode)", tune="lower if text on mid-dark cells is hard to read"),
    Param("value_light_color", "color", "white", unit="hex color", role="Text colour on dark cells"),
    Param("value_dark_color", "color", "#111827", unit="hex color", role="Text colour on light cells"),
    Param("muted_value_color", "color", "#9ca3af", unit="hex color", role="Text colour of muted values (e.g. not significant)"),
    Param("muted_value_style", ("normal", "italic", "oblique"), "italic", role="Font style of muted values"),
    # [Row labels]
    Param("show_row_labels", bool, True, role="Show row (feature) labels"),
    Param("row_label_side", ("left", "right"), "left", role="Side the row labels sit on"),
    Param("row_label_style", ("normal", "italic", "oblique"), "normal", role="Row label font style (italic for gene names)"),
    Param("row_label_fontsize", float, 6.0, unit="pt", range=(0, None), role="Row label font size", tune="lower if labels overlap"),
    Param("row_separators", list, [], unit="row indices", role="Draw a horizontal line above each of these rows"),
    Param("row_separator_color", "color", "#1f2937", unit="hex color", role="Row separator colour"),
    Param("row_separator_width", float, 0.8, unit="pt", range=(0, None), role="Row separator width"),
    # [Column labels and groups]
    Param("col_labels", list, None, role="Column labels (default: the column names)"),
    Param("col_label_fontsize", float, 5.5, unit="pt", range=(0, None), role="Column label font size"),
    Param("col_label_rotation", float, 0, unit="degrees", role="Column label rotation", tune="45 if labels collide"),
    Param("col_label_side", ("bottom", "top"), "bottom", role="Side the column labels sit on"),
    Param("col_groups", list, None, role="Column group headers: [[label, n_columns], ...] left to right"),
    Param("group_label_fontsize", float, 6.0, unit="pt", range=(0, None), role="Column group header font size"),
    Param("group_label_weight", str, "bold", role="Column group header font weight"),
    Param("group_label_pad", float, 0.4, unit="rows (data units)", role="Gap between the matrix and the group headers",
          tune="raise if headers touch the column labels"),
    Param("group_separator_color", "color", "#1f2937", unit="hex color", role="Vertical line between column groups"),
    Param("group_separator_width", float, 0.8, unit="pt", range=(0, None), role="Column group separator width"),
])


@uses_schema(SCHEMA)
def render_signed_heatmap(ax, values: pd.DataFrame, params: dict, value_muted=None):
    """Draw ``values`` (rows x columns, NaN allowed) onto ``ax``.

    params:
      cmap ('RdBu_r'), vmax (10.0), nan_color ('#e5e7eb'),
      origin ('upper': first row on top | 'lower': first row at the bottom,
        for strips that must line up with a y = 0..n-1 scatter),
      ylim (optional (lo, hi) to match another axes' row range),
      show_values (False), value_fmt ('{:+.1f}'), value_fontsize (5.0),
      value_dark_threshold (0.6: |v|/vmax above which the text turns white),
      value_text_color_mode ('threshold' | 'contrast': white or dark text by
        contrast with each cell's colour -- use it when the colormap's two
        ends darken at different rates), value_light_color ('white'),
        value_dark_color ('#111827'),
      show_row_labels (True), row_label_side ('left'), row_label_style
        ('normal' | 'italic'), row_label_fontsize (6.0),
      col_labels (list; defaults to the column names), col_label_fontsize (5.5),
      col_label_rotation (0), col_label_side ('bottom' | 'top'),
      col_groups (list of [label, n_columns] headers above the matrix, in
        column order), group_label_fontsize (6.0), group_label_weight ('bold'),
      group_label_pad (0.4: header height above the top edge, in row units),
      group_separator_color ('#1f2937'), group_separator_width (0.8),
      cell_edgecolor ('white'), cell_edgewidth (0.5), frame_width (0.6),
      muted_value_color ('#9ca3af'), muted_value_style ('italic'),
      row_separators (list of row boundaries, e.g. [4] draws a line between rows
        3 and 4), row_separator_color ('#1f2937'), row_separator_width (0.8)
    value_muted: optional boolean array/DataFrame of the same shape; True cells
      show their value in the muted colour/style (e.g. not significant).
    Returns the ScalarMappable-bearing image (for a colour bar).
    """
    vals = values.to_numpy(dtype=float)
    n_rows, n_cols = vals.shape
    vmax = float(params.get("vmax", 10.0))
    cmap = colormaps[params.get("cmap", "RdBu_r")].copy()
    cmap.set_bad(params.get("nan_color", "#e5e7eb"))
    norm = Normalize(-vmax, vmax)
    origin = params.get("origin", "upper")

    im = ax.imshow(np.ma.masked_invalid(vals), cmap=cmap, norm=norm, aspect="auto",
                   interpolation="nearest", origin=origin,
                   extent=(-0.5, n_cols - 0.5, n_rows - 0.5, -0.5) if origin == "upper"
                   else (-0.5, n_cols - 0.5, -0.5, n_rows - 0.5))
    if params.get("ylim") is not None:
        ax.set_ylim(*params["ylim"])

    # Cell borders
    edge_c, edge_w = params.get("cell_edgecolor", "white"), float(params.get("cell_edgewidth", 0.5))
    for x in np.arange(0.5, n_cols - 0.5):
        ax.axvline(x, color=edge_c, lw=edge_w)
    for y in np.arange(0.5, n_rows - 0.5):
        ax.axhline(y, color=edge_c, lw=edge_w)

    # Values in cells
    if params.get("show_values", False):
        fmt = params.get("value_fmt", "{:+.1f}")
        fs = float(params.get("value_fontsize", 5.0))
        dark = float(params.get("value_dark_threshold", 0.6))
        muted = None if value_muted is None else np.asarray(value_muted, dtype=bool)
        for r in range(n_rows):
            for c in range(n_cols):
                v = vals[r, c]
                if np.isnan(v):
                    continue
                if muted is not None and muted[r, c]:
                    ax.text(c, r, fmt.format(v), ha="center", va="center", fontsize=fs,
                            color=params.get("muted_value_color", "#9ca3af"),
                            fontstyle=params.get("muted_value_style", "italic"))
                    continue
                if params.get("value_text_color_mode", "threshold") == "contrast":
                    # White or dark by contrast with the cell's actual colour.
                    color = readable_text_color(cmap(norm(v)), params.get("value_light_color", "white"),
                                                params.get("value_dark_color", "#111827"))
                else:
                    color = "white" if abs(v) / vmax > dark else "#111827"
                ax.text(c, r, fmt.format(v), ha="center", va="center", fontsize=fs, color=color)

    for rb in params.get("row_separators", []) or []:
        ax.axhline(float(rb) - 0.5, color=params.get("row_separator_color", "#1f2937"),
                   lw=float(params.get("row_separator_width", 0.8)))

    # Row labels
    row_fs = float(params.get("row_label_fontsize", 6.0))
    if params.get("show_row_labels", True):
        ax.set_yticks(range(n_rows))
        ax.set_yticklabels([str(i) for i in values.index], fontsize=row_fs,
                           fontstyle=params.get("row_label_style", "normal"))
        if params.get("row_label_side", "left") == "right":
            ax.yaxis.tick_right()
    else:
        ax.set_yticks([])

    # Column labels
    col_labels = params.get("col_labels") or [str(c) for c in values.columns]
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, fontsize=float(params.get("col_label_fontsize", 5.5)),
                       rotation=float(params.get("col_label_rotation", 0)))
    if params.get("col_label_side", "bottom") == "top":
        ax.xaxis.tick_top()
    ax.tick_params(length=0, pad=1.5)

    # Column-group headers and separators
    groups = params.get("col_groups") or []
    if groups:
        top_y = -0.5 if origin == "upper" else n_rows - 0.5
        sign = -1 if origin == "upper" else 1
        pad = float(params.get("group_label_pad", 0.4))
        start = 0
        for i, (label, width) in enumerate(groups):
            width = int(width)
            ax.text(start + width / 2 - 0.5, top_y + sign * pad, str(label), ha="center",
                    va="bottom" if origin == "lower" else "bottom",
                    fontsize=float(params.get("group_label_fontsize", 6.0)),
                    fontweight=params.get("group_label_weight", "bold"), clip_on=False)
            if i < len(groups) - 1:
                ax.axvline(start + width - 0.5, color=params.get("group_separator_color", "#1f2937"),
                           lw=float(params.get("group_separator_width", 0.8)))
            start += width

    for spine in ax.spines.values():
        spine.set_linewidth(float(params.get("frame_width", 0.6)))
    return im
