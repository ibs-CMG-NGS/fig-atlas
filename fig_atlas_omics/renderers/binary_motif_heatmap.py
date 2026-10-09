"""Binary motif-presence heatmap with tier annotation.

Synthesized (Case C) from final_target_summary_figure panel C: target genes
(grouped/annotated by tier) against headline motif has_* booleans
(TRUE/FALSE -> dark/light cells), with a thin stripe coloring each gene by
its tier.

Two orientations:
- ``vertical`` (default): genes are rows, motifs are columns, tier stripe on
  the left.
- ``horizontal``: genes are columns, motifs are rows, tier stripe on top --
  for long gene lists that must fit a fixed page height (the list then
  grows sideways across the full figure width instead of downwards).
"""

from __future__ import annotations

import textwrap

import numpy as np
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch

from fig_atlas.params import text_param
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, typography, uses_schema

SCHEMA = Schema("binary_motif_heatmap", params=[
    *typography(title_size=13, axes_label_size=12.0, tick_label_size=8, legend_fontsize=CODE_DEFAULT),
    Param("orientation", ("vertical", "horizontal"), "vertical",
          role="'vertical': genes as rows; 'horizontal': genes as columns, motifs as rows"),
    # [Input]
    Param("row_col", str, "gene", role="Column of df with the gene names"),
    Param("tier_col", str, "tier", role="Column of df with each gene's tier"),
    Param("cols", list, None, role="Presence columns to show, in order (default: every has_* column)"),
    Param("col_rename_map", dict, {}, open_keys=True, role="Display label per presence column"),
    Param("col_strip_prefix", str, None, role="Prefix removed from presence column names for display (e.g. 'has_')"),
    Param("row_order", list, None, role="Gene order (default: order of first appearance)"),
    Param("tier_order", list, None, role="Tier order in the stripe and legend"),
    # [Cells]
    Param("present_color", "color", "#2b7bba", unit="hex color", role="Fill of cells where the motif is present"),
    Param("absent_color", "color", "#ffffff", unit="hex color", role="Fill of cells where it is absent"),
    Param("cell_border_color", "color", "#999999", unit="hex color", role="Cell border colour"),
    Param("cell_border_width", float, 0.7, unit="pt", range=(0, None), role="Cell border width"),
    Param("cell_marks", object, None, role="Boolean matrix (genes x cols): a dot on those cells (set by the script)"),
    Param("cell_mark_color", "color", "white", unit="color", role="Colour of the cell-mark dots"),
    Param("cell_mark_edgecolor", "color", "none", unit="color", role="Outline of the cell-mark dots"),
    Param("cell_mark_size", float, 4.0, unit="pt^2 (marker area)", range=(0, None), role="Size of the cell-mark dots"),
    Param("cell_mark_label", str, None, role="Legend text for the cell marks (none = no legend entry)"),
    Param("cell_mark_legend_xy", list, [1.02, -0.12], unit="axes fraction (x, y)", role="Position of the cell-mark legend entry"),
    Param("cell_mark_legend_scale", float, 8.0, unit="x cell_mark_size", role="Size of the legend dot relative to the cell dots"),
    # [Tier stripe]
    Param("tier_colors", dict, {}, open_keys=True, unit="hex color per tier", role="Colour per tier in the stripe"),
    Param("tier_label_map", dict, {}, open_keys=True, role="Legend label per tier"),
    Param("tier_bar_label", str, "Tier", role="Label of the tier stripe"),
    Param("stripe_ratio", float, CODE_DEFAULT, unit="fraction of matrix size", role="Tier stripe thickness (default 0.024/0.72)"),
    Param("show_tier_legend", bool, True, role="Show the tier legend"),
    Param("tier_legend_title", str, "Tier", role="Tier legend title"),
    Param("tier_legend_bbox", list, (1.08, 0.64), unit="axes fraction (x, y)", role="Anchor of the tier legend"),
    Param("tier_legend_frameon", bool, True, role="Frame around the tier legend"),
    Param("show_binary_legend", bool, True, role="Show the present / absent legend"),
    Param("binary_legend_bbox", list, [1.08, 0.72, 0.025, 0.26], unit="figure fraction [x, y, w, h]",
          role="Box of the present / absent legend"),
    Param("present_label", str, "present", role="Legend text for present"),
    Param("absent_label", str, "absent", role="Legend text for absent"),
    # [Labels]
    Param("labels_title", str, "C. Headline Motif Presence (Tier1+2+top Tier3, n=39)", role="Panel title"),
    Param("title_pad", float, 10, unit="pt", role="Gap between title and matrix"),
    Param("labels_xlabel", str, "", role="x-axis title"),
    Param("labels_ylabel", str, "", role="y-axis title"),
    Param("xlabel_pad", float, 10, unit="pt", role="Gap between x tick labels and the x-axis title"),
    Param("ylabel_pad", float, CODE_DEFAULT, unit="pt", role="Gap before the y-axis title (default 10, or 40 when horizontal)"),
    Param("ylabel_position", ("left", "right"), "left", role="Side of the y-axis title"),
    Param("xtick_rotation", float, 90, unit="degrees", role="Column label rotation"),
    Param("xtick_ha", ("left", "center", "right"), "center", role="Horizontal alignment of column labels"),
    Param("row_label_wrap_width", int, 28, unit="characters", range=(1, None), role="Wrap row labels at this width"),
    Param("gene_label_fontsize", float, CODE_DEFAULT, unit="pt", role="Gene label size (horizontal; default tick_label_size)"),
    Param("gene_label_rotation", float, 90, unit="degrees", role="Gene label rotation (horizontal)"),
    # [Row summary bars, horizontal only]
    Param("row_bar_values", list, None, role="One summary value per motif row, drawn as a bar right of the matrix"),
    Param("row_bar_labels", list, None, role="Text at each bar (default: the value)"),
    Param("row_bar_title", str, None, role="Title above the summary bars"),
    Param("row_bar_title_pad", float, 3, unit="pt", role="Gap between the bars and their title"),
    Param("row_bar_gap", float, 0.02, unit="figure fraction", role="Gap between matrix and summary bars"),
    Param("row_bar_width", float, 0.2, unit="figure fraction", role="Width of the summary bar area"),
    Param("row_bar_height", float, 0.62, unit="row units", range=(0, 1), role="Bar thickness"),
    Param("row_bar_color", "color", "#64748b", unit="hex color", role="Summary bar colour"),
    Param("row_bar_max", float, CODE_DEFAULT, unit="value units", role="Bar axis maximum (default: largest value)"),
    Param("row_bar_fontsize", float, CODE_DEFAULT, unit="pt", role="Bar label size (default tick_label_size)"),
    # [Layout, figure-relative]
    Param("gs_left", float, 0.08, unit="[0-1] figure fraction", role="Left edge of the grid"),
    Param("gs_right", float, CODE_DEFAULT, unit="[0-1] figure fraction", role="Right edge of the grid (0.80 vertical / 0.86 horizontal)"),
    Param("gs_top", float, CODE_DEFAULT, unit="[0-1] figure fraction", role="Top edge of the grid (0.90 vertical / 0.94 horizontal)"),
    Param("gs_bottom", float, CODE_DEFAULT, unit="[0-1] figure fraction", role="Bottom edge of the grid (0.25 vertical / 0.15 horizontal)"),
    Param("gs_space", float, CODE_DEFAULT, unit="fraction of the grid", role="Gap between tier stripe and matrix"),
])


@uses_schema(SCHEMA)
def render_binary_motif_heatmap(fig, df, params):
    """Draw a binary motif-presence heatmap onto ``fig`` (Figure/SubFigure).

    ``df`` is long-format with one row per gene: a row_id column (gene),
    a tier column, and the has_* boolean columns listed in ``cols``.
    params: orientation ('vertical' | 'horizontal'),
            row_col('gene'), tier_col('tier'), cols (list of has_* columns),
            col_rename_map, col_strip_prefix, row_order(list), tier_order(list),
            present_color('#2b7bba'), absent_color('#ffffff'),
            tier_colors (dict tier -> hex), show_tier_legend,
            tier_legend_bbox, show_binary_legend, binary_legend_bbox,
            cell_border_color('#999999'), cell_border_width,
            xtick_rotation, row_label_wrap_width,
            gs_left/gs_right/gs_top/gs_bottom (grid margins in the
            fig/subfigure), stripe_ratio (tier stripe thickness relative to
            the matrix), gs_space (gap between stripe and matrix),
            gene_label_fontsize, gene_label_rotation (horizontal only),
            row_bar_values / row_bar_labels / row_bar_title (horizontal
            only: one summary bar per motif row, right of the matrix),
            row_bar_gap, row_bar_width, row_bar_height, row_bar_color,
            row_bar_max, row_bar_fontsize, row_bar_title_pad,
            cell_marks (bool matrix genes x cols: dot on those cells), cell_mark_color,
            cell_mark_size, cell_mark_label, cell_mark_legend_xy,
            labels_title, title_pad, axes_label_size, tick_label_size,
            title_size
    """
    title_sz = params.get("title_size", 13)
    t_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    row_col = params.get("row_col", "gene")
    tier_col = params.get("tier_col", "tier")
    cols = params.get("cols") or [c for c in df.columns if str(c).startswith("has_")]
    cols = [c for c in cols if c in df.columns]

    row_order = params.get("row_order") or list(df[row_col].unique())
    df = df.set_index(row_col).loc[row_order]
    tiers = df[tier_col].tolist()

    _TRUE = {True, 1, 1.0, "TRUE", "True", "true"}
    mat = np.array([[True if v in _TRUE else False for v in df[c]]
                    for c in cols], dtype=bool).T  # (n_rows, n_cols)
    n_rows, n_cols = mat.shape

    present = params.get("present_color", "#2b7bba")
    absent = params.get("absent_color", "#ffffff")
    codes = mat.astype(int)  # 1 present, 0 absent

    tier_order = params.get("tier_order") or list(pd.Series(tiers).unique())
    tier_colors = params.get("tier_colors", {})
    default_tiers = {
        0: "#bdbdbd", 1: "#d73027", 2: "#f46d43", 3: "#fee08b", 4: "#74add1",
    }
    color_map = {t: tier_colors.get(t, default_tiers.get(t, "#999999"))
                 for t in tier_order}

    # Main binary matrix: shape (n_rows, n_cols, 3)
    cmap = {0: absent, 1: present}
    rgb = np.array([[[*to_rgb(cmap[int(codes[r, c])])] for c in range(n_cols)]
                    for r in range(n_rows)])

    border_color = params.get("cell_border_color", "#999999")
    border_width = float(params.get("cell_border_width", 0.7))

    col_rename_map = params.get("col_rename_map", {})
    strip_prefix = params.get("col_strip_prefix")
    col_labels = []
    for c in cols:
        label = col_rename_map.get(c, c)
        if strip_prefix and str(label).startswith(strip_prefix):
            label = str(label)[len(strip_prefix):]
        col_labels.append(label)

    horizontal = params.get("orientation", "vertical") == "horizontal"
    stripe_ratio = float(params.get("stripe_ratio", 0.024 / 0.72))

    if horizontal:
        # Genes along x, motifs along y, tier stripe as a thin top row.
        gs = fig.add_gridspec(2, 1, height_ratios=[stripe_ratio, 1.0],
                              hspace=float(params.get("gs_space", 0.02)),
                              left=float(params.get("gs_left", 0.08)), right=float(params.get("gs_right", 0.86)),
                              top=float(params.get("gs_top", 0.90)), bottom=float(params.get("gs_bottom", 0.25)))
        ax_stripe = fig.add_subplot(gs[0, 0])
        ax = fig.add_subplot(gs[1, 0])

        stripe = np.array([[[*to_rgb(color_map.get(t, "#999999"))] for t in tiers]])  # (1, n_genes, 3)
        ax_stripe.imshow(stripe, aspect="auto", interpolation="nearest")
        ax_stripe.set_xlim(-0.5, n_rows - 0.5)
        ax_stripe.set_ylim(0.5, -0.5)
        ax_stripe.set_yticks([0])
        ax_stripe.set_yticklabels([params.get("tier_bar_label", "Tier")], fontsize=t_sz, fontweight="bold")
        ax_stripe.set_xticks([])
        ax_stripe.set_xticks(np.arange(-0.5, n_rows, 1), minor=True)
        ax_stripe.grid(which="minor", axis="x", color=border_color, linewidth=border_width)
        ax_stripe.tick_params(axis="both", which="both", length=0)
        for spine in ax_stripe.spines.values():
            spine.set_color(border_color)
            spine.set_linewidth(border_width)

        ax.imshow(rgb.transpose(1, 0, 2), aspect="auto", interpolation="nearest")
        ax.set_xlim(-0.5, n_rows - 0.5)
        ax.set_ylim(n_cols - 0.5, -0.5)
        ax.set_xticks(range(n_rows))
        ax.set_xticklabels([str(g) for g in row_order],
                           fontsize=float(params.get("gene_label_fontsize", t_sz)),
                           rotation=float(params.get("gene_label_rotation", 90)), ha="center")
        ax.set_yticks(range(n_cols))
        ax.set_yticklabels(col_labels, fontsize=t_sz)
        ax.tick_params(axis="both", which="both", length=0)
        ax.set_xticks(np.arange(-0.5, n_rows, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n_cols, 1), minor=True)
        ax.grid(which="minor", color=border_color, linewidth=border_width)
        for spine in ax.spines.values():
            spine.set_color(border_color)
            spine.set_linewidth(border_width)
        title_ax = ax_stripe
    else:
        # Genes down y, motifs along x, tier stripe as a thin left column.
        stripe = np.array([[[*to_rgb(color_map.get(t, "#999999"))]] for t in tiers])  # (n_genes, 1, 3)
        gs = fig.add_gridspec(1, 2, width_ratios=[stripe_ratio, 1.0],
                              wspace=float(params.get("gs_space", 0.010)),
                              left=float(params.get("gs_left", 0.08)), right=float(params.get("gs_right", 0.80)),
                              top=float(params.get("gs_top", 0.94)), bottom=float(params.get("gs_bottom", 0.15)))
        ax_stripe = fig.add_subplot(gs[0, 0])
        ax = fig.add_subplot(gs[0, 1])

        ax_stripe.imshow(stripe, aspect="auto", interpolation="nearest")
        ax_stripe.set_xlim(-0.5, 0.5)
        ax_stripe.set_ylim(n_rows - 0.5, -0.5)
        ax_stripe.set_xticks([0])
        ax_stripe.set_xticklabels([params.get("tier_bar_label", "Tier")], fontsize=t_sz,
                                  fontweight="bold", rotation=float(params.get("xtick_rotation", 90)),
                                  ha=params.get("xtick_ha", "center"))
        ax_stripe.set_yticks([])
        ax_stripe.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
        ax_stripe.grid(which="minor", color=border_color, linewidth=border_width)
        ax_stripe.tick_params(axis="both", which="both", length=0)
        for spine in ax_stripe.spines.values():
            spine.set_color(border_color)
            spine.set_linewidth(border_width)

        ax.imshow(rgb, aspect="auto", interpolation="nearest")
        ax.set_xlim(-0.5, n_cols - 0.5)
        ax.set_ylim(n_rows - 0.5, -0.5)
        ax.set_xticks(range(n_cols))
        ax.set_xticklabels(col_labels, fontsize=t_sz,
                           rotation=float(params.get("xtick_rotation", 90)),
                           ha=params.get("xtick_ha", "center"))
        wrap_w = int(params.get("row_label_wrap_width", 28))
        row_labels = [textwrap.fill(str(t), width=wrap_w, break_long_words=False)
                      for t in row_order]
        ax.set_yticks(range(n_rows))
        ax.set_yticklabels(row_labels, fontsize=t_sz)
        ax.yaxis.tick_right()
        ax.tick_params(axis="both", which="both", length=0)
        ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
        ax.grid(which="minor", color=border_color, linewidth=border_width)
        for spine in ax.spines.values():
            spine.set_color(border_color)
            spine.set_linewidth(border_width)
        title_ax = ax

    title = text_param(params, "labels_title", "C. Headline Motif Presence (Tier1+2+top Tier3, n=39)")
    title_ax.set_title(title, fontsize=title_sz, fontweight="bold", loc="center",
                       pad=float(params.get("title_pad", 10)))

    xlabel = text_param(params, "labels_xlabel", "")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=float(params.get("axes_label_size", 12.0)),
                      fontweight="bold", labelpad=float(params.get("xlabel_pad", 10)))

    ylabel = text_param(params, "labels_ylabel", "")
    if ylabel:
        y_pos = params.get("ylabel_position", "left")
        if y_pos == "left":
            (ax if horizontal else ax_stripe).set_ylabel(
                ylabel, fontsize=float(params.get("axes_label_size", 12.0)),
                fontweight="bold", labelpad=float(params.get("ylabel_pad", 10)))
        else:
            ax.yaxis.set_label_position("right")
            ax.set_ylabel(ylabel, fontsize=float(params.get("axes_label_size", 12.0)),
                          fontweight="bold", labelpad=float(params.get("ylabel_pad", 40)))

    # --- Optional cell marks: a dot on cells with an extra line of evidence
    # (e.g. public ChIP binding for that motif's TF at that gene). Shape
    # (n genes, n motif columns), in row_order x cols order.
    marks = params.get("cell_marks")
    if marks is not None:
        mk = np.asarray(marks, dtype=bool)
        gi, ci = np.nonzero(mk)
        xs, ys = (gi, ci) if horizontal else (ci, gi)
        ax.scatter(xs, ys, s=float(params.get("cell_mark_size", 4.0)), c=params.get("cell_mark_color", "white"),
                   edgecolors=params.get("cell_mark_edgecolor", "none"), linewidths=0, zorder=5)
        if params.get("cell_mark_label"):
            lx, ly = params.get("cell_mark_legend_xy", [1.02, -0.12])
            ax.scatter([lx], [ly], s=float(params.get("cell_mark_size", 4.0)) * float(params.get("cell_mark_legend_scale", 8.0)),
                       transform=ax.transAxes,
                       c=params.get("present_color", "#2b7bba"), marker="s", clip_on=False, zorder=5)
            ax.scatter([lx], [ly], s=float(params.get("cell_mark_size", 4.0)), transform=ax.transAxes,
                       c=params.get("cell_mark_color", "white"), clip_on=False, zorder=6)
            ax.text(lx + 0.015, ly, params["cell_mark_label"], transform=ax.transAxes, va="center", ha="left",
                    fontsize=float(params.get("legend_fontsize", t_sz)))

    # --- Optional per-motif summary bars beside the matrix (horizontal
    # orientation only; one bar per motif row), e.g. how many genes of a
    # larger population carry each motif, while the matrix shows examples.
    row_vals = params.get("row_bar_values")
    if horizontal and row_vals is not None:
        gap, width = float(params.get("row_bar_gap", 0.02)), float(params.get("row_bar_width", 0.2))
        ax_bar = ax.inset_axes([1 + gap, 0, width, 1])
        ax_bar.barh(range(n_cols), list(row_vals), height=float(params.get("row_bar_height", 0.62)),
                    color=params.get("row_bar_color", "#64748b"), edgecolor="none")
        ax_bar.set_ylim(ax.get_ylim())
        vmax = float(params.get("row_bar_max", max(list(row_vals) + [1])))
        ax_bar.set_xlim(0, vmax)
        bar_fs = float(params.get("row_bar_fontsize", t_sz))
        for yi, (v, lab) in enumerate(zip(row_vals, params.get("row_bar_labels") or [f"{v:,}" for v in row_vals])):
            ax_bar.text(v + vmax * 0.02, yi, lab, va="center", ha="left", fontsize=bar_fs, clip_on=False)
        ax_bar.set_yticks([])
        ax_bar.set_xticks([])
        for side, spine in ax_bar.spines.items():
            spine.set_visible(side == "left")
            spine.set_linewidth(border_width)
            spine.set_color(border_color)
        if params.get("row_bar_title"):
            ax_bar.set_title(params["row_bar_title"], fontsize=bar_fs, loc="left",
                             pad=float(params.get("row_bar_title_pad", 3)))

    # --- Legends to the right of the matrix ---
    legend_fontsize = float(params.get("legend_fontsize", t_sz))
    if params.get("show_binary_legend", True):
        # Vertical 2-block bar: present (top) / absent (bottom)
        bin_bbox = params.get("binary_legend_bbox", [1.08, 0.72, 0.025, 0.26])
        ax_leg = ax.inset_axes(bin_bbox)
        grad = np.array([[[*to_rgb(present)]], [[*to_rgb(absent)]]])
        ax_leg.imshow(grad, aspect="auto", interpolation="nearest")
        ax_leg.set_xticks([])
        ax_leg.set_yticks([])
        for spine in ax_leg.spines.values():
            spine.set_color(border_color)
            spine.set_linewidth(border_width)
        ax_leg.text(1.35, 0.75, params.get("present_label", "present"),
                    transform=ax_leg.transAxes, ha="left", va="center",
                    fontsize=legend_fontsize)
        ax_leg.text(1.35, 0.25, params.get("absent_label", "absent"),
                    transform=ax_leg.transAxes, ha="left", va="center",
                    fontsize=legend_fontsize)

    if params.get("show_tier_legend", True):
        tier_label_map = params.get("tier_label_map", {})
        handles = [
            Patch(facecolor=color_map[t], edgecolor=border_color, linewidth=border_width,
                  label=tier_label_map.get(t, f"{t}"))
            for t in tier_order if t in color_map
        ]
        tier_bbox = params.get("tier_legend_bbox", (1.08, 0.64))
        leg = ax.legend(handles=handles,
                        title=params.get("tier_legend_title", "Tier"),
                        loc="upper left",
                        bbox_to_anchor=tier_bbox,
                        fontsize=legend_fontsize, title_fontsize=legend_fontsize,
                        frameon=params.get("tier_legend_frameon", True),
                        edgecolor="#cccccc", facecolor="white",
                        handlelength=1.2, handleheight=1.2, borderpad=0.5,
                        labelspacing=0.4)
        if leg.get_title():
            leg.get_title().set_fontweight("bold")

    return mat
