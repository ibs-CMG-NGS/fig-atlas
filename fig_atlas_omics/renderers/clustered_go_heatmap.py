"""Clustered GO terms and pathway enrichment heatmap renderer.

Renders a publication-grade cross-condition, cross-species enrichment heatmap
with distinct condition dividers, species sub-dividers, numeric cell annotations,
and configurable color palettes.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import matplotlib.pyplot as plt

from fig_atlas.schema import Param, Schema, uses_schema
from fig_atlas.renderers.text_color import readable_text_color

SCHEMA = Schema("clustered_go_heatmap", params=[
    # [Colour scale]
    Param("cmap", "cmap", "RdBu_r", role="Diverging colormap for the signed scores"),
    Param("vmax", float, 10.0, unit="value units (signed -log10 FDR)", range=(0, None),
          role="Colour scale runs -vmax..+vmax", tune="lower to stretch contrast for weak clusters"),
    # [Values printed in cells]
    Param("cell_sig_thresh", float, 1.3, unit="|value| (1.3 = FDR 0.05)",
          role="Cells at or above it print their value; below it a placeholder dash"),
    Param("cell_text_color_mode", ("threshold", "contrast"), "threshold",
          role="'threshold': white text above cell_contrast_thresh; 'contrast': by contrast with the cell colour"),
    Param("cell_contrast_thresh", float, 5.5, unit="|value|", role="Above it cell text is white (threshold mode)",
          tune="lower if mid-dark cells have hard-to-read black text"),
    Param("cell_fontsize", float, 9.2, unit="pt", range=(0, None), role="Cell value font size"),
    Param("cell_fontweight", str, "bold", role="Cell value font weight"),
    Param("placeholder_color", "color", "#94A3B8", unit="hex color", role="Colour of the dash in non-significant cells"),
    # [Rows]
    Param("ytick_fontsize", float, 9.8, unit="pt", range=(0, None), role="Row (cluster) label size"),
    Param("ytick_fontweight", str, "bold", role="Row label font weight"),
    # [Columns: species pairs under condition labels]
    Param("species_tick_labels", list, ["● Human", "◆ Mouse"], role="Tick labels of the two species columns per condition"),
    Param("c_human", "color", "#2563EB", unit="hex color", role="Colour of the human tick labels"),
    Param("c_mouse", "color", "#DC2626", unit="hex color", role="Colour of the mouse tick labels"),
    Param("xtick_fontsize", float, 11.0, unit="pt", range=(0, None), role="Species tick label size"),
    Param("xtick_rotation", float, 45.0, unit="degrees", role="Species tick label rotation"),
    Param("cond_label_fontsize", float, 11.5, unit="pt", range=(0, None), role="Condition label size"),
    Param("cond_label_y", float, -0.58, unit="data coords (rows)", role="Vertical position of the condition labels",
          tune="lower (more negative) moves them further below the species ticks"),
    # [Dividers]
    Param("divider_color", "color", "#1E293B", unit="hex color", role="Line between conditions"),
    Param("divider_lw", float, 1.4, unit="pt", range=(0, None), role="Width of the line between conditions"),
    Param("species_divider_color", "color", "#CBD5E1", unit="hex color", role="Line between the two species of a condition"),
    Param("species_divider_lw", float, 0.7, unit="pt", range=(0, None), role="Width of the species divider"),
])


@uses_schema(SCHEMA)
def render_clustered_go_heatmap(
    ax,
    mat: np.ndarray,
    labels: list[str],
    params: dict,
    cond_names: list[str] | None = None,
):
    """Render formal publication-grade clustered GO biological process heatmap.

    All visual attributes come dynamically from ``params`` via ``.get()``.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to draw the heatmap on.
    mat : np.ndarray
        2D array of shape (n_rows, n_cols) containing signed scores (e.g. signed -log10 FDR).
    labels : list[str]
        Row labels (functional cluster descriptions).
    params : dict
        Configuration dictionary containing visual attributes.
    cond_names : list[str] | None
        Display names for major conditions (e.g. ['Acute D1', 'Acute D3', ...]).

    Returns
    -------
    im : matplotlib.image.AxesImage
        The rendered image artist for colorbar binding.
    """
    n_rows, n_cols = mat.shape
    vmax = float(params.get("vmax", 10.0))
    cmap_name = params.get("cmap", "RdBu_r")
    cmap = getattr(plt.cm, cmap_name, plt.cm.RdBu_r)
    im = ax.imshow(mat, cmap=cmap, aspect="auto", vmin=-vmax, vmax=vmax, interpolation="nearest")

    div_color = params.get("divider_color", "#1E293B")
    div_lw = float(params.get("divider_lw", 1.4))
    sp_div_color = params.get("species_divider_color", "#CBD5E1")
    sp_div_lw = float(params.get("species_divider_lw", 0.7))

    # Condition boundaries (solid vertical lines)
    n_conds = n_cols // 2
    for c in range(1, n_conds):
        ax.axvline(c * 2 - 0.5, color=div_color, lw=div_lw, zorder=2)

    # Intra-condition Human / Mouse boundary (subtle dotted lines)
    for c in range(n_conds):
        ax.axvline(c * 2 + 0.5, color=sp_div_color, lw=sp_div_lw, ls=":", zorder=2)

    cell_sig = float(params.get("cell_sig_thresh", 1.3))
    cell_contrast = float(params.get("cell_contrast_thresh", 5.5))
    cell_fs = float(params.get("cell_fontsize", 9.2))
    cell_fw = params.get("cell_fontweight", "bold")

    # Annotate numeric values inside cells
    for r in range(n_rows):
        for c in range(n_cols):
            val = mat[r, c]
            if np.abs(val) >= cell_sig:
                if params.get("cell_text_color_mode", "threshold") == "contrast":
                    # White or black by contrast with the cell's actual colour
                    # (the two ends of a diverging map darken at different rates).
                    txt_color = readable_text_color(im.cmap(im.norm(val)), "white", "black")
                else:
                    txt_color = "white" if np.abs(val) > cell_contrast else "black"
                ax.text(c, r, f"{val:+.1f}", ha="center", va="center",
                        fontsize=cell_fs, fontweight=cell_fw, color=txt_color, zorder=4)
            else:
                ax.text(c, r, "-", ha="center", va="center",
                        fontsize=cell_fs + 0.3, color=params.get("placeholder_color", "#94A3B8"), zorder=4)

    # X-axis ticks: species indicators, rotated with configurable font
    xtick_fs = float(params.get("xtick_fontsize", 11.0))
    xtick_rot = float(params.get("xtick_rotation", 45.0))
    c_human = params.get("c_human", "#2563EB")
    c_mouse = params.get("c_mouse", "#DC2626")

    sp_labels = list(params.get("species_tick_labels", ["● Human", "◆ Mouse"]))
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(sp_labels * n_conds, fontsize=xtick_fs, fontweight="bold",
                       rotation=xtick_rot, ha="right" if xtick_rot else "center", rotation_mode="anchor")
    for idx, tick_label in enumerate(ax.get_xticklabels()):
        tick_label.set_color(c_human if idx % 2 == 0 else c_mouse)

    # Secondary x-labels for Conditions above the plot
    if cond_names is None:
        cond_names = [f"Cond {i+1}" for i in range(n_conds)]
    cond_y = float(params.get("cond_label_y", -0.58))
    cond_fs = float(params.get("cond_label_fontsize", 11.5))
    for ci, cname in enumerate(cond_names):
        col_center = ci * 2 + 0.5
        ax.text(col_center, cond_y, cname, ha="center", va="bottom",
                fontsize=cond_fs, fontweight="bold", color="#0F172A", clip_on=False)

    ytick_fs = float(params.get("ytick_fontsize", 9.8))
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(labels, fontsize=ytick_fs, fontweight=params.get("ytick_fontweight", "bold"))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return im
