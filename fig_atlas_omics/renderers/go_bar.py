"""GO/KEGG enrichment bar chart renderer, ported from go_kegg_*_bar_chart_bundle.

Draws onto a Matplotlib Axes. All visual attributes come from ``params``.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from fig_atlas.params import text_param


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("go_bar", params=[
    # [Terms]
    Param("top_n", int, 15, unit="terms", range=(1, None), role="Terms shown after sorting"),
    Param("sort_by", ("FDR (ascending)", "Gene Count (descending)", "Alphabetical"), "FDR (ascending)",
          role="Order of the terms"),
    Param("x_axis", ("-log10(FDR)", "Gene Ratio", "Fold Enrichment"), "-log10(FDR)", role="Bar length metric"),
    Param("horizontal", bool, True, role="Horizontal bars (terms on the y axis)"),
    Param("label_strip_pattern", str, None, role="Regex removed from term names (e.g. GO IDs)"),
    Param("ylabel_wrap_width", int, 70, unit="characters", range=(1, None), role="Wrap term names at this width"),
    # [Bars]
    Param("bar_color", "color", "#4C72B0", unit="hex color", role="Bar fill colour"),
    Param("bar_edgecolor", "color", "black", unit="color", role="Bar outline colour"),
    Param("bar_edgewidth", float, 0.5, unit="pt", range=(0, None), role="Bar outline width"),
    # [Threshold line]
    Param("show_threshold_line", bool, False, role="Draw the FDR cutoff (only with x_axis -log10(FDR))"),
    Param("threshold_fdr", float, 0.05, unit="FDR", range=(0, 1), role="FDR of the cutoff line"),
    Param("threshold_line_color", "color", "black", unit="color", role="Cutoff line colour"),
    Param("threshold_line_style", str, "--", role="Cutoff line style (matplotlib linestyle)"),
    Param("threshold_line_width", float, 1.0, unit="pt", range=(0, None), role="Cutoff line width"),
    Param("threshold_line_alpha", float, 0.6, unit="alpha [0-1]", range=(0, 1), role="Cutoff line opacity"),
    # [Grid]
    Param("grid", bool, True, role="Draw grid lines along the value axis"),
    Param("grid_style", str, "--", role="Grid line style (matplotlib linestyle)"),
    Param("grid_alpha", float, 0.3, unit="alpha [0-1]", range=(0, 1), role="Grid line opacity"),
    # [Labels]
    Param("labels_title", str, "GO/KEGG Enrichment Bar Chart", role="Panel title"),
    Param("xlabel_text", str, CODE_DEFAULT, role="Value axis title (default: the x_axis name)"),
    Param("ylabel_text", str, "GO/KEGG Terms", role="Term axis title"),
    Param("xtick_rotation", float, 45, unit="degrees", role="Tick label rotation of the category axis in vertical mode"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_go_bar(ax, df, params):
    """Draw a GO/KEGG enrichment bar chart onto ``ax``.

    params: top_n, x_axis('-log10(FDR)'|'Gene Ratio'|'Fold Enrichment'),
            sort_by('FDR (ascending)'|'Gene Count (descending)'|'Alphabetical'),
            bar_color(hex), bar_edgecolor, bar_edgewidth, horizontal(bool),
            xlabel_text, ylabel_text, labels_title, axes_label_size,
            tick_label_size, title_size, xtick_rotation (vertical mode only),
            grid(bool), grid_alpha, grid_style,
            show_threshold_line (bool; only drawn when x_axis is '-log10(FDR)'),
            threshold_fdr (FDR cutoff the line marks, default 0.05),
            threshold_line_color, threshold_line_style, threshold_line_width,
            threshold_line_alpha,
            label_strip_pattern (regex removed from each term label before
            wrapping/truncation, e.g. to drop a KEGG " - <Organism> (<common
            name>)" suffix; default None leaves labels untouched)
    """
    a_sz = params.get("axes_label_size", 11)
    title_sz = params.get("title_size", 13)
    tick_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if len(df) == 0:
        ax.text(0.5, 0.5, "No data to display\nAdjust filters",
                ha="center", va="center", fontsize=title_sz, transform=ax.transAxes)
        return None

    required = ["description"]
    if "fdr" in df.columns:
        required.append("fdr")
    if "gene_count" in df.columns:
        required.append("gene_count")
    df = df.dropna(subset=required)
    if len(df) == 0:
        ax.text(0.5, 0.5, "No valid data to display\n(NaN values removed)",
                ha="center", va="center", fontsize=title_sz, transform=ax.transAxes)
        return None

    sort_by = params.get("sort_by", "FDR (ascending)")
    if sort_by == "FDR (ascending)" and "fdr" in df.columns:
        df = df.sort_values("fdr", ascending=True)
    elif sort_by == "Gene Count (descending)" and "gene_count" in df.columns:
        df = df.sort_values("gene_count", ascending=False)
    elif sort_by == "Alphabetical" and "description" in df.columns:
        df = df.sort_values("description", ascending=True)

    df = df.head(int(params.get("top_n", 15)))

    x_axis_type = params.get("x_axis", "-log10(FDR)")
    if x_axis_type == "-log10(FDR)":
        x_data = (-np.log10(pd.to_numeric(df["fdr"], errors="coerce").replace(0, 1e-300))
                  if "fdr" in df.columns else pd.Series(1, index=df.index))
    elif x_axis_type == "Gene Ratio":
        if "gene_ratio" in df.columns:
            def _parse(r):
                try:
                    if pd.isna(r):
                        return 0.0
                    if isinstance(r, (int, float)):
                        return float(r)
                    p = str(r).split("/")
                    return float(p[0]) / float(p[1]) if len(p) == 2 and float(p[1]) > 0 else 0.0
                except Exception:
                    return 0.0
            x_data = df["gene_ratio"].apply(_parse)
        else:
            x_data = pd.Series(1, index=df.index)
    else:  # Fold Enrichment
        x_data = (pd.to_numeric(df["fold_enrichment"], errors="coerce").fillna(0)
                  if "fold_enrichment" in df.columns else pd.Series(1, index=df.index))

    wrap_w = int(params.get("ylabel_wrap_width", 70))
    strip_pattern = params.get("label_strip_pattern")
    raw_labels = (df["description"].to_list() if "description" in df.columns
                  else [f"Term {i + 1}" for i in range(len(df))])
    if strip_pattern:
        raw_labels = [re.sub(strip_pattern, "", str(l)) for l in raw_labels]
    import textwrap
    y_labels = [textwrap.fill(str(l), width=wrap_w, break_long_words=False)
                for l in raw_labels]
    y_pos = np.arange(len(y_labels))
    bar_color = params.get("bar_color", "#4C72B0")
    bar_edgecolor = params.get("bar_edgecolor", "black")
    bar_edgewidth = float(params.get("bar_edgewidth", 0.5))
    horizontal = bool(params.get("horizontal", True))
    xlabel_text = text_param(params, "xlabel_text", x_axis_type)
    ylabel_text = text_param(params, "ylabel_text", "GO/KEGG Terms")
    show_grid = params.get("grid", True)
    grid_alpha = float(params.get("grid_alpha", 0.3))
    grid_style = params.get("grid_style", "--")

    if horizontal:
        ax.barh(y_pos, x_data, color=bar_color, edgecolor=bar_edgecolor, linewidth=bar_edgewidth)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(y_labels, fontsize=tick_sz)
        ax.tick_params(axis="x", labelsize=tick_sz)
        ax.set_xlabel(xlabel_text, fontsize=a_sz, fontweight="bold")
        ax.set_ylabel(ylabel_text, fontsize=a_sz, fontweight="bold")
        ax.invert_yaxis()
        if show_grid:
            ax.grid(axis="x", alpha=grid_alpha, linestyle=grid_style)
        # NOTE: fig.subplots_adjust()/tight_layout() must NOT be called here --
        # on a SubFigure they don't confine themselves to it, they mutate the
        # ROOT figure's shared subplotpars, which corrupts any outer
        # multi-row gridspec built by the calling analysis script.
        # ax.set_position() only moves this axes within its own parent
        # SubFigure, so it's safe to use instead.
        #
        # Sized from the labels' actually-rendered extent (measured via the
        # Agg renderer), not a character-count heuristic: matplotlib doesn't
        # clip tick labels to the subfigure boundary, so any estimate that
        # undershoots real glyph widths overflows straight into the
        # neighboring panel. The renderer only lives on the root figure's
        # canvas, but the pixel width to size the margin against must be
        # THIS axes' own parent SubFigure's bbox (ax.figure), not the root's
        # (a SubFigure only occupies a fraction of the root canvas).
        root_fig = getattr(ax.figure, "figure", ax.figure)
        renderer = root_fig.canvas.get_renderer()
        label_px = max((t.get_window_extent(renderer=renderer).width
                         for t in ax.get_yticklabels()), default=0)
        pos = ax.get_position()
        panel_px = pos.width * ax.figure.bbox.width
        needed_frac = (label_px + 0.12 * root_fig.dpi) / panel_px if panel_px > 0 else 0.3
        left = min(0.78, max(0.12, needed_frac))
        # Right edge close to this SubFigure's own full width (not pos.x1's
        # stale default ~0.9): there's no colorbar here competing for space,
        # so the bars can use nearly the whole remaining width. Using a
        # fixed wide edge (rather than the data-dependent `left`) also keeps
        # box widths closer to each other across sibling panels whose labels
        # differ in length -- a title (~fixed width for a given string) only
        # looks proportioned against a box that isn't needlessly narrowed.
        ax.set_position([left, pos.y0, 0.98 - left, pos.height])
    else:
        ax.bar(y_pos, x_data, color=bar_color, edgecolor=bar_edgecolor, linewidth=bar_edgewidth)
        ax.set_xticks(y_pos)
        rotation = float(params.get("xtick_rotation", 45))
        ax.set_xticklabels(y_labels, rotation=rotation,
                           ha="right" if rotation else "center", fontsize=tick_sz)
        ax.tick_params(axis="y", labelsize=tick_sz)
        ax.set_ylabel(xlabel_text, fontsize=a_sz, fontweight="bold")
        ax.set_xlabel(ylabel_text, fontsize=a_sz, fontweight="bold")
        if show_grid:
            ax.grid(axis="y", alpha=grid_alpha, linestyle=grid_style)

    # FDR-cutoff reference line, in the same -log10(FDR) units as the x_axis
    # option above; only meaningful (and only drawn) when that's the active axis.
    if x_axis_type == "-log10(FDR)" and params.get("show_threshold_line", False):
        threshold_x = -np.log10(max(float(params.get("threshold_fdr", 0.05)), 1e-300))
        line_kw = dict(
            color=params.get("threshold_line_color", "black"),
            linestyle=params.get("threshold_line_style", "--"),
            linewidth=float(params.get("threshold_line_width", 1.0)),
            alpha=float(params.get("threshold_line_alpha", 0.6)),
        )
        if horizontal:
            ax.axvline(threshold_x, **line_kw)
        else:
            ax.axhline(threshold_x, **line_kw)

    title = text_param(params, "labels_title", "GO/KEGG Enrichment Bar Chart")
    ax.set_title(title, fontsize=title_sz, fontweight="bold")
    return df
