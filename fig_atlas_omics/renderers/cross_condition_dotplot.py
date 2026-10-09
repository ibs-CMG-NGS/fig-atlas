"""Cross-condition GO/KEGG enrichment dot plot.

Ported from cross_condition_dotplot_semantic-{bp,kegg} bundles (and the
identically-shaped cross_condition_top30_dotplot_semantic-bp bundle). Input
is the same long-format per (term, condition) rows as
cross_condition_heatmap.py: x = condition (categorical), y = GO term, dot
color = signed -log10(FDR) (continuous diverging: blue = down-regulated,
red = up-regulated), dot size = gene ratio. A term/condition pair with no
row in the export (never reached significance) is simply not drawn, unlike
the heatmap's explicit "absent" bin.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fig_atlas.params import text_param
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, typography, uses_schema

SCHEMA = Schema("cross_condition_dotplot", params=[
    *typography(title_size=13, axes_label_size=11, tick_label_size=8),
    # [Input columns]
    Param("term_col", str, "GO Term", role="Column of df with the term (row) names"),
    Param("condition_col", str, "Condition", role="Column of df with the condition (column) names"),
    Param("value_col", str, "Signed -log10(FDR)", role="Column of df with the value mapped to colour"),
    Param("size_col", str, "Gene Ratio", role="Column of df with the value mapped to dot size"),
    Param("direction_col", str, "Direction", role="Column of df with UP/DOWN, used by top_n_up / top_n_down"),
    Param("term_strip_pattern", str, None, role="Regex removed from term names before display"),
    # [Rows and columns]
    Param("condition_order", list, None, role="Column order (default: order of first appearance)"),
    Param("condition_rename_map", dict, {}, open_keys=True, role="x-tick label per raw condition (matching uses raw names)"),
    Param("term_order", list, None, role="Row order (default: order of first appearance)"),
    Param("top_n_up", int, None, unit="terms", range=(0, None), role="Keep only the top N UP terms per condition"),
    Param("top_n_down", int, None, unit="terms", range=(0, None), role="Keep only the top N DOWN terms per condition"),
    # [Colour]
    Param("cmap", "cmap", "RdBu_r", role="Colormap for value_col"),
    Param("color_auto", bool, True, role="Colour range symmetric around 0 from the data (else color_min / color_max)"),
    Param("color_min", float, -10.0, unit="value units", role="Lower end of the colour range when color_auto is false"),
    Param("color_max", float, 10.0, unit="value units", role="Upper end of the colour range when color_auto is false"),
    Param("gray_threshold", float, None, unit="value units",
          role="Values below it are drawn in gray_color and the colour scale starts there (e.g. -log10 0.05)"),
    Param("gray_color", "color", "#d0d0d0", unit="hex color",
          role="Fill of dots below gray_threshold ('#ffffff' for hollow, ring-only dots)"),
    # [Dots]
    Param("dot_size_min", float, 20.0, unit="pt^2 (marker area)", range=(0, None), role="Area of the smallest dot",
          tune="raise if small dots vanish"),
    Param("dot_size_scale", float, 800.0, unit="pt^2 per unit of size_col", range=(0, None),
          role="Dot area added per unit of size_col", tune="lower if dots overlap their neighbours"),
    Param("dot_edgecolor", "color", "#555555", unit="hex color", role="Dot outline colour"),
    Param("dot_edgewidth", float, 0.5, unit="pt", range=(0, None), role="Dot outline width"),
    Param("dot_alpha", float, 0.9, unit="[0-1] opacity", range=(0, 1), role="Dot opacity"),
    Param("grid", bool, True, role="Draw the background grid"),
    # [Labels]
    Param("labels_title", str, "Cross-Condition GO Dot Plot", role="Panel title"),
    Param("term_label_side", ("left", "right"), "right", role="Side the term labels sit on"),
    Param("term_fontsize", float, CODE_DEFAULT, unit="pt", role="Term label font size (default tick_label_size)"),
    Param("ylabel_wrap_width", int, 40, unit="characters", range=(1, None), role="Wrap term labels at this width"),
    Param("xtick_fontsize", float, CODE_DEFAULT, unit="pt", role="Condition label font size (default tick_label_size)"),
    Param("xtick_rotation", float, 45, unit="degrees", role="Condition label rotation"),
    Param("xtick_ha", ("left", "center", "right"), "right", role="Horizontal alignment of rotated condition labels"),
    Param("xtick_rotation_mode", str, None, role="'anchor' keeps multi-line rotated labels aligned (matplotlib rotation_mode)"),
    # [Layout]
    Param("reposition_axes", bool, True, role="Shrink the axes to make room for term labels and the colorbar"),
    Param("label_margin_pad", float, 1.2, unit="x measured label width",
          role="Room reserved for term labels beyond their measured width", tune="raise to shrink the plot area further"),
    Param("label_margin_cap", float, 0.82, unit="[0-1] panel fraction", range=(0, 1), role="Most of the panel the labels may claim"),
    Param("min_plot_frac", float, 0.22, unit="[0-1] panel fraction", range=(0, 1), role="Least of the panel kept for the dots"),
    # [Colourbar]
    Param("show_colorbar", bool, True, role="Show the colourbar"),
    Param("cax", object, None, role="An existing axes to draw the colourbar in (set by the script, not in YAML)"),
    Param("colorbar_loc", str, CODE_DEFAULT, role="Side of the colourbar (matplotlib location)"),
    Param("colorbar_orientation", ("vertical", "horizontal"), "vertical", role="Colourbar orientation when cax is given"),
    Param("colorbar_shrink", float, 0.6, unit="fraction of axes height", range=(0, 1), role="Length of the side colourbar"),
    Param("colorbar_margin", float, CODE_DEFAULT, unit="[0-1] panel fraction",
          role="Side margin reserved for the colourbar (default 0.14, or 0.03 without one)"),
    Param("colorbar_top_right", bool, False, role="Small horizontal colourbar above the top-right corner instead of a side bar"),
    Param("colorbar_width_in", float, 3.0, unit="inches", role="Width of the top-right colourbar"),
    Param("colorbar_height_in", float, 0.16, unit="inches", role="Height of the top-right colourbar"),
    Param("colorbar_gap_in", float, 0.25, unit="inches", role="Gap between panel top and the top-right colourbar"),
    Param("colorbar_right_pad_in", float, 0.1, unit="inches", role="Inset of the top-right colourbar from the right edge"),
    Param("colorbar_label", str, "sign(dir) x -log10(FDR)", role="Colourbar title"),
    Param("colorbar_label_fontsize", float, CODE_DEFAULT, unit="pt", role="Colourbar title size (default from axes_label_size)"),
    Param("colorbar_tick_fontsize", float, CODE_DEFAULT, unit="pt", role="Colourbar tick size (default from tick_label_size)"),
    # [Dot-size legend]
    Param("show_size_legend", bool, True, role="Show the dot-size legend"),
    Param("size_legend_title", str, "Gene Ratio", role="Dot-size legend title"),
    Param("size_legend_values", list, None, unit="size_col units", role="Sizes shown in the legend (default: from the data)"),
    Param("size_legend_loc", str, "best", role="Legend anchor inside the axes (matplotlib loc)"),
    Param("size_legend_outside", bool, False, role="Place the legend outside, left of the dots, anchored at size_legend_bbox"),
    Param("size_legend_bbox", list, (0.0, 0.02), unit="axes fraction (x, y)", role="Anchor of the outside legend"),
    Param("size_legend_offset_pts", float, -62, unit="pt", role="Horizontal shift of the outside legend",
          tune="more negative moves it further left of the dots"),
    Param("size_legend_below", bool, False, role="Place the legend centred below the axes"),
    Param("size_legend_below_offset_pts", float, 30, unit="pt", role="Gap between the axes and the legend below it"),
    Param("size_legend_ncol", int, CODE_DEFAULT, unit="columns", role="Columns of the legend below (default: all sizes in one row)"),
])


@uses_schema(SCHEMA)
def render_cross_condition_dotplot(ax, df, params):
    """Draw a cross-condition enrichment dot plot onto ``ax``.

    params: term_col('GO Term'), condition_col('Condition'),
            value_col('Signed -log10(FDR)'), size_col('Gene Ratio'),
            condition_order(list; default = first-seen order),
            condition_rename_map (dict, raw Condition value -> display
            label for the x-tick text only; matching/ordering still uses
            the raw values),
            term_order(list; default = first-seen order in the data),
            cmap('RdBu_r'), color_min/color_max (symmetric around 0 by
            default, auto from data), gray_threshold (float, default None --
            when set, dots with value below this are drawn in gray_color
            instead of the colormap, and the colorbar's vmin is pinned to
            this threshold so the colormap's full dynamic range is spent on
            values that cleared it, e.g. -log10(0.05) for a padj/P-value
            significance cutoff), gray_color (default '#d0d0d0' -- pass
            '#ffffff' for a hollow-dot look: near-invisible fill against a
            white axes background, but the dot_edgecolor ring stays visible
            so "computed, not significant" stays distinguishable from a
            true absence -- no row at all for that term/condition),
            dot_size_min, dot_size_scale,
            dot_edgecolor, dot_edgewidth, dot_alpha, show_size_legend,
            size_legend_values, size_legend_loc, show_colorbar,
            colorbar_loc, colorbar_shrink, colorbar_top_right (bool, default
            False -- draw a small horizontal colorbar anchored above the
            panel's top-right corner instead of a full-height side bar;
            sized via colorbar_width_in/colorbar_height_in/colorbar_gap_in/
            colorbar_right_pad_in, all in inches, plus colorbar_label_fontsize/
            colorbar_tick_fontsize -- pair with a small colorbar_margin so the
            side margin it used to occupy isn't reserved for nothing),
            ylabel_wrap_width, term_fontsize
            (defaults to tick_label_size), label_margin_pad (extra fraction
            beyond the measured minimum reserved for term labels, default
            1.2 -- raise to shrink the plot area further), label_margin_cap
            (max fraction of panel width the label margin may claim,
            default 0.82), size_legend_outside (bool, default False --
            place the dot-size legend below-left of the axes instead of
            inside it), size_legend_bbox ((x, y) in ax.transAxes coords for
            the outside legend's anchor, default (0.0, -0.02)),
            xtick_rotation, grid, labels_title, axes_label_size,
            tick_label_size, title_size
    """
    import textwrap

    title_sz = params.get("title_size", 13)
    a_sz = params.get("axes_label_size", 11)
    t_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty:
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes)
        return None

    term_col = params.get("term_col", "GO Term")
    cond_col = params.get("condition_col", "Condition")
    value_col = params.get("value_col", "Signed -log10(FDR)")
    size_col = params.get("size_col", "Gene Ratio")

    strip_pattern = params.get("term_strip_pattern")
    if strip_pattern:
        import re
        df[term_col] = df[term_col].astype(str).str.replace(strip_pattern, "", regex=True)

    # Optionally cut down to the strongest N terms per direction (e.g. top
    # 10 up + top 10 down) -- a full cross-condition set can be too dense to
    # read as a dot plot even when a heatmap of the same set is legible, so
    # this is independent of any filtering already applied upstream.
    direction_col = params.get("direction_col", "Direction")
    top_n_up = params.get("top_n_up")
    top_n_down = params.get("top_n_down")
    if (top_n_up is not None or top_n_down is not None) and direction_col in df.columns:
        strength = df.groupby(term_col)[value_col].apply(lambda s: s.abs().max())
        direction = df.groupby(term_col)[direction_col].first()
        keep = []
        if top_n_up is not None:
            keep.extend(strength[direction == "UP"].sort_values(ascending=False)
                        .head(int(top_n_up)).index)
        if top_n_down is not None:
            keep.extend(strength[direction == "DOWN"].sort_values(ascending=False)
                        .head(int(top_n_down)).index)
        df = df[df[term_col].isin(keep)]

    condition_order = params.get("condition_order") or list(dict.fromkeys(df[cond_col]))
    # An externally supplied term_order (e.g. a sibling heatmap's clustered
    # row order) is intersected with what's left after top-N filtering,
    # preserving that order, rather than falling back to first-seen order.
    term_order_param = params.get("term_order")
    if term_order_param:
        present = set(df[term_col])
        term_order = [t for t in term_order_param if t in present]
    else:
        term_order = list(dict.fromkeys(df[term_col]))
    cond_pos = {c: i for i, c in enumerate(condition_order)}
    term_pos = {t: i for i, t in enumerate(term_order)}

    df = df[df[term_col].isin(term_pos) & df[cond_col].isin(cond_pos)]
    x = df[cond_col].map(cond_pos)
    y = df[term_col].map(term_pos)
    values = pd.to_numeric(df[value_col], errors="coerce")

    cmap = params.get("cmap", "RdBu_r")
    if params.get("color_auto", True):
        absmax = float(np.nanmax(np.abs(values.to_numpy()))) if len(values) else 1.0
        vmin, vmax = -absmax, absmax
    else:
        vmin = float(params.get("color_min", -10.0))
        vmax = float(params.get("color_max", 10.0))
    # Diverging colormap, blue=down (negative) / red=up (positive); RdBu_r
    # already puts red at the high end, so no reversal needed here.

    # gray_threshold pins vmin to the significance cutoff itself, so a value
    # that just cleared it and one that barely missed it don't get rendered
    # as near-identical dark colormap colors -- the miss is instead an
    # unambiguous flat gray, and the colormap's full range is spent only on
    # values that actually cleared the bar.
    gray_threshold = params.get("gray_threshold")
    if gray_threshold is not None:
        gray_threshold = float(gray_threshold)
        vmin = gray_threshold

    dot_min = float(params.get("dot_size_min", 20.0))
    dot_scale = float(params.get("dot_size_scale", 800.0))
    ratio = pd.to_numeric(df[size_col], errors="coerce").fillna(0.0)
    sizes = dot_min + ratio * dot_scale

    if gray_threshold is not None:
        is_gray = values < gray_threshold
        sig_mask = ~is_gray
        if is_gray.any():
            ax.scatter(x[is_gray], y[is_gray], s=sizes[is_gray],
                      c=params.get("gray_color", "#d0d0d0"),
                      alpha=float(params.get("dot_alpha", 0.9)),
                      edgecolors=params.get("dot_edgecolor", "#555555"),
                      linewidths=float(params.get("dot_edgewidth", 0.5)), zorder=2)
    else:
        sig_mask = pd.Series(True, index=df.index)

    sc = ax.scatter(x[sig_mask], y[sig_mask], c=values[sig_mask], s=sizes[sig_mask],
                    cmap=cmap, vmin=vmin, vmax=vmax,
                    alpha=float(params.get("dot_alpha", 0.9)),
                    edgecolors=params.get("dot_edgecolor", "#555555"),
                    linewidths=float(params.get("dot_edgewidth", 0.5)), zorder=3)

    ax.set_xlim(-0.5, len(condition_order) - 0.5)
    ax.set_ylim(-0.5, len(term_order) - 0.5)
    ax.invert_yaxis()
    # Publication-facing renaming of the raw Condition values (e.g.
    # "D1_vs_Control" -> "Acute D1") happens only at display time, via
    # config -- condition_order/matching above still uses the raw values,
    # same principle as sample_rename_map elsewhere in this codebase.
    condition_rename_map = params.get("condition_rename_map", {})
    condition_labels = [condition_rename_map.get(c, c) for c in condition_order]
    ax.set_xticks(range(len(condition_order)))
    # xtick_fontsize: optional override -- long category names at the shared
    # tick_label_size can collide with their rotated neighbors on narrow
    # panels, so callers may size x ticks independently of y ticks.
    # xtick_rotation_mode: pass "anchor" (with ha=right/va=top) for multiline
    # rotated labels -- without it matplotlib rotates the whole multiline
    # block around its post-alignment bbox, swinging the lines into each
    # other and into the neighboring labels.
    xt_kwargs = dict(fontsize=params.get("xtick_fontsize", t_sz),
                     rotation=float(params.get("xtick_rotation", 45)),
                     ha=params.get("xtick_ha", "right"))
    if params.get("xtick_rotation_mode"):
        xt_kwargs["rotation_mode"] = params["xtick_rotation_mode"]
        xt_kwargs["va"] = "top"
    ax.set_xticklabels(condition_labels, **xt_kwargs)
    term_fs = params.get("term_fontsize", t_sz)
    wrap_w = int(params.get("ylabel_wrap_width", 40))
    y_labels = [textwrap.fill(str(t), width=wrap_w, break_long_words=False) for t in term_order]
    ax.set_yticks(range(len(term_order)))
    ax.set_yticklabels(y_labels, fontsize=term_fs)
    labels_on_right = params.get("term_label_side", "right") == "right"
    if labels_on_right:
        ax.yaxis.tick_right()
    if params.get("grid", True):
        ax.grid(True, alpha=0.25, linestyle="-", zorder=0)
    ax.set_axisbelow(True)

    # Renderer-independent margin, sized from the actually-rendered term
    # -label extent (same measured-extent pattern as go_cluster_dot.py/
    # go_bar.py/go_dot.py/volcano.py this session), applied BEFORE the
    # colorbar below: fig.colorbar(..., ax=ax) steals space from ax's
    # position at call time, so repositioning ax after creating it would
    # leave the colorbar behind. When labels moved to the right (tick_right
    # above), the colorbar defaults to the LEFT instead of competing with
    # them for the same side -- two independent margins, one per side, is
    # far simpler than trying to fit both a colorbar and label text into
    # one shared margin.
    # Renderer-independent margin, sized from the actually-rendered term
    # -label extent (same measured-extent pattern as go_cluster_dot.py/
    # go_bar.py/go_dot.py/volcano.py this session), applied BEFORE the
    # colorbar below: fig.colorbar(..., ax=ax) steals space from ax's
    # position at call time, so repositioning ax after creating it would
    # leave the colorbar behind. When labels moved to the right (tick_right
    # above), the colorbar defaults to the LEFT instead of competing with
    # them for the same side -- two independent margins, one per side, is
    # far simpler than trying to fit both a colorbar and label text into
    # one shared margin.
    root_fig = getattr(ax.figure, "figure", ax.figure)
    do_reposition = params.get("reposition_axes", True)
    default_colorbar_loc = "left" if labels_on_right else "right"

    if do_reposition:
        renderer = root_fig.canvas.get_renderer()
        label_px = max((t.get_window_extent(renderer=renderer).width
                         for t in ax.get_yticklabels()), default=0)
        pos = ax.get_position()
        panel_px = pos.width * ax.figure.bbox.width
        pad = float(params.get("label_margin_pad", 1.2))
        needed_frac = (label_px + 0.12 * root_fig.dpi) / panel_px * pad if panel_px > 0 else 0.3
        label_margin = min(float(params.get("label_margin_cap", 0.82)), max(0.12, needed_frac))
        min_plot_frac = float(params.get("min_plot_frac", 0.22))
        if labels_on_right:
            left_margin = float(params.get("colorbar_margin", 0.14 if params.get("show_colorbar", True) else 0.03))
            label_margin = min(label_margin, 1 - left_margin - min_plot_frac)
            ax.set_position([left_margin, pos.y0, (1 - label_margin) - left_margin, pos.height])
            default_colorbar_loc = "left"
        else:
            label_margin = min(label_margin, 0.97 - min_plot_frac)
            ax.set_position([label_margin, pos.y0, 0.97 - label_margin, pos.height])
            default_colorbar_loc = "right"

    if params.get("show_colorbar", True):
        custom_cax = params.get("cax")
        if custom_cax is not None:
            cbar_orientation = params.get("colorbar_orientation", "vertical")
            cbar = root_fig.colorbar(sc, cax=custom_cax, orientation=cbar_orientation)
            cbar.set_label(text_param(params, "colorbar_label", "sign(dir) x -log10(FDR)"),
                           fontsize=float(params.get("colorbar_label_fontsize", a_sz)))
            cbar.ax.tick_params(labelsize=float(params.get("colorbar_tick_fontsize", t_sz)))
        elif params.get("colorbar_top_right", False):
            # Small horizontal colorbar anchored above the panel's top-right
            # corner instead of a full-height bar reserved in a wide side
            # margin -- sized in absolute inches (not axes-fraction, which
            # would be wildly sensitive on a very tall multi-hundred-row
            # panel) and placed via a dedicated cax so its size/position
            # are exact regardless of how tall ax itself is.
            fig_w_in, fig_h_in = root_fig.get_size_inches()
            final_pos = ax.get_position()
            cb_w_frac = float(params.get("colorbar_width_in", 3.0)) / fig_w_in
            cb_h_frac = float(params.get("colorbar_height_in", 0.16)) / fig_h_in
            gap_frac = float(params.get("colorbar_gap_in", 0.25)) / fig_h_in
            right_pad_frac = float(params.get("colorbar_right_pad_in", 0.1)) / fig_w_in
            x1 = 1.0 - right_pad_frac
            x0 = x1 - cb_w_frac
            y0 = final_pos.y1 + gap_frac
            cax = root_fig.add_axes([x0, y0, cb_w_frac, cb_h_frac])
            cbar = root_fig.colorbar(sc, cax=cax, orientation="horizontal")
            cbar.set_label(text_param(params, "colorbar_label", "sign(dir) x -log10(FDR)"),
                           fontsize=float(params.get("colorbar_label_fontsize", a_sz * 0.8)))
            cbar.ax.tick_params(labelsize=float(params.get("colorbar_tick_fontsize", t_sz * 0.8)))
            cbar.ax.xaxis.set_label_position("top")
            cbar.ax.xaxis.set_ticks_position("top")
        else:
            cbar = ax.figure.colorbar(sc, ax=ax, location=params.get("colorbar_loc", default_colorbar_loc),
                                      shrink=float(params.get("colorbar_shrink", 0.6)), pad=0.02,
                                      use_gridspec=False)
            cbar.set_label(text_param(params, "colorbar_label", "sign(dir) x -log10(FDR)"),
                           fontsize=a_sz)
            cbar.ax.tick_params(labelsize=t_sz)

    if params.get("show_size_legend", True):
        custom_values = params.get("size_legend_values")
        if custom_values:
            reps = list(custom_values)
        else:
            max_v = float(ratio.max()) if len(ratio) else 0.1
            reps = sorted({round(max_v / 3, 2), round(max_v * 2 / 3, 2), round(max_v, 2)})
        handles = [ax.scatter([], [], s=dot_min + v * dot_scale, c="#aaaaaa",
                              edgecolors=params.get("dot_edgecolor", "#555555"),
                              linewidths=float(params.get("dot_edgewidth", 0.5)),
                              label=f"{v:g}")
                   for v in reps]
        legend_kwargs = dict(handles=handles, title=params.get("size_legend_title", "Gene Ratio"),
                             fontsize=t_sz, title_fontsize=t_sz, framealpha=0.9)
        if params.get("size_legend_outside", False):
            # A plain axes-fraction bbox_to_anchor scales with the axes'
            # own size, which broke badly for "below the axes" placement
            # (panel b's tall axes turned the same fraction into a much
            # bigger absolute drop than panel c's short one, pushing the
            # legend behind panel c's later-drawn background). Placing it
            # to the LEFT instead -- in the reserved colorbar-margin column,
            # which has near-constant absolute width regardless of axes
            # height -- sidesteps that: offset_copy shifts by a FIXED
            # number of points from the axes' left edge, landing in that
            # margin's blank area below the colorbar; the y anchor stays a
            # small axes-fraction since that's a within-plot position, not
            # an extrapolated one, so it doesn't have the same scaling bug.
            # loc must be a "right" corner (box's right edge AT the anchor,
            # extending left/up from there) -- a "left" corner anchors the
            # box's own left edge instead, so the box's right portion still
            # extended back across x=0 into the plotted dots regardless of
            # how far left the anchor point itself was pushed.
            from matplotlib.transforms import offset_copy
            bx, by = params.get("size_legend_bbox", (0.0, 0.02))
            offset_pts = float(params.get("size_legend_offset_pts", -62))
            legend_transform = offset_copy(ax.transAxes, fig=ax.figure,
                                           x=offset_pts, y=0, units="points")
            legend_kwargs.update(loc="lower right", bbox_to_anchor=(bx, by),
                                 bbox_transform=legend_transform)
        elif params.get("size_legend_below", False):
            # One horizontal row centred under the axes, a FIXED number of
            # points below its bottom edge (clearing the x tick labels) --
            # for dense panels where every in-plot corner holds dots. Points,
            # not an axes fraction, so the gap doesn't scale with axes height.
            from matplotlib.transforms import offset_copy
            offset_pts = float(params.get("size_legend_below_offset_pts", 30))
            legend_transform = offset_copy(ax.transAxes, fig=ax.figure,
                                           x=0, y=-offset_pts, units="points")
            legend_kwargs.update(loc="upper center", bbox_to_anchor=(0.5, 0.0),
                                 bbox_transform=legend_transform,
                                 ncol=int(params.get("size_legend_ncol", len(reps) + 1)))
        else:
            legend_kwargs["loc"] = params.get("size_legend_loc", "best")
        ax.legend(**legend_kwargs)

    title = text_param(params, "labels_title", "Cross-Condition GO Dot Plot")
    ax.set_title(title, fontsize=title_sz, fontweight="bold")

    return df
