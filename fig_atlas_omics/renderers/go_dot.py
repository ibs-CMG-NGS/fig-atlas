"""GO/KEGG enrichment dot plot renderer, ported from go_dot_plot_bundle.

Draws onto a Matplotlib Figure or SubFigure. All visual attributes come from
``params``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fig_atlas.params import text_param


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("go_dot", params=[
    Param("top_n", int, 20, unit="terms", range=(1, None), role="Terms shown (highest on the x measure)"),
    Param("x_axis", ("Gene Ratio", "Fold Enrichment"), "Gene Ratio", role="Measure on the x axis"),
    Param("size_mode", ("Gene Count", "Gene Ratio", "Fold Enrichment"), "Gene Count", role="Measure mapped to dot size"),
    Param("palette", "cmap", "YlOrRd_r", role="Colormap for the adjusted P"),
    Param("color_min", float, 0.0, unit="adjusted P", role="Lower end of the colour scale"),
    Param("color_max", float, 0.05, unit="adjusted P", role="Upper end of the colour scale"),
    Param("ylabel_wrap_width", int, 26, unit="characters", range=(1, None), role="Wrap term labels at this width"),
    Param("xlabel_text", str, CODE_DEFAULT, role="x-axis title (default: the x_axis name)"),
    Param("title_size", float, 13, unit="pt", role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", role="Tick label font size"),
])


def _gene_ratio(df):
    if 'gene_ratio' in df.columns:
        def parse(v):
            try:
                if pd.isna(v):
                    return 0.0
                if isinstance(v, (int, float)):
                    return float(v)
                p = str(v).split('/')
                if len(p) == 2:
                    d = float(p[1])
                    return float(p[0]) / d if d > 0 else 0.0
                return 0.0
            except Exception:
                return 0.0
        return df['gene_ratio'].apply(parse)
    if 'gene_count' in df.columns:
        m = df['gene_count'].max()
        if m > 0:
            return df['gene_count'] / m
    return pd.Series(0.5, index=df.index)


def _wrap_label(text, width):
    """Wrap ``text`` onto multiple lines at word boundaries near ``width`` chars.

    Falls back to a hard split when a single word is longer than ``width``.
    width <= 0 disables wrapping.
    """
    import textwrap
    text = str(text)
    if width and width > 0 and len(text) > width:
        wrapped = textwrap.fill(text, width=width, break_long_words=True)
        return wrapped
    return text


@uses_schema(SCHEMA)
def render_go_dot(fig, df, params):
    """Draw a GO/KEGG enrichment dot plot onto ``fig`` (Figure or SubFigure).

    params: top_n, x_axis('Gene Ratio'|'Fold Enrichment'),
            size_mode('Gene Count'|'Gene Ratio'|'Fold Enrichment'),
            palette, color_min, color_max, xlabel_text
    """
    _SIZE_NORM = {
        "Gene Count":      (100.0, [(10, "10 genes"), (30, "30 genes"), (80, "≥80 genes")]),
        "Gene Ratio":      (0.40,  [(0.03, "0.03"),   (0.12, "0.12"),  (0.35, "≥0.35")]),
        "Fold Enrichment": (20.0,  [(2.0,  "2×"),     (5.0,  "5×"),    (15.0, "≥15×")]),
    }
    _S_MIN, _S_MAX = 50, 500

    # Honor the harmonized global style keys instead of hardcoding sizes.
    a_sz = params.get('axes_label_size', 11)
    title_sz = params.get('title_size', 13)
    tick_sz = params.get('tick_label_size', 8)

    df = df.copy() if df is not None else pd.DataFrame()
    ax = fig.add_subplot(111)
    if len(df) == 0:
        ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return None

    required = ['description']
    if 'fdr' in df.columns:
        required.append('fdr')
    if 'gene_count' in df.columns:
        required.append('gene_count')
    df = df.dropna(subset=required)
    if len(df) == 0:
        ax.text(0.5, 0.5, 'No valid data to display\n(NaN values removed)',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return None

    df['_gene_ratio'] = _gene_ratio(df)

    x_axis_type = params.get('x_axis', 'Gene Ratio')
    if x_axis_type == "Fold Enrichment" and 'fold_enrichment' in df.columns:
        df['_x_val'] = pd.to_numeric(df['fold_enrichment'], errors='coerce').fillna(0)
    else:
        df['_x_val'] = df['_gene_ratio']

    df = df.sort_values('_x_val', ascending=False).head(int(params.get('top_n', 20)))
    df = df.sort_values('_x_val', ascending=True)

    wrap_w = int(params.get('ylabel_wrap_width', 26))
    x_data = df['_x_val']
    raw_labels = [str(l)[:60] + '...' if len(str(l)) > 60 else str(l)
                  for l in (df['description'].to_list() if 'description' in df.columns
                            else [f"Term {i+1}" for i in range(len(df))])]
    y_labels = [_wrap_label(l, wrap_w) for l in raw_labels]
    y_data = np.arange(len(y_labels))

    # Denser plots shrink tick labels a step at a time, relative to tick_label_size.
    n = len(df)
    step = 0 if n <= 10 else 1 if n <= 20 else 2 if n <= 30 else 3
    yfs = max(4, tick_sz + 1 - step)
    ax.set_yticks(y_data)
    ax.set_yticklabels(y_labels, fontsize=yfs)

    # Renderer-independent left margin, applied BEFORE the colorbar/legend
    # are added below: fig.colorbar(scatter, ax=ax) steals space from ax's
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
    # real glyph widths overflows straight into the neighboring panel. The
    # renderer only lives on the root figure's canvas, but the pixel width to
    # size the margin against must be THIS axes' own parent SubFigure's bbox
    # (fig), not the root's (a SubFigure only occupies a fraction of the root
    # canvas).
    root_fig = getattr(fig, "figure", fig)
    renderer = root_fig.canvas.get_renderer()
    label_px = max((t.get_window_extent(renderer=renderer).width
                     for t in ax.get_yticklabels()), default=0)
    pos = ax.get_position()
    panel_px = pos.width * fig.bbox.width
    needed_frac = (label_px + 0.12 * root_fig.dpi) / panel_px if panel_px > 0 else 0.3
    left = min(0.75, max(0.12, needed_frac))
    # Right edge close to this SubFigure's own full width (not the old
    # hardcoded 0.85) -- this subfigure already has its own gap from its
    # sibling panels via the calling script's gridspec wspace, so reserving
    # extra padding here on top of that only starves the dot-plot area. The
    # colorbar call below shrinks ax again from whatever right edge it
    # finds, so it's safe to start wide.
    ax.set_position([left, pos.y0, 0.97 - left, pos.height])

    if 'fdr' in df.columns:
        colors = df['fdr']
        cmap = params.get('palette', 'YlOrRd_r')
        color_label = "FDR"
        vmin = params.get('color_min', 0.0)
        vmax = params.get('color_max', 0.05)
    else:
        colors, cmap, color_label, vmin, vmax = 'steelblue', None, None, None, None

    size_mode = params.get('size_mode', 'Gene Count')
    if size_mode == "Gene Count" and 'gene_count' in df.columns:
        raw = pd.to_numeric(df['gene_count'], errors='coerce').fillna(0)
    elif size_mode == "Gene Ratio":
        raw = pd.to_numeric(df['_gene_ratio'], errors='coerce').fillna(0)
    elif size_mode == "Fold Enrichment" and 'fold_enrichment' in df.columns:
        raw = pd.to_numeric(df['fold_enrichment'], errors='coerce').fillna(0)
    else:
        raw = None

    if raw is not None and size_mode in _SIZE_NORM:
        norm_max, size_rep = _SIZE_NORM[size_mode]
        sizes = _S_MIN + np.clip(raw / norm_max, 0, 1) * (_S_MAX - _S_MIN)
    else:
        norm_max, size_rep = None, None
        sizes = pd.Series(100, index=df.index)

    scatter = ax.scatter(x_data, y_data, c=colors, s=sizes, cmap=cmap, alpha=0.7,
                         edgecolors='black', linewidth=0.5, vmin=vmin, vmax=vmax)

    # Renderer-independent margins. Figure exposes get_size_inches; a SubFigure
    # does not, so fall back to its pixel bbox (already in points at fig dpi).
    max_s = float(sizes.max() if hasattr(sizes, 'max') else sizes)
    max_r_pt = np.sqrt(max_s) / 2
    try:
        fig_w_pt = fig.get_size_inches()[0] * fig.dpi
        fig_h_pt = fig.get_size_inches()[1] * fig.dpi
    except AttributeError:
        fig_w_pt = fig.bbox.width
        fig_h_pt = fig.bbox.height
    ax.margins(x=max_r_pt / (fig_w_pt * 0.55) + 0.05,
               y=max_r_pt / (fig_h_pt * 0.80) + 0.05)

    ax.set_xlabel(text_param(params, 'xlabel_text', x_axis_type), fontsize=a_sz, fontweight='bold')
    ax.set_ylabel("GO/KEGG Terms", fontsize=a_sz, fontweight='bold')
    ax.set_title("GO/KEGG Enrichment Dot Plot", fontsize=title_sz,
                 fontweight='bold')
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    if cmap is not None and color_label is not None:
        # use_gridspec=False: the default (True) recomputes ax's position
        # from its ORIGINAL subplotspec, silently discarding the manual
        # ax.set_position() margin fix above. use_gridspec=False shrinks ax
        # from its actual CURRENT position instead.
        cbar = fig.colorbar(scatter, ax=ax, shrink=0.5, pad=0.02, anchor=(0, 1.0),
                            use_gridspec=False)
        cbar.set_label(color_label, fontsize=tick_sz + 2)

    if size_rep is not None and norm_max is not None:
        from matplotlib.lines import Line2D
        lfs = tick_sz

        def _ms(val):
            s = _S_MIN + np.clip(val / norm_max, 0, 1) * (_S_MAX - _S_MIN)
            return 2.0 * np.sqrt(s / np.pi)

        max_diam = max(_ms(v) for v, _ in size_rep)
        elements = [Line2D([0], [0], marker='o', color='none', markerfacecolor='#808080',
                           markeredgecolor='#333333', markeredgewidth=0.8,
                           markersize=_ms(v), label=lbl) for v, lbl in size_rep]
        leg = ax.legend(handles=elements, title=size_mode, loc='upper left', fontsize=lfs,
                        title_fontsize=lfs, labelspacing=max_diam / lfs + 0.5,
                        handlelength=0, handletextpad=1.2, borderpad=0.9, framealpha=0.95,
                        edgecolor='#bbbbbb', fancybox=False, bbox_to_anchor=(1.02, 0.20))
        leg.get_title().set_fontweight('bold')

    return df, sizes
