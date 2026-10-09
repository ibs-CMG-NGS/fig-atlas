"""Grouped bar + scatter renderer.

Draws a grouped vertical bar chart where each categorical x-tick carries one bar
per series (group). Bars show the group mean, error bars show SEM or SD, and the
individual replicate values are overlaid as jittered dots. When exactly two
groups are present, a significance star bracket sourced from a per-category
p-value column is drawn over each pair.

Every visual attribute is read from ``params`` via ``.get()`` so the same
renderer serves any wide replicate table without code changes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_DEFAULT_COLORS = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"]


from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("bar_scatter", params=[
    # [Data]
    Param("category_col", str, "symbol", role="Column holding the x categories"),
    Param("category_order", list, None, role="Category order, left to right (default: order in the data)"),
    Param("groups", list, [], role="Series per category: list of {label, color, columns} (replicate columns)"),
    Param("pvalue_col", str, None, role="Column with the per-category p-value for the two-group bracket"),
    # [Bars and error bars]
    Param("bar_width", float, 0.8, unit="x units (one category = 1)", range=(0, None),
          role="Total width of one category's bars"),
    Param("bar_edgecolor", "color", "none", unit="color", role="Bar outline colour"),
    Param("bar_edgewidth", float, 0.0, unit="pt", range=(0, None), role="Bar outline width"),
    Param("errorbar", ("sem", "sd"), "sem", role="Error bar: standard error or standard deviation"),
    Param("errorbar_width", float, 1.0, unit="pt", range=(0, None), role="Error bar and cap line width"),
    Param("capsize", float, 3.0, unit="pt", range=(0, None), role="Error bar cap length"),
    # [Replicate points]
    Param("show_points", bool, True, role="Overlay the replicate values as dots"),
    Param("point_color", "color", "#111111", unit="hex color", role="Replicate dot colour"),
    Param("point_edgecolor", "color", "white", unit="color", role="Replicate dot outline"),
    Param("point_edgewidth", float, 0.4, unit="pt", range=(0, None), role="Replicate dot outline width"),
    Param("point_size", float, 20, unit="pt^2 (marker area)", range=(0, None), role="Replicate dot size"),
    Param("point_jitter", float, 0.06, unit="x units", range=(0, None), role="Horizontal jitter of the dots"),
    Param("point_seed", int, 0, unit="random seed", role="Seed of the jitter (fixed for reproducible output)"),
    # [Significance bracket]
    Param("show_significance", bool, True, role="Draw the star bracket when there are exactly two groups"),
    Param("sig_thresholds", list, [[0.001, "***"], [0.01, "**"], [0.05, "*"]], unit="p-value",
          role="[threshold, symbol] pairs, ascending"),
    Param("sig_ns_display", str, "ns", role="Text for non-significant pairs (empty to hide)"),
    Param("sig_font_size", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Star size (default tick_label_size + 1)"),
    Param("sig_gap", float, 0.03, unit="fraction of the data top", range=(0, None), role="Gap between bars and bracket"),
    Param("sig_line_color", "color", "#333333", unit="hex color", role="Bracket line colour"),
    Param("sig_line_width", float, 1.0, unit="pt", range=(0, None), role="Bracket line width"),
    # [Axes]
    Param("y_min", float, 0, unit="data coords", role="Lower y limit"),
    Param("y_max", float, None, unit="data coords", role="Upper y limit (default: data top x y_headroom)"),
    Param("y_headroom", float, 1.28, unit="multiple of the data top", range=(1, None),
          role="Space above the bars for the brackets", tune="raise if stars touch the top"),
    Param("grid", bool, True, role="Draw horizontal grid lines"),
    Param("grid_alpha", float, 0.3, unit="alpha [0-1]", range=(0, 1), role="Grid line opacity"),
    Param("despine", bool, True, role="Hide the top and right spines"),
    Param("xtick_rotation", float, 0, unit="degrees", role="Category label rotation"),
    Param("xtick_mode", ("category", "group"), "category",
          role="x tick labels: one per category, or one per bar named by its group (e.g. a single two-group comparison)"),
    # [Legend]
    Param("show_legend", bool, True, role="Show the group legend"),
    Param("legend_loc", str, "upper right", role="Legend location (matplotlib loc string)"),
    Param("legend_ncol", int, 1, unit="columns", range=(1, None), role="Legend columns"),
    Param("legend_frameon", bool, False, role="Draw a frame around the legend"),
    Param("legend_fontsize", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Legend font size (default tick_label_size)"),
    # [Labels]
    Param("labels_title", str, None, role="Panel title"),
    Param("labels_xlabel", str, CODE_DEFAULT, role="x-axis title (default: category_col)"),
    Param("labels_ylabel", str, "Value", role="y-axis title"),
    Param("title_size", float, 12, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 10, unit="pt", range=(0, None), role="Axis title font size"),
    Param("axes_label_weight", str, "bold", role="Axis title weight (matplotlib: bold, normal, ...)"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


def _stars(p, thresholds, ns_display):
    """Map a p-value to a significance symbol using ascending (thr, symbol) pairs."""
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return ns_display
    for thr, sym in thresholds:
        if p <= thr:
            return sym
    return ns_display


@uses_schema(SCHEMA)
def render_bar_scatter(ax, df, params):
    """Render a grouped bar + scatter plot onto ``ax``.

    Args:
        ax:     Matplotlib Axes to draw on.
        df:     Wide DataFrame: one row per category, replicate values in columns.
        params: Visual parameters sourced from config / metadata YAML.
    """
    cat_col = params.get("category_col", "symbol")
    groups = params.get("groups", []) or []

    if cat_col not in df.columns or not groups:
        ax.text(0.5, 0.5,
                f"bar_scatter: need category_col ('{cat_col}') and groups",
                ha="center", va="center", fontsize=11, transform=ax.transAxes)
        return

    # Global style hooks (inherited from rcParams / config overrides).
    tick_sz = params.get("tick_label_size", 8)
    a_sz = params.get("axes_label_size", 10)
    title_sz = params.get("title_size", 12)

    df = df.copy()
    df[cat_col] = df[cat_col].astype(str)
    row_by_cat = {r[cat_col]: r for _, r in df.iterrows()}

    order = params.get("category_order")
    cats = [str(c) for c in order] if order else df[cat_col].tolist()
    cats = [c for c in cats if c in row_by_cat]

    n_groups = len(groups)
    total_w = float(params.get("bar_width", 0.8))
    bar_w = total_w / n_groups
    x = np.arange(len(cats), dtype=float)
    errtype = str(params.get("errorbar", "sem")).lower()

    # Per-category running top (bar+error, then raised by overlaid points) so the
    # significance brackets and y-headroom clear whatever is tallest.
    bar_centers = [[] for _ in cats]
    tops = [[] for _ in cats]

    for gi, g in enumerate(groups):
        cols = [c for c in g.get("columns", []) if c in df.columns]
        label = g.get("label", f"Group {gi + 1}")
        color = g.get("color", _DEFAULT_COLORS[gi % len(_DEFAULT_COLORS)])
        offset = (gi - (n_groups - 1) / 2.0) * bar_w
        centers = x + offset

        means, errs = [], []
        for ci, c in enumerate(cats):
            row = row_by_cat[c]
            vals = pd.to_numeric(pd.Series([row.get(col) for col in cols]),
                                 errors="coerce").dropna().to_numpy(dtype=float)
            m = float(vals.mean()) if vals.size else 0.0
            if vals.size > 1:
                sd = float(vals.std(ddof=1))
                e = sd / np.sqrt(vals.size) if errtype == "sem" else sd
            else:
                e = 0.0
            means.append(m)
            errs.append(e)
            bar_centers[ci].append(centers[ci])
            tops[ci].append(m + e)

        ax.bar(centers, means, width=bar_w * 0.9, color=color, label=label,
               yerr=errs, capsize=float(params.get("capsize", 3.0)),
               error_kw={"elinewidth": float(params.get("errorbar_width", 1.0)),
                         "capthick": float(params.get("errorbar_width", 1.0))},
               edgecolor=params.get("bar_edgecolor", "none"),
               linewidth=float(params.get("bar_edgewidth", 0.0)), zorder=2)

        if params.get("show_points", True):
            rng = np.random.default_rng(int(params.get("point_seed", 0)) + gi)
            jitter = float(params.get("point_jitter", 0.06))
            for ci, c in enumerate(cats):
                row = row_by_cat[c]
                vals = pd.to_numeric(pd.Series([row.get(col) for col in cols]),
                                     errors="coerce").dropna().to_numpy(dtype=float)
                if not vals.size:
                    continue
                xs = np.full(vals.size, centers[ci]) + rng.uniform(-jitter, jitter, vals.size)
                ax.scatter(xs, vals, s=float(params.get("point_size", 20)),
                           color=params.get("point_color", "#111111"),
                           edgecolors=params.get("point_edgecolor", "white"),
                           linewidths=float(params.get("point_edgewidth", 0.4)),
                           zorder=4)
                tops[ci][gi] = max(tops[ci][gi], float(vals.max()))

    data_top = max((max(t) for t in tops if t), default=1.0)

    # Significance brackets (only well-defined for a pairwise, 2-group comparison).
    pcol = params.get("pvalue_col")
    if (params.get("show_significance", True) and n_groups == 2
            and pcol and pcol in df.columns):
        thresholds = sorted((float(t), str(s))
                            for t, s in params.get("sig_thresholds",
                                                   [[0.001, "***"], [0.01, "**"], [0.05, "*"]]))
        ns_display = params.get("sig_ns_display", "ns")
        gap = float(params.get("sig_gap", 0.03)) * data_top
        line_c = params.get("sig_line_color", "#333333")
        line_w = float(params.get("sig_line_width", 1.0))
        sig_fs = params.get("sig_font_size", tick_sz + 1)
        for ci, c in enumerate(cats):
            row = row_by_cat[c]
            raw = row.get(pcol)
            p = None if pd.isna(raw) else float(raw)
            sym = _stars(p, thresholds, ns_display)
            if not sym:
                continue
            x1, x2 = bar_centers[ci][0], bar_centers[ci][1]
            y = max(tops[ci]) + gap
            ax.plot([x1, x1, x2, x2], [y, y + gap, y + gap, y],
                    lw=line_w, color=line_c, zorder=5)
            ax.text((x1 + x2) / 2.0, y + gap, sym, ha="center", va="bottom",
                    fontsize=sig_fs, color=line_c, zorder=5)

    y_min = params.get("y_min", 0)
    y_max = params.get("y_max")
    if y_max is None:
        y_max = data_top * float(params.get("y_headroom", 1.28))
    if y_min is not None and y_max is not None:
        ax.set_ylim(float(y_min), float(y_max))

    if params.get("grid", True):
        ax.grid(axis="y", alpha=float(params.get("grid_alpha", 0.3)),
                linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)

    rotation = float(params.get("xtick_rotation", 0))
    if params.get("xtick_mode", "category") == "group":
        # One tick per bar, named by its group (e.g. a single comparison of two groups).
        ticks = [(c + (gi - (n_groups - 1) / 2.0) * bar_w, g.get("label", f"Group {gi + 1}"))
                 for c in x for gi, g in enumerate(groups)]
        ax.set_xticks([t for t, _ in ticks])
        ax.set_xticklabels([lab for _, lab in ticks], rotation=rotation,
                           ha="right" if rotation else "center", fontsize=tick_sz)
    else:
        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=rotation,
                           ha="right" if rotation else "center", fontsize=tick_sz)
    ax.tick_params(axis="y", labelsize=tick_sz)       # y tick labels follow tick_label_size too
    a_wt = params.get("axes_label_weight", "bold")
    ax.set_xlabel(params.get("labels_xlabel", cat_col), fontsize=a_sz, fontweight=a_wt)
    ax.set_ylabel(params.get("labels_ylabel", "Value"), fontsize=a_sz, fontweight=a_wt)
    ax.margins(x=0.02)

    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=title_sz, fontweight="bold")

    if params.get("despine", True):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    if params.get("show_legend", True):
        ax.legend(loc=params.get("legend_loc", "upper right"),
                  fontsize=params.get("legend_fontsize", tick_sz),
                  frameon=bool(params.get("legend_frameon", False)),
                  ncol=int(params.get("legend_ncol", 1)))
