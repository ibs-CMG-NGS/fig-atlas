"""PCA scatter renderer.

Computes a PCA via SVD and draws the requested component scatter onto a
Matplotlib Figure or SubFigure. All visual attributes come from ``params``.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import matplotlib
import numpy as np
import pandas as pd

from ..params import text_param


from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("pca", params=[
    Param("n_genes", int, 500, unit="genes", range=(2, None), role="Most variable genes used for the PCA"),
    Param("transform", ("log2", "log1p", "none"), "log2", role="Transform of the counts before the PCA"),
    Param("scaling", ("standard", "none"), "standard", role="'standard': centre and scale each gene; otherwise centre only"),
    Param("x_pc", int, 1, unit="component number", range=(1, None), role="Component on the x axis"),
    Param("y_pc", int, 2, unit="component number", range=(1, None), role="Component on the y axis"),
    Param("sample_columns", list, None, role="Columns to use as samples (default: every numeric column that is not "
          "a statistic such as padj or log2FC)"),
    Param("sample_groups", dict, None, open_keys=True,
          role="Group name -> its sample columns; points are coloured by group, with a legend"),
    Param("group_colors", dict, {}, open_keys=True, unit="hex color",
          role="Colour per group (default: matplotlib tab10 by group)"),
    Param("legend_loc", str, "best", role="Group legend location (matplotlib loc)"),
    Param("sample_rename_map", dict, {}, open_keys=True, role="Display label per raw sample name"),
    Param("point_size", float, 80, unit="pt^2 (marker area)", range=(0, None), role="Sample point size"),
    Param("show_labels", bool, True, role="Label each sample point"),
    Param("title", str, "PCA — Sample Expression", role="Panel title"),
    Param("title_size", float, 10, unit="pt", role="Panel title font size"),
    Param("axes_label_size", float, 8, unit="pt", role="Axis title font size"),
    Param("tick_label_size", float, 7, unit="pt", role="Tick and point label font size"),
])


@uses_schema(SCHEMA)
def render_pca(fig, df, params):
    exclude = {
        'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
        'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue', 'adj_p',
        'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name',
        'pvalue', 'p_value',
    }
    ax = fig.add_subplot(111)
    df = df.copy() if df is not None else pd.DataFrame()

    chosen = params.get('sample_columns') or [c for cols in (params.get('sample_groups') or {}).values() for c in cols]
    sample_cols = ([c for c in chosen if c in df.columns] if chosen else
                   [c for c in df.columns
                    if not any(p in c.lower() for p in exclude)
                    and pd.api.types.is_numeric_dtype(df[c])])
    if not sample_cols:
        ax.text(0.5, 0.5, 'No sample expression columns found.',
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
        return None

    expr = df[sample_cols].fillna(0)
    n = min(int(params.get('n_genes', 500)), len(expr))
    expr = expr.loc[expr.var(axis=1).nlargest(n).index]
    mat = expr.values.astype(float)
    transform = params.get('transform', 'log2')
    if transform == 'log2':
        mat = np.log2(mat + 1.0)
    elif transform == 'log1p':
        mat = np.log1p(mat)

    X = mat.T
    if params.get('scaling', 'standard') == 'standard':
        mean = X.mean(axis=0)
        std = X.std(axis=0, ddof=0)
        std[std == 0] = 1.0
        X = (X - mean) / std

    Xc = X - X.mean(axis=0)
    U, s, Vt = np.linalg.svd(Xc, full_matrices=False)
    ev = (s ** 2) / (Xc.shape[0] - 1)
    explained = (ev / ev.sum()).tolist()
    n_comp = min(len(sample_cols), Xc.shape[1], 10)
    scores = U[:, :n_comp] * s[:n_comp]
    rename_map = params.get('sample_rename_map', {})
    display_names = [rename_map.get(c, c) for c in sample_cols]

    scores_df = pd.DataFrame(scores, index=display_names,
                             columns=[f"PC{i+1}" for i in range(scores.shape[1])])
    explained = explained[:n_comp]

    xi = int(params.get('x_pc', 1)) - 1
    yi = int(params.get('y_pc', 2)) - 1
    if xi >= scores.shape[1] or yi >= scores.shape[1]:
        ax.text(0.5, 0.5, f"Only {scores.shape[1]} PCs available.",
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
        return scores_df, explained

    xs, ys = scores[:, xi], scores[:, yi]
    cmap = matplotlib.colormaps.get_cmap('tab10')
    sample_groups = params.get('sample_groups') or {}
    group_of = {c: g for g, cols in sample_groups.items() for c in cols}
    if sample_groups:
        names = list(sample_groups)
        gcol = {g: params.get('group_colors', {}).get(g) or cmap(i % 10) for i, g in enumerate(names)}
        colors = [gcol.get(group_of.get(c), cmap(0)) for c in sample_cols]
    else:
        colors = [cmap(i % 10) for i in range(len(display_names))]

    ax.scatter(xs, ys, s=int(params.get('point_size', 80)), c=colors, alpha=0.85,
               edgecolors='white', linewidths=0.8, zorder=3)
    if sample_groups:
        from matplotlib.lines import Line2D
        handles = [Line2D([], [], linestyle='none', marker='o', color=gcol[g], label=str(g)) for g in sample_groups]
        ax.legend(handles=handles, loc=params.get('legend_loc', 'best'), frameon=False,
                  fontsize=params.get('tick_label_size', 7))
    if params.get('show_labels', True):
        for x, y, lbl in zip(xs, ys, display_names):
            ax.annotate(lbl, (x, y), xytext=(4, 4), textcoords='offset points',
                        fontsize=6, color='#222',
                        bbox=dict(boxstyle='round,pad=0.15', fc='white', alpha=0.6, ec='none'))

    pct_x = explained[xi] * 100 if xi < len(explained) else 0
    pct_y = explained[yi] * 100 if yi < len(explained) else 0

    t_sz = params.get('tick_label_size', 7)
    a_sz = params.get('axes_label_size', 8)
    title_sz = params.get('title_size', 10)

    ax.set_xlabel(f"PC{xi+1}  ({pct_x:.1f}% variance)", fontsize=a_sz)
    ax.set_ylabel(f"PC{yi+1}  ({pct_y:.1f}% variance)", fontsize=a_sz)
    ax.set_title(text_param(params, 'title', 'PCA — Sample Expression'), fontsize=title_sz, fontweight='bold')
    ax.axhline(0, color='#bbb', linewidth=0.8, linestyle='--', zorder=1)
    ax.axvline(0, color='#bbb', linewidth=0.8, linestyle='--', zorder=1)
    ax.grid(True, alpha=0.3, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=t_sz)

    scree = "Explained variance:\n" + "  ".join(
        f"PC{i+1}: {v*100:.1f}%" for i, v in enumerate(explained[:3]))
    ax.text(0.99, 0.01, scree, transform=ax.transAxes, fontsize=t_sz - 1,
            ha='right', va='bottom', color='#666',
            bbox=dict(boxstyle='round', fc='white', alpha=0.7, ec='#ccc'))
    return scores_df, explained
