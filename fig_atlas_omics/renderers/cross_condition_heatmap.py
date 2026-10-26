"""Cross-condition GO/KEGG enrichment heatmap.

Ported from cross_condition_heatmap_semantic-{bp,kegg} bundles. Input is
long-format per (term, condition) rows (GO ID, GO Term, Condition,
Direction, Gene Ratio, Adjusted P-value, Signed -log10(FDR)); this pivots to
a term x condition matrix and draws it with a DISCRETE 7-bin diverging
color scale (UP/DOWN x FDR<0.001/0.01/0.05, plus "absent" for a
term/condition pair that never reached significance and so has no row in
the export) rather than a continuous colormap -- every present cell is
already significant (the upstream export only includes FDR<=0.05 hits), so
there is no "present but not significant" bin to represent.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd

from fig_atlas.params import text_param
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, typography, uses_schema

SCHEMA = Schema("cross_condition_heatmap", params=[
    *typography(title_size=13, tick_label_size=8),
    # [Input columns]
    Param("term_col", str, "GO Term", role="Column of df with the term (row) names"),
    Param("condition_col", str, "Condition", role="Column of df with the condition (column) names"),
    Param("value_col", str, "Signed -log10(FDR)", role="Column of df with the signed enrichment value"),
    Param("term_strip_pattern", str, None, role="Regex removed from term names before display (e.g. a GO ID prefix)"),
    # [Rows and columns]
    Param("condition_order", list, None, role="Column order (default: order of first appearance)"),
    Param("condition_rename_map", dict, {}, open_keys=True, role="Display label per condition", tune="raw name -> label"),
    Param("column_groups", list, None,
          role="Column group banners over the matrix, one item per group: label, start / end (column index), "
               "color, y_banner (1.04) and line_y (1.02) in axes fraction, line_width (2.2 pt)"),
    Param("cluster_rows", bool, True, role="Order rows by hierarchical clustering (needs > 2 rows)"),
    Param("metric", str, "euclidean", role="Row distance for clustering (scipy pdist metric)"),
    Param("linkage", str, "average", role="Linkage method for row clustering (scipy)"),
    Param("show_cluster_bands", bool, False, role="Split rows into clusters with a labelled header row each"),
    Param("cluster_dist_threshold", float, None, unit="dendrogram distance",
          role="Cut height for the cluster bands (default: cluster_dist_threshold_frac x the tallest merge)"),
    Param("cluster_dist_threshold_frac", float, 0.7, unit="fraction of the tallest merge", range=(0, 1),
          role="Relative cut height when cluster_dist_threshold is unset", tune="lower for more, smaller bands"),
    Param("cluster_band_color", "color", "#4F46E5", unit="hex color", role="Colour of the cluster band headers"),
    # [Colours]
    Param("colors", dict, {}, open_keys=True, unit="hex color per bin",
          role="Colour of each bin: up3/up2/up1/absent/down1/down2/down3 (FDR < 0.001 / 0.01 / 0.05)"),
    Param("bin_edges", list, [2.0, 3.0], unit="-log10 FDR",
          role="Edges between the 3 strength bins (default 2 and 3 = FDR 0.01 and 0.001)"),
    Param("show_cell_borders", bool, True, role="Draw a grid between cells"),
    Param("cell_border_color", "color", "lightgrey", unit="color", role="Cell grid colour"),
    Param("cell_border_width", float, 0.5, unit="pt", range=(0, None), role="Cell grid line width"),
    Param("split_vline", float, None, unit="column index (data coords)",
          role="Dashed vertical divider at this x (e.g. 3.5 between human and mouse columns)"),
    Param("split_vline_color", "color", "#333333", unit="hex color", role="Divider colour"),
    Param("split_vline_style", str, "--", role="Divider line style (matplotlib)"),
    Param("split_vline_width", float, 1.8, unit="pt", range=(0, None), role="Divider width"),
    # [Labels and title]
    Param("labels_title", str, "Cross-Condition GO Heatmap", role="Panel title"),
    Param("title_pad", float, CODE_DEFAULT, unit="pt",
          role="Gap between title and matrix (default 24 with column banners, else 6)", tune="raise if banners touch the title"),
    Param("group_banner_fontsize", float, CODE_DEFAULT, unit="pt", role="Column banner font size (default title_size - 1.5)"),
    Param("show_term_labels", bool, True, role="Show the term (row) labels"),
    Param("term_fontsize", float, CODE_DEFAULT, unit="pt", role="Term label font size (default tick_label_size)"),
    Param("term_label_wrap_width", int, 28, unit="characters", range=(1, None), role="Wrap term labels at this width",
          tune="raise for fewer, longer lines"),
    Param("xtick_rotation", float, 45, unit="degrees", role="Condition label rotation"),
    Param("show_legend", bool, True, role="Show the bin legend"),
    Param("legend_loc", str, "upper right", role="Legend anchor (matplotlib loc, figure coords)"),
    # [Layout, figure-relative]
    Param("gs_left", float, 0.03, unit="[0-1] figure fraction", role="Left edge of the plot grid"),
    Param("gs_right", float, 0.98, unit="[0-1] figure fraction", role="Right edge of the plot grid"),
    Param("gs_top", float, 0.88, unit="[0-1] figure fraction", role="Top edge of the plot grid", tune="lower if the title clips"),
    Param("gs_bottom", float, 0.12, unit="[0-1] figure fraction", role="Bottom edge of the plot grid",
          tune="raise if rotated condition labels clip"),
    Param("dendro_width", float, 0.12, unit="fraction of the grid width", range=(0, 1), role="Width of the row dendrogram"),
    Param("dendro_wspace", float, 0.02, unit="fraction of the grid width", role="Gap between dendrogram and matrix"),
    Param("label_margin_pad", float, 1.2, unit="x label width", role="Room reserved for term labels relative to their width",
          tune="raise if term labels clip at the left"),
    Param("label_margin_cap", float, 0.72, unit="[0-1] grid fraction", range=(0, 1),
          role="Upper limit on the room reserved for term labels"),
])


def _pivot_and_link(df, params):
    """Shared by render_cross_condition_heatmap and count_cluster_row_groups
    so a pre-render row-count check and the actual render always agree."""
    term_col = params.get("term_col", "GO Term")
    cond_col = params.get("condition_col", "Condition")
    value_col = params.get("value_col", "Signed -log10(FDR)")

    strip_pattern = params.get("term_strip_pattern")
    df = df.copy()
    if strip_pattern:
        import re
        df[term_col] = df[term_col].astype(str).str.replace(strip_pattern, "", regex=True)

    condition_order = params.get("condition_order") or list(dict.fromkeys(df[cond_col]))
    pivot = df.pivot_table(index=term_col, columns=cond_col, values=value_col, aggfunc="first")
    pivot = pivot.reindex(columns=condition_order)

    lm = None
    order = None
    if params.get("cluster_rows", True) and len(pivot) > 2:
        try:
            from scipy.cluster.hierarchy import linkage, dendrogram
            from scipy.spatial.distance import pdist
            filled = pivot.fillna(0.0)
            lm = linkage(pdist(filled, metric=params.get("metric", "euclidean")),
                        method=params.get("linkage", "average"))
            order = dendrogram(lm, no_plot=True)["leaves"]
            pivot = pivot.iloc[order]
        except ImportError:
            lm = None
    return pivot, lm, order


def _cluster_bands(pivot, lm, order, params):
    """Cut the already-computed row dendrogram into contiguous groups and
    return [(insert_row_idx_in_pivot, header_label, member_count), ...] in
    row order. insert_row_idx is the position (in the already-leaf-ordered
    pivot) each group's header row should be inserted BEFORE. A horizontal
    cut of a dendrogram always yields leaf groups that are contiguous in
    that same tree's leaf order, so no extra reordering is needed here.
    """
    if lm is None or len(pivot) == 0:
        return []
    from scipy.cluster.hierarchy import fcluster

    dist_threshold = params.get("cluster_dist_threshold")
    if dist_threshold is None:
        # Fraction of max linkage distance -- scipy dendrogram's own default
        # color_threshold convention (0.7) is tuned for dendrogram *coloring*
        # legibility, not for producing balanced cluster sizes; datasets with
        # one dominant correlated block (verified: this repo's RNA KEGG panel
        # puts 108/112 terms in one cluster at any reasonable fraction) may
        # need a much lower fraction, or may not usefully split at all --
        # that's a real property of the data, not something to force-split.
        frac = float(params.get("cluster_dist_threshold_frac", 0.7))
        dist_threshold = frac * float(lm[:, 2].max())
    raw_labels = fcluster(lm, t=float(dist_threshold), criterion="distance")
    labels_ordered = raw_labels[order]

    abs_strength = pivot.abs().max(axis=1).fillna(0.0).to_numpy()
    bands = []
    n = len(labels_ordered)
    start = 0
    while start < n:
        lab = labels_ordered[start]
        end = start
        while end + 1 < n and labels_ordered[end + 1] == lab:
            end += 1
        block = list(range(start, end + 1))
        rep_local = max(block, key=lambda i: abs_strength[i])
        rep_term = str(pivot.index[rep_local])
        size = len(block)
        header_label = f"■ {rep_term} ({size} term{'s' if size > 1 else ''})"
        bands.append((start, header_label, size))
        start = end + 1
    return bands


def count_cluster_row_groups(df, params) -> int:
    """Number of Jaccard/value-profile cluster groups a render_cross_condition_
    heatmap(..., show_cluster_bands=True) call would produce for this df/params
    -- for sizing the panel's height BEFORE rendering (the header rows it adds
    need room reserved for them)."""
    pivot, lm, order = _pivot_and_link(df, params)
    return len(_cluster_bands(pivot, lm, order, params))


@uses_schema(SCHEMA)
def render_cross_condition_heatmap(fig, df, params):
    """Draw a discrete cross-condition enrichment heatmap onto ``fig``.

    params: term_col('GO Term'), condition_col('Condition'),
            value_col('Signed -log10(FDR)'), condition_order(list; default
            = first-seen order), condition_rename_map (dict, raw Condition
            value -> display label for the x-tick text only; pivoting
            still uses the raw values), cluster_rows(bool, default True),
            linkage, metric, dendro_width, bin_edges([2.0, 3.0] -- the
            |signed value| cutoffs between the FDR<0.05/<0.01/<0.001 tiers;
            -log10(0.05)=1.301 is the implicit floor since every present
            cell already clears that), colors (dict with keys
            up3/up2/up1/absent/down1/down2/down3, deepest-to-lightest each
            side), show_dendro_labels, show_term_labels, term_fontsize,
            term_label_wrap_width (chars before wrapping, default 28),
            label_margin_pad (extra fraction beyond the measured minimum
            reserved for term labels, default 1.2 -- raise to shrink the
            heatmap plot area further), xtick_rotation, show_legend,
            legend_loc, labels_title, axes_label_size, tick_label_size,
            title_size,
            show_cluster_bands (bool, default False -- cut the row
            dendrogram already computed for cluster_rows into groups via
            fcluster and insert a bold/colored blank header row + shaded
            band + separator line above each group's member rows, in place
            of drawing the side dendrogram tree; use
            count_cluster_row_groups(df, params) beforehand to size the
            panel for the extra header rows this adds),
            cluster_dist_threshold (float; distance cutoff for the fcluster
            group cut, default 0.7 * max linkage distance -- scipy
            dendrogram's own default color_threshold convention),
            cluster_band_color (default '#4F46E5')
    """
    title_sz = params.get("title_size", 13)
    t_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    condition_order = params.get("condition_order") or list(dict.fromkeys(df[params.get("condition_col", "Condition")]))
    pivot, lm, order = _pivot_and_link(df, params)

    # Optional title-layer: cut the already-computed row dendrogram into
    # groups (same clustering that already orders the rows -- this doesn't
    # introduce a new clustering axis, just labels the one already driving
    # row order) and insert a blank/bold header row above each group, with a
    # shaded band + separator line marking the boundary. All-NaN header rows
    # render as an ordinary "absent" (white) row in the heatmap grid; the
    # band/label are what distinguish them from a real all-white term row.
    header_rows: dict[str, int] = {}  # header label -> row index in final pivot
    if params.get("show_cluster_bands", False) and lm is not None:
        bands = _cluster_bands(pivot, lm, order, params)
        if bands:
            new_index = []
            new_rows = []
            cursor = 0
            for insert_at, header_label, _size in bands:
                new_index.extend(pivot.index[cursor:insert_at])
                new_rows.extend(pivot.iloc[cursor:insert_at].to_numpy().tolist())
                header_rows[header_label] = len(new_index)
                new_index.append(header_label)
                new_rows.append([np.nan] * pivot.shape[1])
                cursor = insert_at
            new_index.extend(pivot.index[cursor:])
            new_rows.extend(pivot.iloc[cursor:].to_numpy().tolist())
            pivot = pd.DataFrame(new_rows, index=new_index, columns=pivot.columns)

    # Cluster-band mode inserts header rows that the dendrogram's leaf
    # coordinates (still sized to the ORIGINAL, un-inflated row count) can no
    # longer be aligned against -- the header labels + separator bands
    # already show the same grouping the tree would, more explicitly (with
    # a representative term name), so the side tree is dropped rather than
    # risk drawing a misaligned one.
    show_dendro = lm is not None and not header_rows
    dendro_w = float(params.get("dendro_width", 0.12)) if show_dendro else 0.0
    if show_dendro:
        gs = fig.add_gridspec(
            1, 2, width_ratios=[dendro_w, 1 - dendro_w], wspace=float(params.get("dendro_wspace", 0.02)),
            top=float(params.get("gs_top", 0.88)),
            bottom=float(params.get("gs_bottom", 0.12)),
            left=float(params.get("gs_left", 0.03)),
            right=float(params.get("gs_right", 0.98))
        )
        ax_dendro = fig.add_subplot(gs[0, 0])
        ax = fig.add_subplot(gs[0, 1])
        from scipy.cluster.hierarchy import dendrogram as draw_dendro
        draw_dendro(lm, ax=ax_dendro, orientation="left", no_labels=True,
                   link_color_func=lambda i: "black")
        ax_dendro.axis("off")
        ax_dendro.set_ylim(10 * len(pivot), 0)
    else:
        ax = fig.add_subplot(111)

    e1, e2 = params.get("bin_edges", [2.0, 3.0])
    colors = params.get("colors", {})
    default_colors = {
        "up3": "#e6550d", "up2": "#fd8d3c", "up1": "#fdd0a2",
        "absent": "#ffffff",
        "down1": "#c6dbef", "down2": "#6baed6", "down3": "#08519c",
    }
    color_seq = [colors.get(k, default_colors[k]) for k in
                 ("down3", "down2", "down1", "absent", "up1", "up2", "up3")]

    def _bin(v):
        if pd.isna(v):
            return 3  # absent
        av = abs(v)
        tier = 2 if av >= e2 else 1 if av >= e1 else 0  # 0=<0.05, 1=<0.01, 2=<0.001
        return (3 - (tier + 1)) if v < 0 else (3 + (tier + 1))

    codes = pivot.apply(lambda col: col.map(_bin)).to_numpy()

    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap = ListedColormap(color_seq)
    norm = BoundaryNorm(np.arange(-0.5, 7.5, 1.0), cmap.N)
    ax.imshow(codes, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")

    if params.get("show_cell_borders", True):
        # Minor-tick grid at cell boundaries -- imshow itself has no concept
        # of per-cell borders, so this is the standard way to draw a
        # separator between adjacent cells without affecting the major
        # ticks/labels below.
        n_rows, n_cols = codes.shape
        ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
        ax.grid(which="minor", color=params.get("cell_border_color", "lightgrey"),
               linewidth=float(params.get("cell_border_width", 0.5)))
        ax.tick_params(which="minor", length=0)

    # Publication-facing renaming of the raw Condition values (e.g.
    # "D1_vs_Control" -> "Acute D1") happens only at display time, via
    # config -- condition_order/pivoting above still uses the raw values,
    # same principle as sample_rename_map elsewhere in this codebase.
    condition_rename_map = params.get("condition_rename_map", {})
    condition_labels = [condition_rename_map.get(c, c) for c in condition_order]
    ax.set_xticks(range(len(condition_order)))
    ax.set_xticklabels(condition_labels, fontsize=t_sz,
                       rotation=float(params.get("xtick_rotation", 45)), ha="right")

    if params.get("show_term_labels", True):
        import textwrap
        fs = params.get("term_fontsize", t_sz)
        wrap_w = int(params.get("term_label_wrap_width", 28))
        labels = [textwrap.fill(str(t), width=wrap_w, break_long_words=False)
                  for t in pivot.index.tolist()]
        ax.set_yticks(range(len(pivot)))
        ax.set_yticklabels(labels, fontsize=fs)
        if show_dendro:
            ax.yaxis.tick_right()

        # Shrink the actual heatmap plot area to leave explicit room for the
        # (larger, possibly wrapped) term labels, sized from the
        # actually-rendered label extent -- same measured-extent pattern as
        # cross_condition_dotplot.py/go_cluster_dot.py/go_bar.py/go_dot.py/
        # volcano.py this session. A label_margin_pad > 1 adds deliberate
        # extra breathing room beyond the bare minimum so the plot reads as
        # visibly narrower, not just non-clipping.
        root_fig = getattr(ax.figure, "figure", ax.figure)
        renderer = root_fig.canvas.get_renderer()
        label_px = max((t.get_window_extent(renderer=renderer).width
                         for t in ax.get_yticklabels()), default=0)
        pos = ax.get_position()
        panel_px = pos.width * ax.figure.bbox.width
        pad = float(params.get("label_margin_pad", 1.2))
        needed_frac = (label_px + 0.12 * root_fig.dpi) / panel_px * pad if panel_px > 0 else 0.3
        label_margin = min(float(params.get("label_margin_cap", 0.72)), max(0.15, needed_frac))
        if show_dendro:
            ax.set_position([pos.x0, pos.y0, pos.width * (1 - label_margin), pos.height])
        else:
            new_x0 = pos.x0 + pos.width * label_margin
            ax.set_position([new_x0, pos.y0, pos.width * (1 - label_margin), pos.height])
    else:
        ax.set_yticks([])

    if header_rows:
        band_color = params.get("cluster_band_color", "#4F46E5")
        yticklabels = ax.get_yticklabels() if params.get("show_term_labels", True) else []
        for _label_text, idx in header_rows.items():
            ax.axhspan(idx - 0.5, idx + 0.5, color=band_color, alpha=0.10, zorder=1)
            ax.axhline(idx - 0.5, color=band_color, lw=1.2, alpha=0.85, zorder=6)
            if idx < len(yticklabels):
                yticklabels[idx].set_fontweight("bold")
                yticklabels[idx].set_color(band_color)

    split_vline = params.get("split_vline")
    if split_vline is not None:
        ax.axvline(float(split_vline), color=params.get("split_vline_color", "#333333"),
                   linestyle=params.get("split_vline_style", "--"),
                   linewidth=float(params.get("split_vline_width", 1.8)), zorder=10)

    column_groups = params.get("column_groups")
    if column_groups:
        for grp in column_groups:
            start_col = grp["start"]
            end_col = grp["end"]
            mid_col = (start_col + end_col) / 2.0
            label = grp.get("label", "")
            grp_color = grp.get("color", "#333333")
            y_banner = float(grp.get("y_banner", 1.04))
            ax.text(mid_col, y_banner, label, transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=params.get("group_banner_fontsize", title_sz - 1.5),
                    fontweight="bold", color=grp_color)
            line_y = float(grp.get("line_y", 1.02))
            ax.plot([start_col - 0.4, end_col + 0.4], [line_y, line_y],
                    transform=ax.get_xaxis_transform(), color=grp_color,
                    linewidth=float(grp.get("line_width", 2.2)), clip_on=False)

    title = text_param(params, "labels_title", "Cross-Condition GO Heatmap")
    title_ax = ax_dendro if show_dendro else ax
    title_pad = float(params.get("title_pad", 24 if column_groups else 6))
    title_ax.set_title(title, fontsize=title_sz, fontweight="bold",
                       loc="left" if show_dendro else "center", pad=title_pad)

    if params.get("show_legend", True):
        from matplotlib.patches import Patch
        legend_labels = ["UP FDR<0.001", "UP FDR<0.01", "UP FDR<0.05", "absent",
                          "DOWN FDR<0.05", "DOWN FDR<0.01", "DOWN FDR<0.001"]
        handles = [Patch(facecolor=c, edgecolor="#888888", label=l)
                   for c, l in zip(reversed(color_seq), legend_labels)]
        fig.legend(handles=handles, loc=params.get("legend_loc", "upper right"),
                  bbox_to_anchor=(0.99, 0.99),
                  bbox_transform=fig.transSubfigure if hasattr(fig, "transSubfigure")
                  else fig.transFigure,
                  fontsize=t_sz, frameon=False, handlelength=1.2, labelspacing=0.3)

    return pivot
