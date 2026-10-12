"""Expression heatmap renderer (optionally with a clustering dendrogram).

Draws onto a Matplotlib Figure or SubFigure because it may create its own
gridspec (heatmap + dendrogram). All visual attributes come from ``params``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("heatmap", params=[
    # [Rows and values]
    Param("label_col", str, None, role="Column with the row labels (default: symbol, else gene_id, else the row number)"),
    Param("sample_columns", list, None, role="Columns to show as samples (default: every numeric column that is not "
          "a statistic such as padj or log2FC)"),
    Param("n_genes", int, 50, unit="genes", range=(1, None), role="Genes shown (after sorting)"),
    Param("max_gene_labels", int, 20, unit="genes", range=(0, None),
          role="Genes are named only up to this many rows (more: no names, rather than row numbers)",
          tune="raise with a taller panel and a smaller tick_label_size"),
    Param("sorting", ("padj", "log2fc", "clustering"), "padj", role="How the genes are chosen and ordered"),
    Param("normalization", ("z-score", "minmax", "log2", "none"), "z-score", role="Per-gene scaling of the values"),
    Param("transpose", bool, False, role="Samples as rows, genes as columns"),
    Param("sample_rename_map", dict, {}, open_keys=True, role="Display label per raw sample name"),
    Param("show_dendrogram", bool, False, role="Draw the clustering dendrogram"),
    # [Colours]
    Param("colormap", "cmap", "RdBu_r", role="Colormap of the heatmap"),
    Param("colorbar_min", float, None, unit="value units", role="Lower end of the colour scale (default: data)"),
    Param("colorbar_max", float, None, unit="value units", role="Upper end of the colour scale (default: data)"),
    Param("show_colorbar", bool, True, role="Show the colourbar"),
    # [Labels]
    Param("labels_title", str, None, role="Panel title"),
    Param("labels_xlabel", str, None, role="x-axis title"),
    Param("labels_ylabel", str, None, role="y-axis title"),
    Param("show_xticklabels", bool, True, role="Show column labels"),
    Param("show_yticklabels", bool, True, role="Show row labels"),
    Param("xtick_label_rotation", float, 90, unit="degrees", role="Column label rotation"),
    Param("xtick_label_alignment", str, CODE_DEFAULT, role="Column label alignment (default: center at 0/90 degrees, else right)"),
    Param("title_size", float, 10, unit="pt", role="Panel title font size"),
    Param("axes_label_size", float, 8, unit="pt", role="Axis title font size"),
    Param("tick_label_size", float, 6, unit="pt", role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_heatmap(fig, df, params):
    exclude_patterns = [
        'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
        'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue',
        'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name',
    ]
    df = df.copy()

    n_genes = int(params.get('n_genes', 50))
    normalization = params.get('normalization', 'z-score')
    transpose = bool(params.get('transpose', False))
    sorting = params.get('sorting', 'padj')
    colormap = params.get('colormap', 'RdBu_r')
    cbar_min = params.get('colorbar_min')
    cbar_max = params.get('colorbar_max')
    show_dendrogram = bool(params.get('show_dendrogram', False))

    chosen = params.get('sample_columns')
    sample_cols = ([c for c in chosen if c in df.columns] if chosen else
                   [c for c in df.columns
                    if not any(p in c.lower() for p in exclude_patterns)
                    and pd.api.types.is_numeric_dtype(df[c])])
    if not sample_cols:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No sample expression columns found.',
                ha='center', va='center', fontsize=12, transform=ax.transAxes)
        return None

    expr_data = df[sample_cols].copy().dropna()
    rename_map = params.get('sample_rename_map', {})
    if rename_map:
        expr_data = expr_data.rename(columns=rename_map)

    if len(expr_data) == 0:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No valid data after removing NaN values',
                ha='center', va='center', fontsize=12, transform=ax.transAxes)
        return None

    if 'padj' in df.columns and df.loc[expr_data.index, 'padj'].dropna().shape[0] > 0:
        valid_padj = df.loc[expr_data.index, 'padj'].dropna()
        top_idx = valid_padj.nsmallest(min(n_genes, len(valid_padj))).index
    else:
        variances = expr_data.var(axis=1)
        top_idx = variances.nlargest(min(n_genes, len(expr_data))).index

    label_col = params.get('label_col')
    if label_col and label_col in df.columns:
        gene_labels = df.loc[top_idx, label_col].tolist()
    elif 'symbol' in df.columns:
        gene_labels = df.loc[top_idx, 'symbol'].tolist()
    elif 'gene_id' in df.columns:
        gene_labels = df.loc[top_idx, 'gene_id'].tolist()
    else:
        gene_labels = top_idx.tolist()
    expr_data = expr_data.loc[top_idx]

    if normalization == 'z-score':
        heatmap_data = expr_data.apply(lambda x: (x - x.mean()) / (x.std() + 1e-10), axis=1)
        cbar_label = 'Z-score'
    elif normalization == 'minmax':
        heatmap_data = expr_data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-10), axis=1)
        cbar_label = 'Normalized (0-1)'
    elif normalization == 'log2':
        heatmap_data = np.log2(expr_data + 1)
        cbar_label = 'Log2(count + 1)'
    else:
        heatmap_data = expr_data
        cbar_label = 'Raw count'

    lm = None
    if sorting == 'padj' and 'padj' in df.columns:
        sort_order = df.loc[heatmap_data.index, 'padj'].argsort()
        heatmap_data = heatmap_data.iloc[sort_order]
        gene_labels = [gene_labels[i] for i in sort_order]
    elif sorting == 'log2fc' and 'log2FC' in df.columns:
        sort_order = df.loc[heatmap_data.index, 'log2FC'].abs().argsort()[::-1]
        heatmap_data = heatmap_data.iloc[sort_order]
        gene_labels = [gene_labels[i] for i in sort_order]
    elif sorting == 'clustering':
        try:
            from scipy.cluster.hierarchy import linkage, dendrogram
            from scipy.cluster.hierarchy import dendrogram as get_order_dendro
            from scipy.spatial.distance import pdist
            lm = linkage(pdist(heatmap_data, metric='euclidean'), method='average')
            order = get_order_dendro(lm, no_plot=True)['leaves']
            heatmap_data = heatmap_data.iloc[order]
            gene_labels = [gene_labels[i] for i in order]
        except ImportError:
            pass

    # Determine axes layout based on show_dendrogram and linkage
    if show_dendrogram and lm is not None:
        if transpose:
            gs = fig.add_gridspec(2, 1, height_ratios=[1, 4], hspace=0.02)
            ax_dendro = fig.add_subplot(gs[0, 0])
            ax = fig.add_subplot(gs[1, 0])
        else:
            gs = fig.add_gridspec(1, 2, width_ratios=[1, 6], wspace=0.01)
            ax_dendro = fig.add_subplot(gs[0, 0])
            ax = fig.add_subplot(gs[0, 1])
    else:
        ax = fig.add_subplot(111)
        ax_dendro = None

    if transpose:
        heatmap_data = heatmap_data.T

    im = ax.imshow(heatmap_data, cmap=colormap, aspect='auto',
                   interpolation='nearest', vmin=cbar_min, vmax=cbar_max)

    t_sz = params.get('tick_label_size', 6)
    a_sz = params.get('axes_label_size', 8)
    title_sz = params.get('title_size', 10)

    rot = params.get('xtick_label_rotation', 90)
    align = params.get('xtick_label_alignment', 'center' if rot in (0, 90) else 'right')

    # Draw dendrogram if enabled
    if ax_dendro is not None:
        try:
            from scipy.cluster.hierarchy import dendrogram as draw_tree_dendro
            if transpose:
                draw_tree_dendro(lm, ax=ax_dendro, orientation='top', no_labels=True, link_color_func=lambda x: 'black')
                ax_dendro.axis('off')
                ax_dendro.set_xlim(0, 10 * len(heatmap_data.columns))
            else:
                draw_tree_dendro(lm, ax=ax_dendro, orientation='left', no_labels=True, link_color_func=lambda x: 'black')
                ax_dendro.axis('off')
                ax_dendro.set_ylim(10 * len(heatmap_data.index), 0)
        except Exception as e:
            print(f"Dendrogram rendering failed: {e}")

    if transpose:
        if len(heatmap_data.index) <= 50:
            ax.set_yticks(range(len(heatmap_data.index)))
            ax.set_yticklabels(heatmap_data.index, fontsize=t_sz)
        if len(gene_labels) <= int(params.get('max_gene_labels', 20)):
            ax.set_xticks(range(len(gene_labels)))
            ax.set_xticklabels(gene_labels, rotation=rot, fontsize=t_sz, ha=align)
        else:
            ax.set_xticks([])
    else:
        if len(heatmap_data.columns) <= 50:
            ax.set_xticks(range(len(heatmap_data.columns)))
            ax.set_xticklabels(heatmap_data.columns, rotation=rot, fontsize=t_sz, ha=align)
        if len(gene_labels) <= int(params.get('max_gene_labels', 20)):
            ax.set_yticks(range(len(gene_labels)))
            ax.set_yticklabels(gene_labels, fontsize=t_sz)
        else:
            ax.set_yticks([])
        # If dendrogram is on the left, move heatmap ticks/labels to the right
        if ax_dendro is not None:
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")

    title = params.get('labels_title')
    if title:
        ax.set_title(title, fontsize=title_sz, fontweight='bold')
    if params.get('labels_xlabel'):
        ax.set_xlabel(params['labels_xlabel'], fontsize=a_sz)
    if params.get('labels_ylabel'):
        # Move ylabel to the left of the dendrogram if ticks are on the right
        if ax_dendro is not None and not transpose:
            ax.set_ylabel(params['labels_ylabel'], fontsize=a_sz)
            ax.yaxis.set_label_coords(-0.22, 0.5)
        else:
            ax.set_ylabel(params['labels_ylabel'], fontsize=a_sz)
    if not params.get('show_xticklabels', True):
        ax.tick_params(axis='x', labelbottom=False)
    if not params.get('show_yticklabels', True):
        ax.tick_params(axis='y', labelleft=False, labelright=False)

    if params.get('show_colorbar', True):
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.08 if (ax_dendro is not None and not transpose) else 0.04)
        cbar.set_label(cbar_label, fontsize=a_sz)
        cbar.ax.tick_params(labelsize=t_sz)

    return heatmap_data, gene_labels
