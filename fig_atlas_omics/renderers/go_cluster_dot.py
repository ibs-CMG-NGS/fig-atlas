"""GO cluster-summary dot plot renderer, ported from go_bp_*_cluster_dot_bundle.

Each row is a cluster representative term (already clustered/deduplicated
upstream). Draws onto a Matplotlib Figure or SubFigure. All visual attributes
come from ``params``.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd

from fig_atlas.params import text_param

_C_CLUSTER, _C_FDR, _C_RATIO, _C_FE = "cluster_id", "fdr", "gene_ratio", "fold_enrichment"
_C_COUNT, _C_DESC, _C_ONT, _C_DIR = "gene_count", "description", "ontology", "direction"


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("go_cluster_dot", params=[
    # [Clusters]
    Param("top_n", int, 20, unit="clusters", range=(1, None), role="Clusters shown"),
    Param("top_n_by", ("FDR", "Fold Enrichment"), "FDR", role="Which clusters are kept when there are more than top_n"),
    Param("sort_by", ("FDR", "Cluster Size", "Term Name"), "FDR", role="Row order of the kept clusters"),
    Param("ylabel_wrap_width", int, 60, unit="characters", range=(1, None), role="Characters kept from each term name"),
    # [Axes]
    Param("x_axis", ("-log10(FDR)", "Gene Ratio", "Fold Enrichment"), "Fold Enrichment", role="Metric on the x axis"),
    Param("x_min", float, None, unit="data coords", role="Lower x limit (default: data)"),
    Param("x_max", float, None, unit="data coords", role="Upper x limit (default: data)"),
    Param("y_min", float, None, unit="row index", role="Lower y limit (default: data)"),
    Param("y_max", float, None, unit="row index", role="Upper y limit (default: data)"),
    Param("show_zero_line", bool, True, role="Draw the x = 0 reference line"),
    Param("zero_line_color", "color", "gray", unit="color", role="Reference line colour"),
    Param("zero_line_width", float, 0.6, unit="pt", range=(0, None), role="Reference line width"),
    Param("zero_line_style", str, "-", role="Reference line style (matplotlib linestyle)"),
    # [Dot colour]
    Param("color_by", ("Fold Enrichment", "Fold Enrichment (median)", "FDR", "Ontology", "Direction"), "Fold Enrichment",
          role="What the dot colour encodes"),
    Param("cmap", str, CODE_DEFAULT, role="Colormap (default YlOrRd for fold enrichment, viridis_r for FDR)"),
    Param("z_auto", bool, True, role="Colour scale from the data; set false to use z_min/z_max"),
    Param("z_min", float, CODE_DEFAULT, unit="colour metric units", role="Lower colour limit when z_auto is false"),
    Param("z_max", float, CODE_DEFAULT, unit="colour metric units", role="Upper colour limit when z_auto is false"),
    Param("direction_colors", dict, {"UP": "#e74c3c", "DOWN": "#3498db", "TOTAL": "#95a5a6"}, open_keys=True,
          unit="hex color", role="Colour per direction when color_by is Direction"),
    Param("dot_default_color", "color", "#3498db", unit="hex color", role="Dot colour when the color_by column is missing"),
    Param("colorbar_loc", ("right", "left", "top", "bottom"), "right", role="Side of the colourbar"),
    Param("colorbar_shrink", float, 0.6, unit="fraction of the axes height", range=(0, 1), role="Colourbar length"),
    Param("color_legend_loc", str, "best", role="Location of the Ontology/Direction colour key"),
    # [Dot size]
    Param("size_by", ("Cluster size", "Gene count"), "Cluster size", role="What the dot size encodes"),
    Param("dot_size_min", float, 40.0, unit="pt^2 (marker area)", range=(0, None), role="Size of the smallest dot"),
    Param("dot_size_scale", float, 20.0, unit="pt^2 per unit", range=(0, None), role="Added area per member or gene",
          tune="lower if large dots overlap"),
    Param("dot_alpha", float, 0.85, unit="alpha [0-1]", range=(0, 1), role="Dot opacity"),
    Param("dot_edgecolor", "color", "black", unit="color", role="Dot outline colour"),
    Param("dot_edgewidth", float, 0.8, unit="pt", range=(0, None), role="Dot outline width"),
    Param("show_size_legend", bool, True, role="Show the dot size legend"),
    Param("size_legend_loc", str, "best", role="Size legend location (matplotlib loc string)"),
    Param("size_legend_values", list, None, role="Values shown in the size legend (default: three spread values)"),
    # [Labels]
    Param("labels_title", str, CODE_DEFAULT, role="Panel title (default names top N and the size metric)"),
    Param("title", str, CODE_DEFAULT, role="Older name of labels_title, used when labels_title is not set"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_go_cluster_dot(fig, df, params):
    """Draw a GO cluster-summary dot plot onto ``fig`` (Figure or SubFigure).

    params: x_axis('-log10(FDR)'|'Gene Ratio'|'Fold Enrichment'),
            color_by('Fold Enrichment'|'FDR'|'Ontology'|'Direction'),
            size_by('Cluster size'|'Gene count'), sort_by('FDR'|'Cluster Size'|'Term Name'),
            top_n, top_n_by, dot_size_min, dot_size_scale, cmap, z_auto, z_min, z_max,
            colorbar_loc, colorbar_shrink, show_size_legend, size_legend_loc
            (any matplotlib legend loc string, e.g. 'upper left'), size_legend_values
            (explicit list of size-legend category values; defaults to an
            auto-computed 3-value spread when omitted), color_legend_loc
            (Ontology/Direction color-key legend, default 'lower right'),
            dot_alpha, dot_edgecolor, dot_edgewidth, dot_default_color
            (fallback dot fill when color_by has no usable column),
            direction_colors (dict of {direction: hex} for color_by='Direction'),
            ylabel_wrap_width (max chars kept from each term description),
            show_zero_line, zero_line_color, zero_line_width, zero_line_style
            (the x=0 reference vline), x_min, x_max, y_min, y_max,
            labels_title, axes_label_size, tick_label_size, title_size
    """
    import matplotlib.colors as mcolors
    from matplotlib import cm
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    a_sz = params.get("axes_label_size", 11)
    title_sz = params.get("title_size", 13)
    tick_sz = params.get("tick_label_size", 8)

    ax = fig.add_subplot(111)
    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax.text(0.5, 0.5, "No clustered data available", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        ax.axis("off")
        return None
    if "_cluster_size" not in df.columns:
        df["_cluster_size"] = 1

    sort_by = params.get("sort_by", "FDR")
    if sort_by == "FDR" and _C_FDR in df.columns:
        df = df.sort_values(_C_FDR, ascending=False)
    elif sort_by == "Cluster Size":
        df = df.sort_values("_cluster_size", ascending=True)
    elif sort_by == "Term Name" and _C_DESC in df.columns:
        df = df.sort_values(_C_DESC, ascending=False)

    top_n = int(params.get("top_n", 20))
    top_n_by = params.get("top_n_by", "FDR")
    if len(df) > top_n:
        if top_n_by == "Fold Enrichment" and _C_FE in df.columns:
            keep = pd.to_numeric(df[_C_FE], errors="coerce").fillna(
                float("-inf")).nlargest(top_n).index
        elif _C_FDR in df.columns:
            keep = df.nsmallest(top_n, _C_FDR).index
        else:
            keep = df.index[:top_n]
        df = df.loc[df.index.isin(keep)]
    n_terms = len(df)

    cluster_ids = df[_C_CLUSTER].tolist() if _C_CLUSTER in df.columns else list(range(n_terms))

    def _cid_prefix(cid):
        return f"C{cid}: " if str(cid).isdigit() else ""

    wrap_w = int(params.get("ylabel_wrap_width", 60))
    if _C_DESC in df.columns:
        import textwrap
        y_labels = [textwrap.fill(f"{_cid_prefix(cid)}{str(v)}", width=wrap_w,
                                   break_long_words=False)
                    for cid, v in zip(cluster_ids, df[_C_DESC])]
    else:
        y_labels = [f"C{cid}" if str(cid).isdigit() else str(cid) for cid in cluster_ids]

    # Renderer-independent left margin, applied BEFORE the colorbar/legends
    # are added below: fig.colorbar(sc, ax=ax) steals space from ax's
    # position at call time and places its own cax there -- if ax is moved
    # afterwards, the colorbar doesn't move with it and ends up overlapping
    # the plot instead of sitting outside it. ax.set_position() (rather than
    # fig.subplots_adjust()/tight_layout(), which on a SubFigure mutate the
    # ROOT figure's shared subplotpars instead of confining themselves to it)
    # is safe here since nothing has attached to ax's position yet.
    #
    # Sized from the labels' actually-rendered extent (measured via the Agg
    # renderer), not a character-count heuristic: matplotlib doesn't clip
    # tick labels to the subfigure boundary, so any estimate that undershoots
    # real glyph widths -- proportional fonts, wide/narrow letter mixes --
    # overflows straight into the neighboring panel. A real measurement can't
    # undershoot in the same way a guessed average character width can.
    ax.set_yticks(list(range(n_terms)))
    ax.set_yticklabels(y_labels, fontsize=tick_sz)
    # get_window_extent() needs a renderer, which only the root figure's
    # canvas has -- but the pixel width to size the margin against must be
    # THIS axes' own parent SubFigure's bbox (ax.figure), not the root
    # figure's (a SubFigure only occupies a fraction of the root canvas, so
    # using the root's full width there would drastically overestimate the
    # space actually available and undersize the margin).
    root_fig = getattr(ax.figure, "figure", ax.figure)
    renderer = root_fig.canvas.get_renderer()
    label_px = max((t.get_window_extent(renderer=renderer).width
                     for t in ax.get_yticklabels()), default=0)
    pos = ax.get_position()
    panel_px = pos.width * ax.figure.bbox.width
    needed_frac = (label_px + 0.12 * root_fig.dpi) / panel_px if panel_px > 0 else 0.3
    left = min(0.78, max(0.12, needed_frac))
    # Right edge close to this SubFigure's own full width (not the old
    # hardcoded 0.85): this subfigure already has its own gap from its
    # sibling panels via the calling script's gridspec wspace, so reserving
    # extra padding here on top of that only starves the dot-plot area --
    # confirmed visually: long labels pushed `left` out past 0.7, leaving
    # under 10% of the panel for the actual dots once colorbar carved its
    # own slice out of the 0.85 boundary. The colorbar call below shrinks ax
    # again from whatever right edge it finds, so it's safe to start wide.
    ax.set_position([left, pos.y0, 0.97 - left, pos.height])

    x_axis = params.get("x_axis", "Fold Enrichment")
    if x_axis == "-log10(FDR)" and _C_FDR in df.columns:
        x_vals = [-np.log10(max(float(v), 1e-300)) for v in df[_C_FDR]]
        x_label = "-log10(FDR)"
    elif x_axis == "Gene Ratio" and _C_RATIO in df.columns:
        x_vals = []
        for v in df[_C_RATIO]:
            try:
                if "/" in str(v):
                    a, b = str(v).split("/")
                    x_vals.append(float(a) / float(b))
                else:
                    x_vals.append(float(v))
            except Exception:
                x_vals.append(0.0)
        x_label = "Gene Ratio"
    elif x_axis == "Fold Enrichment" and _C_FE in df.columns:
        x_vals = [float(v) if pd.notna(v) else 0.0 for v in df[_C_FE]]
        x_label = "Fold Enrichment"
    elif _C_FDR in df.columns:
        x_vals = [-np.log10(max(float(v), 1e-300)) for v in df[_C_FDR]]
        x_label = "-log10(FDR)"
    else:
        x_vals = list(range(n_terms))
        x_label = "Index"

    color_by = params.get("color_by", "Fold Enrichment")
    legend_handles = []
    scatter_cmap = scatter_norm = None
    color_label = "FDR"
    if color_by in ("Fold Enrichment", "Fold Enrichment (median)") and (
            _C_FE in df.columns or "_fe_median" in df.columns):
        fe_col = ("_fe_median" if color_by == "Fold Enrichment (median)"
                  and "_fe_median" in df.columns else _C_FE)
        fe_vals = pd.to_numeric(df[fe_col], errors="coerce").fillna(0.0).tolist() \
            if fe_col in df.columns else []
        if fe_vals:
            if params.get("z_auto", True):
                vmin, vmax = min(fe_vals), max(fe_vals)
            else:
                vmin = float(params.get("z_min", 0.0))
                vmax = float(params.get("z_max", 1.0))
            if vmax <= vmin:
                vmax = vmin + 1.0
            scatter_norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            cmap_name = params.get("cmap", "YlOrRd_r")
            if cmap_name.endswith("_r"):
                cmap_name = cmap_name[:-2]
            scatter_cmap = cmap_name
            dot_colors = fe_vals
            color_label = ("Fold Enrichment (cluster median)"
                           if fe_col == "_fe_median" else "Fold Enrichment")
        else:
            dot_colors = params.get("dot_default_color", "#3498db")
    elif color_by == "FDR" and _C_FDR in df.columns:
        fdr_vals = [float(v) for v in df[_C_FDR]]
        if params.get("z_auto", True):
            vmin = max(min(fdr_vals), 1e-300) if fdr_vals else 1e-300
            vmax = max(max(fdr_vals, default=1.0), vmin * 10)
        else:
            vmin = max(float(params.get("z_min", 1e-10)), 1e-300)
            vmax = float(params.get("z_max", 0.05))
            if vmax <= vmin:
                vmax = vmin * 10
        scatter_norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
        scatter_cmap = params.get("cmap", "viridis_r")
        dot_colors = fdr_vals
        color_label = "FDR (representative term)"
    elif color_by == "Ontology" and _C_ONT in df.columns:
        onts = df[_C_ONT].tolist()
        uniq = list(dict.fromkeys(onts))
        cmap_ont = cm.tab10
        ont_map = {o: cmap_ont(i / max(len(uniq), 1)) for i, o in enumerate(uniq)}
        dot_colors = [ont_map.get(str(o), "#aaa") for o in onts]
        legend_handles = [Patch(color=ont_map[o], label=o) for o in uniq]
    elif color_by == "Direction" and _C_DIR in df.columns:
        dir_c = params.get("direction_colors",
                           {"UP": "#e74c3c", "DOWN": "#3498db", "TOTAL": "#95a5a6"})
        dot_colors = [dir_c.get(str(d), "#95a5a6") for d in df[_C_DIR]]
        seen = list(dict.fromkeys(df[_C_DIR].tolist()))
        legend_handles = [Patch(color=dir_c.get(str(d), "#aaa"), label=str(d)) for d in seen]
    else:
        dot_colors = params.get("dot_default_color", "#3498db")

    size_by = params.get("size_by", "Cluster size")
    dot_min = float(params.get("dot_size_min", 40.0))
    dot_scale = float(params.get("dot_size_scale", 20.0))
    if size_by == "Gene count" and _C_COUNT in df.columns:
        size_src = pd.to_numeric(df[_C_COUNT], errors="coerce").fillna(1)
        size_legend_title = "Genes"
    else:
        size_src = df["_cluster_size"]
        size_legend_title = "Members"
        size_by = "Cluster size"
    # When an explicit size_legend_values is given, cap dots at its largest
    # value so a real outlier can never render bigger than the legend's top
    # reference circle (and bleed into a neighboring row) -- values above the
    # cap all render at the same size as that top reference, same as the
    # legend swatches below.
    custom_legend_values = params.get("size_legend_values")
    size_cap = max(custom_legend_values) if custom_legend_values else None
    def _capped(v):
        v = float(v)
        return min(v, size_cap) if size_cap is not None else v
    dot_sizes = [max(dot_min, _capped(s) * dot_scale) for s in size_src]

    dot_alpha = float(params.get("dot_alpha", 0.85))
    dot_edgecolor = params.get("dot_edgecolor", "black")
    dot_edgewidth = float(params.get("dot_edgewidth", 0.8))

    y_pos = list(range(n_terms))
    sc = ax.scatter(x_vals, y_pos, s=dot_sizes, c=dot_colors,
                    cmap=scatter_cmap, norm=scatter_norm, alpha=dot_alpha,
                    edgecolors=dot_edgecolor, linewidths=dot_edgewidth, zorder=3)

    if scatter_cmap is not None and scatter_norm is not None:
        # use_gridspec=False: the default (True) recomputes ax's position
        # from its ORIGINAL subplotspec, silently discarding the manual
        # ax.set_position() margin fix above -- confirmed by direct repro
        # (ax snapped back to ~0.125-0.9 immediately after fig.colorbar()
        # regardless of what set_position() had just done). use_gridspec
        # =False shrinks ax from its actual CURRENT position instead.
        cbar = fig.colorbar(sc, ax=ax, location=params.get("colorbar_loc", "right"),
                            shrink=float(params.get("colorbar_shrink", 0.6)), pad=0.02,
                            use_gridspec=False)
        cbar.set_label(color_label, fontsize=tick_sz + 2)
        cbar.ax.tick_params(labelsize=tick_sz)

    if params.get("show_size_legend", True):
        if custom_legend_values:
            counts = list(custom_legend_values)
        else:
            max_v = int(size_src.max()) if len(size_src) else 1
            if max_v <= 4:
                counts = list(range(1, max_v + 1))
            else:
                counts = sorted(set([1] + [int(round(v)) for v in np.linspace(max_v / 3, max_v, 3)]))
        size_handles = [ax.scatter([], [], s=max(dot_min, float(cnt) * dot_scale), c="#aaaaaa",
                                   alpha=dot_alpha, edgecolors=dot_edgecolor,
                                   linewidths=dot_edgewidth, label=f"{cnt:g}")
                        for cnt in counts]
    else:
        size_handles = []

    if legend_handles:
        color_leg = ax.legend(handles=legend_handles,
                              loc=params.get("color_legend_loc", "best"),
                              title=color_by, framealpha=0.9, fontsize=tick_sz,
                              title_fontsize=tick_sz)
        ax.add_artist(color_leg)
    if size_handles:
        # "best" (matplotlib's collision-avoiding auto-placement) is the
        # default rather than a fixed corner: which corner is actually empty
        # of dots depends on the data (FDR/enrichment distribution) and can
        # flip between panels or after a data refresh, so a hardcoded corner
        # silently starts overlapping dots again -- "best" adapts every render.
        ax.legend(handles=size_handles, title=size_legend_title,
                  loc=params.get("size_legend_loc", "best"),
                  framealpha=0.9, handletextpad=1.2, labelspacing=1.0,
                  fontsize=tick_sz, title_fontsize=tick_sz)

    ax.tick_params(axis="x", labelsize=tick_sz)
    ax.set_xlabel(x_label, fontsize=a_sz, fontweight="bold")
    size_txt = "gene count" if size_by == "Gene count" else "cluster member count"
    default_title = f"GO Cluster Summary Dot Plot\nTop {n_terms} clusters  ·  dot size = {size_txt}"
    title = text_param(params, "labels_title", text_param(params, "title", default_title))
    ax.set_title(title, fontsize=title_sz, fontweight="bold")
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    if params.get("show_zero_line", True):
        ax.axvline(x=0, color=params.get("zero_line_color", "gray"),
                  linewidth=float(params.get("zero_line_width", 0.6)),
                  linestyle=params.get("zero_line_style", "-"))

    x_min, x_max = params.get("x_min"), params.get("x_max")
    if x_min is not None and x_max is not None:
        ax.set_xlim(float(x_min), float(x_max))
    y_min, y_max = params.get("y_min"), params.get("y_max")
    if y_min is not None and y_max is not None:
        ax.set_ylim(float(y_min) - 0.5, float(y_max) + 0.5)

    return df
