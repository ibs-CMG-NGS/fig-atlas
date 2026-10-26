"""Full-grid motif-enrichment dot plot.

Synthesized (Case C) from the motif_summary_figure reference: a motif x
condition grid where EVERY cell draws a dot -- significant motifs are sized by
-log10(P) and colored by log2 fold enrichment (diverging, red=up/blue=down),
while non-significant cells draw a tiny gray placeholder dot. Input is
long-format with NaN value/p for the non-significant cells.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd

from fig_atlas.params import text_param


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("motif_dotplot", params=[
    # [Data]
    Param("term_col", str, "motif", role="Column with the motif (row) names"),
    Param("class_col", str, "pattern_class", role="Column with the condition (column) names"),
    Param("value_col", str, "log2fc", role="Column coloured: log2 fold enrichment"),
    Param("p_col", str, "neg_log10_p", role="Column sized: -log10(P)"),
    Param("class_order", list, None, role="Column order (default: order in the data)"),
    Param("term_order", list, None, role="Row order (default: order in the data)"),
    Param("condition_rename_map", dict, {}, open_keys=True, role="Display label per condition"),
    # [Dot colour]
    Param("fc_cmap", "cmap", "RdBu_r", role="Diverging colormap of the fold enrichment"),
    Param("fc_min", float, -2.0, unit="log2 fold enrichment", role="Lower colour limit"),
    Param("fc_max", float, 2.0, unit="log2 fold enrichment", role="Upper colour limit"),
    Param("na_color", "color", "#cccccc", unit="hex color", role="Colour of the placeholder dot in empty cells"),
    Param("show_colorbar", bool, True, role="Show the colourbar"),
    Param("colorbar_label", str, "log2 fold enrichment", role="Colourbar title"),
    Param("colorbar_loc", ("right", "left", "top", "bottom"), CODE_DEFAULT,
          role="Side of the colourbar (default: opposite the motif labels)"),
    Param("colorbar_shrink", float, 0.6, unit="fraction of the axes height", range=(0, 1), role="Colourbar length"),
    # [Dot size]
    Param("size_min", float, 6.0, unit="pt^2 (marker area)", range=(0, None), role="Dot area at -log10(P) = 0"),
    Param("size_scale", float, 30.0, unit="pt^2 per -log10(P) unit", range=(0, None),
          role="Added dot area per -log10(P) unit", tune="lower if neighbouring dots overlap"),
    Param("na_size", float, CODE_DEFAULT, unit="pt^2 (marker area)", range=(0, None), role="Placeholder dot size (default 0.4 x size_min)"),
    Param("dot_alpha", float, 0.9, unit="alpha [0-1]", range=(0, 1), role="Dot opacity"),
    Param("dot_edgecolor", "color", "#555555", unit="hex color", role="Dot outline colour"),
    Param("dot_edgewidth", float, 0.5, unit="pt", range=(0, None), role="Dot outline width"),
    Param("show_size_legend", bool, True, role="Show the dot size legend"),
    Param("size_legend_title", str, "-log10(P)", role="Size legend title"),
    Param("size_legend_loc", str, "best", role="Size legend location (matplotlib loc string)"),
    Param("size_legend_values", list, None, unit="-log10(P)", role="Values shown in the size legend (default 0, 5, 10)"),
    # [Grid]
    Param("show_grid", bool, True, role="Draw horizontal grid lines"),
    Param("grid_color", "color", "#eeeeee", unit="hex color", role="Grid line colour"),
    # [Layout]
    Param("term_label_side", ("left", "right"), "left", role="Side of the motif labels"),
    Param("label_margin_pad", float, 1.2, unit="multiple of the measured label width", range=(0, None),
          role="Room left for the motif labels", tune="raise if labels clip the canvas edge"),
    Param("label_margin_cap", float, 0.5, unit="fraction of the panel width", range=(0, 1), role="Largest label margin"),
    Param("min_plot_frac", float, 0.3, unit="fraction of the panel width", range=(0, 1), role="Smallest width kept for the dots"),
    Param("colorbar_margin", float, 0.1, unit="fraction of the panel width", range=(0, 1),
          role="Left margin for the colourbar when the labels are on the right"),
    # [Labels]
    Param("labels_title", str, "Motif Enrichment", role="Panel title"),
    Param("labels_subtitle", str, None, role="Second line under the title"),
    Param("title_pad", float, 24.0, unit="pt", range=(0, None), role="Gap between title and axes"),
    Param("xtick_rotation", float, 45, unit="degrees", role="Condition label rotation"),
    Param("xtick_ha", ("left", "center", "right"), "right", role="Condition label horizontal alignment"),
    Param("xtick_rotation_mode", str, None, role="matplotlib rotation_mode for the condition labels ('anchor' or 'default')"),
    Param("xtick_fontsize", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Condition label size (default tick_label_size)"),
    Param("term_fontsize", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Motif label size (default tick_label_size)"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("subtitle_size", float, 9, unit="pt", range=(0, None), role="Subtitle font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Colourbar title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_motif_dotplot(ax, df, params):
    """Draw a full-grid motif enrichment dot plot onto ``ax``.

    params: term_col('motif'), class_col('pattern_class'),
            value_col('log2fc'), p_col('neg_log10_p'),
            class_order(list), term_order(list),
            condition_rename_map (dict raw -> display label for x-tick text),
            fc_cmap('RdBu_r'), fc_min, fc_max (symmetric diverging range),
            na_color, na_size (placeholder dot for non-significant cells),
            size_min, size_scale (size = size_min + -log10P * size_scale),
            size_legend_values, size_legend_title, show_size_legend,
            show_colorbar, colorbar_label, colorbar_loc, colorbar_shrink,
            dot_edgecolor, dot_edgewidth, dot_alpha,
            show_grid, grid_color,
            xtick_rotation, xtick_ha, xtick_fontsize, xtick_rotation_mode,
            term_fontsize, term_label_side, label_margin_pad, label_margin_cap,
            labels_title, labels_subtitle, axes_label_size, tick_label_size,
            title_size, subtitle_size
    """
    import matplotlib as mpl
    import matplotlib.colors as mcolors
    from matplotlib.lines import Line2D
    title_sz = params.get("title_size", 13)
    sub_sz = params.get("subtitle_size", 9)
    a_sz = params.get("axes_label_size", 11)
    t_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    term_col = params.get("term_col", "motif")
    class_col = params.get("class_col", "pattern_class")
    value_col = params.get("value_col", "log2fc")
    p_col = params.get("p_col", "neg_log10_p")

    class_order = params.get("class_order") or list(dict.fromkeys(df[class_col]))
    term_order_param = params.get("term_order")
    if term_order_param:
        present = set(df[term_col])
        term_order = [t for t in term_order_param if t in present]
    else:
        term_order = list(dict.fromkeys(df[term_col]))
    class_pos = {c: i for i, c in enumerate(class_order)}
    term_pos = {t: i for i, t in enumerate(term_order)}

    df = df[df[term_col].isin(term_pos) & df[class_col].isin(class_pos)].copy()
    x = df[class_col].map(class_pos)
    y = df[term_col].map(term_pos)
    fc = pd.to_numeric(df[value_col], errors="coerce")
    pval = pd.to_numeric(df[p_col], errors="coerce")
    selected = pval.notna() & fc.notna()

    size_min = float(params.get("size_min", 6.0))
    size_scale = float(params.get("size_scale", 30.0))
    na_size = float(params.get("na_size", size_min * 0.4))
    sizes = np.where(selected, size_min + np.nan_to_num(pval.to_numpy()) * size_scale,
                     na_size)

    fc_min = float(params.get("fc_min", -2.0))
    fc_max = float(params.get("fc_max", 2.0))
    norm = mcolors.Normalize(vmin=fc_min, vmax=fc_max)
    cmap = params.get("fc_cmap", "RdBu_r")
    na_color = params.get("na_color", "#cccccc")
    cmap_obj = mpl.colormaps[str(cmap)]

    alpha = float(params.get("dot_alpha", 0.9))
    edge = params.get("dot_edgecolor", "#555555")
    edge_w = float(params.get("dot_edgewidth", 0.5))

    # Significant dots on top.
    sc = ax.scatter(x[selected], y[selected], s=sizes[selected],
                    c=fc[selected].to_numpy(), cmap=cmap_obj, norm=norm,
                    alpha=alpha, edgecolors=edge, linewidths=edge_w, zorder=3)
    if (~selected).any():
        ax.scatter(x[~selected], y[~selected], s=sizes[~selected],
                   c=na_color, alpha=0.5, edgecolors=edge, linewidths=edge_w,
                   zorder=2)

    ax.set_xlim(-0.5, len(class_order) - 0.5)
    ax.set_ylim(-0.5, len(term_order) - 0.5)
    ax.invert_yaxis()

    if params.get("show_grid", True):
        ax.grid(axis="y", color=params.get("grid_color", "#eeeeee"),
                linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

    condition_rename_map = params.get("condition_rename_map", {})
    condition_labels = [condition_rename_map.get(c, c) for c in class_order]
    ax.set_xticks(range(len(class_order)))
    xt_kwargs = dict(fontsize=params.get("xtick_fontsize", t_sz),
                     rotation=float(params.get("xtick_rotation", 45)),
                     ha=params.get("xtick_ha", "right"))
    if params.get("xtick_rotation_mode"):
        xt_kwargs["rotation_mode"] = params["xtick_rotation_mode"]
        xt_kwargs["va"] = "top"
    ax.set_xticklabels(condition_labels, **xt_kwargs)

    term_fs = params.get("term_fontsize", t_sz)
    ax.set_yticks(range(len(term_order)))
    ax.set_yticklabels([str(t) for t in term_order], fontsize=term_fs)
    if params.get("term_label_side", "left") == "right":
        ax.yaxis.tick_right()

    # Sized left margin from measured label extent (short motif names, but
    # font/DPI vary), then attach colorbar AFTER (it steals ax space).
    root_fig = getattr(ax.figure, "figure", ax.figure)
    renderer = root_fig.canvas.get_renderer()
    label_px = max((t.get_window_extent(renderer=renderer).width
                    for t in ax.get_yticklabels()), default=0)
    pos = ax.get_position()
    panel_px = pos.width * ax.figure.bbox.width
    pad = float(params.get("label_margin_pad", 1.2))
    needed_frac = (label_px + 0.12 * root_fig.dpi) / panel_px * pad if panel_px > 0 else 0.12
    label_margin = min(float(params.get("label_margin_cap", 0.5)),
                       max(0.06, needed_frac))
    min_plot_frac = float(params.get("min_plot_frac", 0.3))
    if params.get("term_label_side", "left") == "right":
        left_margin = float(params.get("colorbar_margin", 0.1))
        label_margin = min(label_margin, 1 - left_margin - min_plot_frac)
        ax.set_position([left_margin, pos.y0, (1 - label_margin) - left_margin, pos.height])
        default_cbar_loc = "left"
    else:
        label_margin = min(label_margin, 0.97 - min_plot_frac)
        ax.set_position([label_margin, pos.y0, 0.97 - label_margin, pos.height])
        default_cbar_loc = "right"

    if params.get("show_colorbar", True):
        cbar = ax.figure.colorbar(sc, ax=ax,
                                  location=params.get("colorbar_loc", default_cbar_loc),
                                  shrink=float(params.get("colorbar_shrink", 0.6)),
                                  pad=0.02, use_gridspec=False)
        cbar.set_label(text_param(params, "colorbar_label", "log2 fold enrichment"),
                       fontsize=a_sz)
        cbar.ax.tick_params(labelsize=t_sz)

    if params.get("show_size_legend", True):
        reps = params.get("size_legend_values")
        if reps is None:
            reps = [0.0, 5.0, 10.0]
        handles = [Line2D([], [], marker="o", linestyle="none",
                          markersize=np.sqrt(size_min + float(v) * size_scale),
                          markerfacecolor="#aaaaaa", markeredgecolor=edge,
                          markeredgewidth=edge_w, label=f"{v:g}")
                   for v in reps]
        ax.legend(handles=handles, title=params.get("size_legend_title", "-log10(P)"),
                  loc=params.get("size_legend_loc", "best"),
                  fontsize=t_sz, title_fontsize=t_sz, framealpha=0.9,
                  handletextpad=0.6, labelspacing=0.9)

    title = text_param(params, "labels_title", "Motif Enrichment")
    subtitle = params.get("labels_subtitle")
    if subtitle:
        ax.set_title(title, fontsize=title_sz, fontweight="bold", pad=float(params.get("title_pad", 24.0)))
        ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=sub_sz, color="gray")
    else:
        ax.set_title(title, fontsize=title_sz, fontweight="bold")

    return df
