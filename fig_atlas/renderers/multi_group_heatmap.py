"""Multi-group (condition-annotated) clustered heatmap.

Ported from Filtered_*_mg_heatmap bundles (common DEG heatmap and the
time-series cluster heatmaps). Distinct from the simpler ``render_heatmap``:
samples are pre-assigned to named groups (e.g. Control/1D/3D) with a color
annotation strip above the heatmap, and rows are optionally re-ordered by
hierarchical clustering rather than by padj/log2FC.
"""

from __future__ import annotations

import ast

import numpy as np
import pandas as pd


from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("multi_group_heatmap", params=[
    # [Data]
    Param("gene_label_col", str, "gene_label", role="Column with the row (gene) labels"),
    Param("sample_columns", list, None, role="Sample columns to show (default: every numeric column)"),
    Param("sample_groups", dict, None, open_keys=True, role="Group name -> sample columns; orders and groups the columns"),
    Param("sample_rename_map", dict, {}, open_keys=True, role="Display label per raw sample name"),
    # [Clustering]
    Param("cluster_rows", bool, False, role="Cluster the rows and draw the row dendrogram"),
    Param("linkage", str, "average", role="scipy linkage method (average, complete, ward, ...)"),
    Param("metric", str, "euclidean", role="scipy distance metric for the clustering"),
    Param("dendro_width", float, 0.12, unit="fraction of the axes width", range=(0, 1), role="Width of the row dendrogram"),
    # [Colour scale]
    Param("cmap", "cmap", "RdBu_r", role="Colormap of the z-scores"),
    Param("z_auto", bool, True, role="Symmetric colour limits from the data; set false to use z_min/z_max"),
    Param("z_min", float, -2.0, unit="z-score", role="Lower colour limit when z_auto is false"),
    Param("z_max", float, 2.0, unit="z-score", role="Upper colour limit when z_auto is false"),
    Param("show_colorbar", bool, True, role="Show the colourbar"),
    Param("colorbar_pad", float, CODE_DEFAULT, unit="fraction of the axes width", range=(0, None),
          role="Gap between heatmap and colourbar (default 0.15 with gene labels and dendrogram, else 0.02)",
          tune="increase to widen the gap between heatmap and colorbar"),
    # [Group strip]
    Param("group_colors", dict, None, open_keys=True, unit="hex color", role="Strip colour per sample group"),
    Param("show_group_bar", bool, True, role="Show the group colour strip (columns stay grouped when off)"),
    Param("group_bar_height", float, 0.03, unit="fraction of the axes height", range=(0, None), role="Strip height"),
    Param("group_bar_position", ("top", "bottom"), "top", role="Strip above or below the heatmap"),
    Param("margin_left", float, None, unit="[0-1] fraction of the figure", range=(0, 1),
          role="Left edge of the heatmap block (default: matplotlib's figure.subplot.left)"),
    Param("margin_right", float, None, unit="[0-1] fraction of the figure", range=(0, 1),
          role="Right edge of the heatmap block, colour bar outside it (default: matplotlib's)",
          tune="lower if the colour bar's title is cut off"),
    Param("margin_bottom", float, None, unit="[0-1] fraction of the figure", range=(0, 1),
          role="Bottom edge of the heatmap block (default: matplotlib's)",
          tune="raise if the sample names below the heatmap are cut off"),
    Param("margin_top", float, None, unit="[0-1] fraction of the figure", range=(0, 1),
          role="Top edge of the heatmap block (default: matplotlib's)"),
    Param("show_group_legend", bool, True, role="Show the group legend"),
    # [Labels]
    Param("show_gene_labels", bool, True, role="Show the row labels"),
    Param("gene_fontsize", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Row label size (default tick_label_size)"),
    Param("show_col_labels", bool, True, role="Show the column labels"),
    Param("xtick_rotation", float, 90, unit="degrees", role="Column label rotation"),
    Param("labels_title", str, None, role="Panel title"),
    Param("title", str, None, role="Older name of labels_title, used when labels_title is not set"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Colourbar title font size"),
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
def render_multi_group_heatmap(fig, df, params):
    """Draw a group-annotated z-scored clustered heatmap onto ``fig``.

    params: gene_label_col, sample_columns(list), sample_groups(dict of
            group -> [columns]), group_colors(dict of group -> hex),
            cmap, linkage, metric, cluster_rows(bool), z_auto, z_min, z_max,
            show_gene_labels, gene_fontsize, show_col_labels, xtick_rotation,
            sample_rename_map, show_colorbar, show_group_bar (bool; columns
            are still grouped/ordered by sample_groups even when this is
            off, only the color strip + its legend are hidden),
            show_group_legend, group_bar_height (fraction of axes height),
            group_bar_position ('top'|'bottom'), dendro_width (fraction of
            axes width for the row dendrogram), labels_title / title,
            axes_label_size, tick_label_size, title_size

    A row dendrogram is drawn automatically whenever cluster_rows produces a
    linkage (matches the original bundle script, which always shows one when
    seaborn.clustermap's row_cluster=True -- there is no separate toggle).

    Returns ``(zdata, gene_labels, ax)`` (the main heatmap Axes, handy for
    e.g. aligning a companion plot's x-axis to it) or ``None`` when there was
    nothing to plot.
    """
    df = df.copy() if df is not None else pd.DataFrame()
    title_sz = params.get("title_size", 13)
    a_sz = params.get("axes_label_size", 11)
    t_sz = params.get("tick_label_size", 8)

    if df.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No heatmap data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    gene_col = params.get("gene_label_col", "gene_label")
    if gene_col not in df.columns:
        gene_col = next((c for c in ("symbol", "gene_id") if c in df.columns), None)

    sample_groups = _as_obj(params.get("sample_groups"), {})
    if sample_groups:
        group_order = list(sample_groups.keys())
        columns = [c for g in group_order for c in sample_groups[g] if c in df.columns]
        col_group = {c: g for g in group_order for c in sample_groups[g]}
    else:
        columns = _as_obj(params.get("sample_columns"), None) or [
            c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        columns = [c for c in columns if c in df.columns]
        group_order, col_group = [], {}

    if not columns:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No sample columns found", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    expr = df[columns].apply(pd.to_numeric, errors="coerce").dropna()
    gene_labels = (df.loc[expr.index, gene_col].astype(str).tolist()
                  if gene_col else [str(i) for i in expr.index])

    row_std = expr.std(axis=1, ddof=1).replace(0, np.nan)
    zdata = expr.sub(expr.mean(axis=1), axis=0).div(row_std, axis=0).fillna(0.0)

    lm = None
    if params.get("cluster_rows", False) and len(zdata) > 2:
        try:
            from scipy.cluster.hierarchy import linkage, dendrogram
            from scipy.spatial.distance import pdist
            lm = linkage(pdist(zdata, metric=params.get("metric", "euclidean")),
                        method=params.get("linkage", "average"))
            order = dendrogram(lm, no_plot=True)["leaves"]
            zdata = zdata.iloc[order]
            gene_labels = [gene_labels[i] for i in order]
        except ImportError:
            lm = None

    group_colors = _as_obj(params.get("group_colors"), {})
    # Column ordering/grouping (via sample_groups, above) always applies;
    # this only controls whether the color strip + its legend are drawn.
    show_strip = bool(group_order and group_colors) and bool(params.get("show_group_bar", True))
    group_bar_h = float(params.get("group_bar_height", 0.03)) if show_strip else 0.0
    show_dendro = lm is not None
    dendro_w = float(params.get("dendro_width", 0.12)) if show_dendro else 0.0

    grp_at_bottom = params.get("group_bar_position", "top") == "bottom"
    n_rows, n_cols = (2 if show_strip else 1), (2 if show_dendro else 1)
    if show_strip and grp_at_bottom:
        heatmap_row, grp_row = 0, 1
        height_ratios = [1 - group_bar_h, group_bar_h]
    else:
        heatmap_row, grp_row = (1, 0) if show_strip else (0, 0)
        height_ratios = [group_bar_h, 1 - group_bar_h] if show_strip else [1]
    gs = fig.add_gridspec(
        n_rows, n_cols,
        height_ratios=height_ratios,
        width_ratios=[dendro_w, 1 - dendro_w] if show_dendro else [1],
        hspace=0.01, wspace=0.02,
        **{side: float(params.get(f"margin_{side}")) for side in ("left", "right", "bottom", "top")
           if params.get(f"margin_{side}") is not None},
    )
    ax = fig.add_subplot(gs[heatmap_row, n_cols - 1])
    ax_grp = fig.add_subplot(gs[grp_row, n_cols - 1]) if show_strip else None
    ax_dendro = fig.add_subplot(gs[heatmap_row, 0]) if show_dendro else None

    if ax_dendro is not None:
        from scipy.cluster.hierarchy import dendrogram as draw_dendro
        draw_dendro(lm, ax=ax_dendro, orientation="left", no_labels=True,
                   link_color_func=lambda i: "black")
        ax_dendro.axis("off")
        ax_dendro.set_ylim(10 * len(zdata), 0)

    cmap = params.get("cmap", "RdBu_r")
    if params.get("z_auto", True):
        absmax = float(np.nanmax(np.abs(zdata.to_numpy()))) if zdata.size else 1.0
        vmin, vmax = -absmax, absmax
    else:
        vmin = float(params.get("z_min", -2.0))
        vmax = float(params.get("z_max", 2.0))

    im = ax.imshow(zdata, cmap=cmap, aspect="auto", interpolation="nearest",
                   vmin=vmin, vmax=vmax)

    if ax_grp is not None:
        strip = np.arange(len(columns)).reshape(1, -1)
        from matplotlib.colors import ListedColormap
        uniq_groups = list(dict.fromkeys(col_group[c] for c in columns))
        strip_cmap = ListedColormap([group_colors.get(g, "#cccccc") for g in uniq_groups])
        strip_idx = np.array([[uniq_groups.index(col_group[c]) for c in columns]])
        ax_grp.imshow(strip_idx, cmap=strip_cmap, aspect="auto",
                     vmin=0, vmax=max(len(uniq_groups) - 1, 1))
        ax_grp.set_xticks([])
        ax_grp.set_yticks([])
        if params.get("show_group_legend", True):
            from matplotlib.patches import Patch
            handles = [Patch(color=group_colors.get(g, "#cccccc"), label=g) for g in uniq_groups]
            # One row above the group strip, attached to it: it moves with the
            # heatmap when the panel is fitted into its cell, and stays clear
            # of the centred title and the colour bar.
            ax_grp.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=len(handles),
                          fontsize=t_sz, frameon=False, handlelength=1.0, columnspacing=1.0, borderaxespad=0.2)

    rename_map = params.get("sample_rename_map", {})
    col_labels = [rename_map.get(c, c) for c in columns]
    rotation = float(params.get("xtick_rotation", 90))
    if params.get("show_col_labels", True):
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=rotation, fontsize=t_sz,
                           ha="center" if rotation in (0, 90) else "right")
    else:
        ax.set_xticks([])

    if params.get("show_gene_labels", True):
        gfs = params.get("gene_fontsize", t_sz)
        ax.set_yticks(range(len(gene_labels)))
        ax.set_yticklabels(gene_labels, fontsize=gfs)
        # Matches seaborn.clustermap's own convention (and the original
        # bundle render): when a row dendrogram occupies the left, gene
        # labels go on the right so the two never compete for the same space.
        if ax_dendro is not None:
            ax.yaxis.tick_right()
    else:
        ax.set_yticks([])

    title = params.get("labels_title") or params.get("title")
    if title:
        # Whichever axes sits in the top row carries the title.
        title_ax = ax_grp if (ax_grp is not None and grp_row == 0) else ax
        title_ax.set_title(title, fontsize=title_sz, fontweight="bold",
                           pad=10 if title_ax is ax_grp else None)

    if params.get("show_colorbar", True):
        # Right-side gene labels (when a dendrogram is present) need more
        # clearance than the default pad, or the colorbar sits on top of them.
        default_pad = 0.15 if (ax_dendro is not None and params.get("show_gene_labels", True)) else 0.02
        cbar = fig.colorbar(im, ax=[ax_grp, ax] if ax_grp is not None else ax,
                            fraction=0.03, pad=float(params.get("colorbar_pad", default_pad)))
        cbar.set_label("Z-score", fontsize=a_sz)
        cbar.ax.tick_params(labelsize=t_sz)

    return zdata, gene_labels, ax
