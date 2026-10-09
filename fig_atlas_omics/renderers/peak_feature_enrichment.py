"""Peak/gene-feature enrichment-vs-background renderers.

Both renderers here share one input table shape (one row per (geneset,
feature) pair, e.g. from a Fisher's-exact-test feature-enrichment script):
GeneSet, Feature, DA_Count, DA_Pct, Background_Count, Background_Pct,
OddsRatio, p_value, p_adjust. render_peak_feature_enrichment draws the
statistical comparison (log2 odds ratio, colored by significance);
render_peak_feature_composition draws the plain compositional context
(DA% vs background% per feature) the odds ratio was computed from -- two
different questions from the same already-computed table, so no separate
data source or recomputation is needed for either.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fig_atlas.params import text_param


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("peak_feature_enrichment", params=[
    # [Data]
    Param("geneset_col", str, "GeneSet", role="Column with the gene set (one facet or bar group each)"),
    Param("geneset_order", list, None, role="Gene set order (default: order in the data)"),
    Param("geneset_rename_map", dict, {}, open_keys=True, role="Display title per gene set"),
    Param("feature_col", str, "Feature", role="Column with the peak feature category"),
    Param("feature_order", list, None, role="Feature order (default: order in the data); first is bottom in the composition bars"),
    Param("odds_ratio_col", str, "OddsRatio", role="Enrichment: odds ratio column"),
    Param("fdr_col", str, "p_adjust", role="Enrichment: adjusted P column"),
    Param("da_pct_col", str, "DA_Pct", role="Composition: percentage of DA peaks per feature"),
    Param("background_pct_col", str, "Background_Pct", role="Composition: percentage of background peaks per feature"),
    # [Enrichment bars]
    Param("fdr_max", float, 0.05, unit="FDR", range=(0, 1), role="Bars at or below this FDR use sig_color"),
    Param("sig_color", "color", "#e57373", unit="hex color", role="Colour of significant bars"),
    Param("ns_color", "color", "#9e9e9e", unit="hex color", role="Colour of non-significant bars"),
    Param("bar_height", float, 0.68, unit="fraction of the row", range=(0, 1), role="Bar thickness"),
    Param("bar_edgecolor", "color", "black", unit="color", role="Enrichment bar outline colour"),
    Param("bar_edgewidth", float, 0.5, unit="pt", range=(0, None), role="Enrichment bar outline width"),
    Param("shared_xlim", bool, True, role="One zero-centred x range for every facet, so bar lengths compare across facets"),
    Param("xlim_pad", float, 1.15, unit="multiple of the largest |log2 OR|", range=(1, None), role="Margin of the shared x range"),
    Param("xlim", list, None, unit="data coords [min, max]", role="Explicit x range; overrides shared_xlim (use it to align separate calls)"),
    Param("wspace", float, 0.08, unit="fraction of the mean facet width", range=(0, None), role="Gap between facets"),
    Param("xlabel_text", str, "log2(Odds Ratio) vs background", role="x-axis title of the enrichment facets"),
    # [Composition bars]
    Param("feature_colors", dict, None, open_keys=True, unit="hex color", role="Colour per feature (default: built-in palette)"),
    Param("bar_width", float, 0.7, unit="x units (one bar = 1)", range=(0, None), role="Composition bar width"),
    Param("group_gap", float, 1.0, unit="x units", range=(0, None), role="Extra gap between gene set groups"),
    Param("edge_color", "color", "white", unit="color", role="Outline between stacked segments"),
    Param("edge_width", float, 0.5, unit="pt", range=(0, None), role="Segment outline width"),
    Param("ylabel_text", str, "% of peaks", role="y-axis title of the composition chart"),
    # [Legend and labels]
    Param("show_legend", bool, True, role="Show the legend"),
    Param("legend_loc", str, CODE_DEFAULT, role="Legend location (default 'best' for enrichment, 'center left' for composition)"),
    Param("labels_title", str, CODE_DEFAULT, role="Figure title (each chart has its own default)"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Title font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


def _facet_axes(fig, genesets, wspace, title_sz):
    """Create one subplot per geneset, left-to-right, sharing the y-axis."""
    n = len(genesets)
    gs = fig.add_gridspec(1, n, wspace=wspace)
    axes = []
    for i in range(n):
        ax = fig.add_subplot(gs[0, i], sharey=axes[0] if axes else None)
        if i > 0:
            ax.tick_params(labelleft=False)
        axes.append(ax)
    return axes


@uses_schema(SCHEMA)
def render_peak_feature_enrichment(fig, df, params):
    """Draw a faceted diverging log2(Odds Ratio) bar chart onto ``fig``.

    One facet (subplot) per GeneSet value (e.g. total/up/down), each with
    one horizontal bar per Feature category, colored by whether it passed
    the FDR cutoff.

    params: geneset_col('GeneSet'), geneset_order(list; default = first
            -seen), geneset_rename_map (dict, raw value -> facet title),
            feature_col('Feature'), feature_order(list; default =
            first-seen), odds_ratio_col('OddsRatio'), fdr_col('p_adjust'),
            fdr_max(0.05), sig_color, ns_color, bar_edgecolor,
            bar_edgewidth, bar_height (fraction of the per-feature row a
            bar's thickness fills, default 0.68 -- 85% of matplotlib's own
            0.8 barh default), shared_xlim (bool, default True -- one common,
            0-centered x-range across every facet, sized to the largest
            |log2 Odds Ratio| anywhere in the table, so a bar's length
            means the same effect size in every facet; False reverts to
            each facet auto-scaling to its own data, which makes bars look
            comparable across facets even when their underlying odds
            ratios aren't), xlim_pad (multiplier on that shared range for
            a bit of margin, default 1.15), xlim ((min, max) tuple --
            explicit override that always wins over shared_xlim/xlim_pad;
            needed when several SEPARATE calls to this function (e.g. one
            per row in a multi-panel figure, not multiple facets within
            one call) must all share the same x-range: compute the global
            max in the caller and pass it here to every call, since this
            function's own auto-shared-range logic only sees the facets
            inside its own single call), xlabel_text, labels_title,
            show_legend, legend_loc, wspace, axes_label_size,
            tick_label_size, title_size
    """
    a_sz = params.get("axes_label_size", 11)
    title_sz = params.get("title_size", 13)
    tick_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    geneset_col = params.get("geneset_col", "GeneSet")
    feature_col = params.get("feature_col", "Feature")
    or_col = params.get("odds_ratio_col", "OddsRatio")
    fdr_col = params.get("fdr_col", "p_adjust")
    required = {geneset_col, feature_col, or_col, fdr_col}
    if df.empty or not required.issubset(df.columns):
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    genesets = params.get("geneset_order") or list(dict.fromkeys(df[geneset_col]))
    features = params.get("feature_order") or list(dict.fromkeys(df[feature_col]))
    rename = params.get("geneset_rename_map", {})
    fdr_max = float(params.get("fdr_max", 0.05))
    sig_color = params.get("sig_color", "#e57373")
    ns_color = params.get("ns_color", "#9e9e9e")
    wspace = float(params.get("wspace", 0.08))
    shared_xlim = params.get("shared_xlim", True)
    xlim_pad = float(params.get("xlim_pad", 1.15))
    xlim_override = params.get("xlim")

    axes = _facet_axes(fig, genesets, wspace, title_sz)
    y_pos = list(range(len(features)))[::-1]

    # First pass: compute each facet's log2(OR) + significance color without
    # drawing yet, so the shared x-range (if any) can be sized from every
    # facet's data before any bars are placed.
    per_geneset = {}
    max_abs_log_or = 0.0
    for gs_val in genesets:
        sub = df[df[geneset_col] == gs_val].set_index(feature_col)
        odds = pd.to_numeric(sub.reindex(features)[or_col], errors="coerce")
        fdr = pd.to_numeric(sub.reindex(features)[fdr_col], errors="coerce")
        # OddsRatio == 0 (zero DA hits in that feature) or Inf (zero
        # background hits, or a degenerate 1-peak geneset like a
        # single-DA-peak "down" set) has no finite log -- leave that bar
        # undrawn rather than clipping to an arbitrary floor or letting Inf
        # poison the shared x-range for every other facet/panel.
        log_or = odds.where((odds > 0) & np.isfinite(odds)).apply(np.log2)
        colors = [sig_color if (pd.notna(f) and f <= fdr_max) else ns_color for f in fdr]
        per_geneset[gs_val] = (log_or, colors)
        if log_or.notna().any():
            max_abs_log_or = max(max_abs_log_or, float(log_or.abs().max()))

    bar_height = float(params.get("bar_height", 0.68))
    for ax, gs_val in zip(axes, genesets):
        log_or, colors = per_geneset[gs_val]
        ax.barh(y_pos, log_or.fillna(0.0), height=bar_height, color=colors,
               edgecolor=params.get("bar_edgecolor", "black"),
               linewidth=float(params.get("bar_edgewidth", 0.5)), zorder=3)
        ax.axvline(0, color="black", linewidth=0.8, zorder=2)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features, fontsize=tick_sz)
        ax.set_title(rename.get(gs_val, str(gs_val)), fontsize=a_sz, fontweight="bold")
        ax.tick_params(axis="x", labelsize=tick_sz)
        ax.grid(axis="x", alpha=0.25, linestyle="--", zorder=0)

        # Draw soft horizontal swimlanes to match feature colors from stacked bar
        feature_colors = params.get("feature_colors")
        if not feature_colors:
            feature_colors = {
                "Promoter": "#4682b4",
                "Intron": "#f39c12",
                "Distal Intergenic": "#2ecc71",
                "Exon": "#9b59b6",
                "3' UTR": "#e74c3c",
                "Downstream": "#1abc9c",
                "5' UTR": "#95a5a6",
            }
        if feature_colors:
            for y, feat in zip(y_pos, features):
                c = feature_colors.get(feat)
                if c:
                    ax.axhspan(y - 0.45, y + 0.45, facecolor=c, alpha=0.08, zorder=1)
        if xlim_override is not None:
            # An explicit override (e.g. a global max computed across
            # several SEPARATE render calls -- one per row/panel here, not
            # facets within this one call -- so this function's own
            # per-call max_abs_log_or can't see it) always wins over the
            # auto-computed shared range below.
            ax.set_xlim(float(xlim_override[0]), float(xlim_override[1]))
        elif shared_xlim and max_abs_log_or > 0:
            lim = max_abs_log_or * xlim_pad
            ax.set_xlim(-lim, lim)

    axes[0].set_ylabel("", fontsize=a_sz)
    mid = axes[len(axes) // 2]
    mid.set_xlabel(text_param(params, "xlabel_text", "log2(Odds Ratio) vs background"), fontsize=a_sz)

    if params.get("show_legend", True):
        from matplotlib.patches import Patch
        handles = [Patch(facecolor=sig_color, edgecolor="black", label=f"FDR < {fdr_max:g}"),
                  Patch(facecolor=ns_color, edgecolor="black", label="n.s.")]
        axes[-1].legend(handles=handles, loc=params.get("legend_loc", "best"), fontsize=tick_sz)

    # fig.suptitle() silently produces no visible text on a SubFigure in
    # this matplotlib version (confirmed via the saved SVG containing zero
    # occurrences of the title string) -- fig.text() with the subfigure's
    # own transform is the same fallback already used for legend placement
    # elsewhere in this codebase (see cross_condition_heatmap.py) and does
    # render correctly on both a root Figure and a SubFigure.
    title = text_param(params, "labels_title", "Peak Feature Enrichment vs Background")
    fig.text(0.5, 0.99, title, ha="center", va="top", fontsize=title_sz, fontweight="bold",
            transform=fig.transSubfigure if hasattr(fig, "transSubfigure") else fig.transFigure)
    return df


@uses_schema(SCHEMA)
def render_peak_feature_composition(fig, df, params):
    """Draw a 100%-stacked bar chart (feature composition) onto ``fig``.

    One pair of stacked bars (DA peaks, Background) per GeneSet group,
    segments = Feature categories stacked bottom-to-top in feature_order
    (so listing e.g. Promoter first puts it at the bottom of every bar) --
    shows the plain compositional percentages the odds ratio in
    render_peak_feature_enrichment was computed from, as parts of a whole,
    rather than that renderer's per-feature DA-vs-background comparison.

    params: geneset_col('GeneSet'), geneset_order, geneset_rename_map,
            feature_col('Feature'), feature_order, da_pct_col('DA_Pct'),
            background_pct_col('Background_Pct'), feature_colors (dict of
            {feature: hex}; falls back to an evenly-spaced qualitative
            colormap), bar_width, group_gap, edge_color, edge_width,
            ylabel_text, labels_title, show_legend, legend_loc,
            axes_label_size, tick_label_size, title_size
    """
    from matplotlib import cm
    from matplotlib.patches import Patch

    a_sz = params.get("axes_label_size", 11)
    title_sz = params.get("title_size", 13)
    tick_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    geneset_col = params.get("geneset_col", "GeneSet")
    feature_col = params.get("feature_col", "Feature")
    da_col = params.get("da_pct_col", "DA_Pct")
    bg_col = params.get("background_pct_col", "Background_Pct")
    required = {geneset_col, feature_col, da_col, bg_col}
    if df.empty or not required.issubset(df.columns):
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    genesets = params.get("geneset_order") or list(dict.fromkeys(df[geneset_col]))
    features = params.get("feature_order") or list(dict.fromkeys(df[feature_col]))
    rename = params.get("geneset_rename_map", {})
    bar_w = float(params.get("bar_width", 0.7))
    group_gap = float(params.get("group_gap", 1.0))

    custom_colors = params.get("feature_colors")
    if custom_colors:
        colors = [custom_colors.get(f, "#cccccc") for f in features]
    else:
        cmap = cm.get_cmap("tab20", max(len(features), 1))
        colors = [cmap(i) for i in range(len(features))]

    ax = fig.add_subplot(111)
    x_positions, x_labels, group_centers = [], [], []
    x = 0.0
    for gs_val in genesets:
        sub = df[df[geneset_col] == gs_val].set_index(feature_col)
        da_pct = pd.to_numeric(sub.reindex(features)[da_col], errors="coerce").fillna(0.0)
        bg_pct = pd.to_numeric(sub.reindex(features)[bg_col], errors="coerce").fillna(0.0)
        group_start = x
        for bar_label, pct in (("DA", da_pct), ("Background", bg_pct)):
            bottom = 0.0
            for feat, color in zip(features, colors):
                val = float(pct.get(feat, 0.0))
                ax.bar(x, val, width=bar_w, bottom=bottom, color=color,
                      edgecolor=params.get("edge_color", "white"),
                      linewidth=float(params.get("edge_width", 0.5)), zorder=3)
                bottom += val
            x_positions.append(x)
            x_labels.append(bar_label)
            x += 1.0
        group_centers.append((group_start + x - 1) / 2)
        x += group_gap

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, fontsize=tick_sz, rotation=30, ha="right")
    ax.set_ylabel(text_param(params, "ylabel_text", "% of peaks"), fontsize=a_sz)
    ax.set_ylim(0, 100)
    ax.tick_params(axis="y", labelsize=tick_sz)

    # Facet group labels (total/up/down) above each pair of bars, placed via
    # the x-axis transform (x in data coords, y in axes-fraction) so they
    # don't require inflating ylim past the natural 0-100 range.
    for center, gs_val in zip(group_centers, genesets):
        ax.text(center, 1.02, rename.get(gs_val, str(gs_val)), ha="center", va="bottom",
               fontsize=a_sz, fontweight="bold", transform=ax.get_xaxis_transform())

    if params.get("show_legend", True):
        handles = [Patch(facecolor=c, edgecolor="black", label=f) for f, c in zip(features, colors)]
        ax.legend(handles=handles, loc=params.get("legend_loc", "center left"),
                 bbox_to_anchor=(1.01, 0.5), fontsize=tick_sz, title="Feature",
                 title_fontsize=tick_sz, frameon=False)

    title = text_param(params, "labels_title", "Peak Feature Composition")
    ax.set_title(title, fontsize=title_sz, fontweight="bold", pad=22)
    return df
