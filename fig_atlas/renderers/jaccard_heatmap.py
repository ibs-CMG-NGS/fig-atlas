"""Annotated matrix heatmap for Jaccard-style cross-tabulations.

Synthesized (Case C) from the go_summary_figure reference: a row x column
matrix of continuous values where each cell shows a text annotation such as
"0.13(22)" (value + shared-term count) and cells whose count is zero are
drawn blank. All visual attributes come from ``params``.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd

from ..params import text_param


from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("jaccard_heatmap", params=[
    # [Data]
    Param("row_col", str, "pattern_class", role="Column giving the matrix rows"),
    Param("col_col", str, "concordance_class", role="Column giving the matrix columns"),
    Param("value_col", str, "jaccard", role="Column coloured in each cell"),
    Param("count_col", str, "n_shared_terms", role="Column with the count printed in each cell"),
    Param("row_order", list, None, role="Row order (default: order in the data)"),
    Param("col_order", list, None, role="Column order (default: order in the data)"),
    # [Colour scale]
    Param("cmap", "cmap", "Reds", role="Colormap of the cells"),
    Param("vmin", float, 0.0, unit="value units", role="Lower end of the colour scale"),
    Param("vmax", float, None, unit="value units", role="Upper end of the colour scale (default: data maximum)"),
    Param("blank_when_count_zero", bool, True, role="Leave cells with a zero count blank"),
    Param("blank_color", "color", "white", unit="color", role="Colour of blank cells"),
    Param("show_colorbar", bool, True, role="Show the colourbar"),
    Param("colorbar_label", str, "Jaccard", role="Colourbar title"),
    Param("colorbar_loc", ("right", "left", "top", "bottom"), "right", role="Side of the colourbar"),
    Param("colorbar_shrink", float, 0.8, unit="fraction of the axes height", range=(0, 1), role="Colourbar length"),
    # [Cells]
    Param("cell_text_format", str, "{value:.2f}({count:d})", role="Cell text; fields value and count"),
    Param("cell_text_color", str, "black", role="Cell text colour, or 'auto' for white on dark cells"),
    Param("cell_text_size", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Cell text size (default tick_label_size)"),
    Param("cell_border_color", "color", "white", unit="color", role="Grid line colour between cells"),
    Param("cell_border_width", float, 1.0, unit="pt", range=(0, None), role="Grid line width between cells"),
    # [Labels]
    Param("labels_title", str, "Jaccard Heatmap", role="Panel title"),
    Param("xtick_rotation", float, 45, unit="degrees", role="Column label rotation"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Colourbar title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Row and column label font size"),
])


@uses_schema(SCHEMA)
def render_jaccard_heatmap(ax, df, params):
    """Draw an annotated value-count matrix heatmap onto ``ax``.

    params: row_col('pattern_class'), col_col('concordance_class'),
            value_col('jaccard'), count_col('n_shared_terms'),
            row_order(list), col_order(list),
            cmap('Reds'), vmin, vmax (auto from data when vmax omitted),
            cell_text_format('{value:.2f}({count:d})'),
            blank_when_count_zero(True -- count==0 cells render blank),
            cell_text_color('black' or 'auto' for white-on-dark),
            cell_text_size, cell_border_color, cell_border_width,
            xtick_rotation, show_colorbar, colorbar_label, colorbar_loc,
            colorbar_shrink, labels_title, axes_label_size,
            tick_label_size, title_size
    """
    title_sz = params.get("title_size", 13)
    a_sz = params.get("axes_label_size", 11)
    t_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    row_col = params.get("row_col", "pattern_class")
    col_col = params.get("col_col", "concordance_class")
    value_col = params.get("value_col", "jaccard")
    count_col = params.get("count_col", "n_shared_terms")

    row_order = params.get("row_order") or list(dict.fromkeys(df[row_col]))
    col_order = params.get("col_order") or list(dict.fromkeys(df[col_col]))

    counts = (df.pivot_table(index=row_col, columns=col_col, values=count_col,
                             aggfunc="first")
                .reindex(index=row_order, columns=col_order))
    values = (df.pivot_table(index=row_col, columns=col_col, values=value_col,
                             aggfunc="first")
                .reindex(index=row_order, columns=col_order))

    vmat = values.to_numpy(dtype=float)
    nmat = counts.to_numpy(dtype=float)

    blank_zero = bool(params.get("blank_when_count_zero", True))
    draw_mask = ~np.isnan(vmat)
    if blank_zero and nmat is not None:
        draw_mask &= ~(np.nan_to_num(nmat) <= 0)

    vmax = params.get("vmax")
    if vmax is None:
        finite = vmat[draw_mask & np.isfinite(vmat)]
        vmax = float(finite.max()) if finite.size else 1.0
    vmin = float(params.get("vmin", 0.0))

    masked = np.ma.array(vmat, mask=~draw_mask)
    import matplotlib as mpl
    import matplotlib.colors as mcolors
    cmap = params.get("cmap", "Reds")
    cmap = mpl.colormaps[str(cmap)].copy()
    cmap.set_bad(color=params.get("blank_color", "white"))

    im = ax.imshow(masked, cmap=cmap, vmin=vmin, vmax=vmax,
                   aspect="auto", interpolation="nearest")

    # Cell borders via a minor-tick grid (imshow has no per-cell borders).
    n_rows, n_cols = vmat.shape
    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color=params.get("cell_border_color", "white"),
            linewidth=float(params.get("cell_border_width", 1.0)))
    ax.tick_params(which="minor", length=0)

    text_color_mode = params.get("cell_text_color", "black")
    text_color = "black"
    if text_color_mode == "auto":
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        text_color = [
            "white" if (draw_mask[r, c] and norm(vmat[r, c]) > 0.6) else "black"
            for r in range(n_rows) for c in range(n_cols)
        ]

    text_fmt = params.get("cell_text_format", "{value:.2f}({count:d})")
    text_size = params.get("cell_text_size", t_sz)
    for r in range(n_rows):
        for c in range(n_cols):
            if not draw_mask[r, c]:
                continue
            label = text_fmt.format(value=vmat[r, c], count=int(nmat[r, c]))
            ax.text(c, r, label, ha="center", va="center",
                    fontsize=text_size, color=text_color)

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_order, fontsize=t_sz,
                       rotation=float(params.get("xtick_rotation", 45)), ha="right")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(row_order, fontsize=t_sz)

    if params.get("show_colorbar", True):
        cbar = ax.figure.colorbar(im, ax=ax,
                                  location=params.get("colorbar_loc", "right"),
                                  shrink=float(params.get("colorbar_shrink", 0.8)),
                                  pad=0.02, use_gridspec=False)
        cbar.set_label(text_param(params, "colorbar_label", "Jaccard"),
                       fontsize=a_sz)
        cbar.ax.tick_params(labelsize=t_sz)

    title = text_param(params, "labels_title", "Jaccard Heatmap")
    ax.set_title(title, fontsize=title_sz, fontweight="bold")

    return values
