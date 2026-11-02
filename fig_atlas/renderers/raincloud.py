"""raincloud: a half violin (the cloud), a box and the points (the rain) per
category -- the distribution, its summary and every value in one mark.

``orientation: horizontal`` (the classic raincloud) puts the categories on the
y axis, first at the top, each cloud above its box and the rain below;
``vertical`` puts the cloud to the right and the rain to the left. ``flip``
swaps the two sides.

The cloud's outline is a kernel density estimate and the box shows the
quartiles and whiskers: display arithmetic of the drawn shape, as in violin
and boxplot. Brackets compare each category with ``control_category``; their
P values come from the analysis script (fig-atlas
docs/howto/analysis_recipes.md, section 3) in the column named by pvalue_col,
on each category's rows. This renderer never runs a test (ADR 0007).

Data: one row per value with the columns named by category_col and value_col
(and pvalue_col). Returns the summary it drew (category, position, n, median,
q1, q3), ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

import matplotlib
import numpy as np
import pandas as pd

from fig_atlas.params import text_param
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema
from fig_atlas.stats import stars

FAMILY = "column"    # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("raincloud", params=[
    # [Data]
    Param("category_col", str, "group", role="Column with the categories (one raincloud each)"),
    Param("value_col", str, "value", role="Column with the values"),
    Param("pvalue_col", str, None,
          role="Column with each category's P value against control_category, from the analysis (default: none)"),
    Param("control_category", str, None, role="The category the brackets compare against (needed with pvalue_col)"),
    Param("category_order", list, None, role="Categories in drawing order (default: order in the data)"),
    Param("category_labels", dict, {}, open_keys=True, role="Tick label per category (default: the value)"),
    # [Layout]
    Param("orientation", ("horizontal", "vertical"), "horizontal",
          role="horizontal: categories on the y axis, first at the top; vertical: categories on the x axis"),
    Param("flip", bool, False, role="Swap the sides of the cloud and the rain"),
    # [Colours]
    Param("category_colors", dict, {}, open_keys=True, unit="hex color",
          role="Colour per category (default: matplotlib colour cycle)"),
    # [Cloud] half violin
    Param("show_cloud", bool, True, role="Draw the half violin"),
    Param("cloud_width", float, 0.4, unit="category units (categories are 1 apart)", range=(0, None),
          role="Height of the cloud at its widest", tune="lower if neighbouring clouds touch"),
    Param("cloud_offset", float, 0.08, unit="category units", range=(0, None),
          role="Gap between the box's centre and the cloud's base"),
    Param("cloud_alpha", float, 0.6, unit="[0-1] opacity", range=(0, 1), role="Cloud fill opacity"),
    Param("cloud_edge_color", "color", "#374151", unit="hex color", role="Cloud outline colour"),
    Param("cloud_edge_width", float, 0.5, unit="pt", range=(0, None), role="Cloud outline width"),
    Param("bandwidth", float, None, unit="multiple of the data's SD (kernel width)", range=(0, None),
          role="Smoothing of the cloud outline (default: Scott's rule, n^-1/5)",
          tune="lower to follow the data more closely, raise for a smoother outline"),
    Param("cloud_cut", float, 2.0, unit="kernel widths", range=(0, None),
          role="How far the cloud's tails reach beyond the lowest and highest value", tune="0 ends it at the data"),
    Param("cloud_points", int, 128, unit="points along the value axis", range=(16, None),
          role="Smoothness of the cloud outline"),
    # [Box]
    Param("show_box", bool, True, role="Draw the box (quartiles, median, whiskers)"),
    Param("box_width", float, 0.1, unit="category units", range=(0, None), role="Box width"),
    Param("box_color", "color", "#ffffff", unit="hex color", role="Box fill colour"),
    Param("box_edge_color", "color", "#111827", unit="hex color", role="Box outline, whisker and cap colour"),
    Param("box_line_width", float, 0.7, unit="pt", range=(0, None), role="Box outline and whisker width"),
    Param("median_color", "color", "#111827", unit="hex color", role="Median line colour"),
    Param("median_line_width", float, 1.0, unit="pt", range=(0, None), role="Median line width"),
    Param("whisker_range", float, 1.5, unit="multiple of the IQR", range=(0, None),
          role="Whiskers reach the furthest value within this many IQRs of the box (state it in the legend)"),
    # [Rain] points
    Param("show_points", bool, True, role="Draw every value as a point"),
    Param("point_color", "color", None, unit="hex color", role="Point colour (default: the category's colour)"),
    Param("point_size", float, 6.0, unit="pt^2 (marker area)", range=(0, None), role="Point size"),
    Param("point_alpha", float, 0.7, unit="[0-1] opacity", range=(0, 1), role="Point opacity"),
    Param("point_edge_width", float, 0.0, unit="pt", range=(0, None), role="Point outline width (0: none)"),
    Param("rain_offset", float, 0.18, unit="category units", range=(0, None),
          role="Distance of the rain's centre from the box's centre"),
    Param("rain_jitter", float, 0.06, unit="category units", range=(0, None),
          role="Scatter of the points across the rain band", tune="0 puts them on one line"),
    Param("point_seed", int, 0, unit="random seed", role="Seed of the jitter (fixed: the same picture every build)"),
    Param("category_margin", float, 0.05, unit="category units", range=(0, None),
          role="Room beyond the outermost cloud or rain"),
    # [Significance brackets]
    Param("show_significance", bool, True, role="Draw brackets when pvalue_col and control_category are given"),
    Param("sig_thresholds", list, [[0.001, "***"], [0.01, "**"], [0.05, "*"]], unit="P value",
          role="[threshold, symbol] pairs, P < threshold gets the symbol (state the rule in the legend)"),
    Param("sig_ns_display", str, "ns", role="Text for a P at or above every threshold ('' to draw no bracket)"),
    Param("sig_gap", float, 0.04, unit="fraction of the value range", range=(0, None),
          role="Gap between the highest value and a bracket"),
    Param("sig_tick", float, 0.02, unit="fraction of the value range", range=(0, None),
          role="Length of a bracket's end ticks"),
    Param("sig_step", float, 0.09, unit="fraction of the value range", range=(0, None),
          role="Distance between stacked brackets", tune="raise if the stars of stacked brackets touch"),
    Param("sig_line_color", "color", "#333333", unit="hex color", role="Bracket colour"),
    Param("sig_line_width", float, 0.8, unit="pt", range=(0, None), role="Bracket line width"),
    Param("sig_font_size", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Star size (default: tick_label_size)"),
    Param("sig_text_pad", float, 1.5, unit="pt", range=(0, None), role="Gap between a bracket and its star"),
    # [Axes and text]
    Param("value_min", float, None, unit="data coords", role="Lower limit of the value axis (default: the data)"),
    Param("value_max", float, None, unit="data coords",
          role="Upper limit of the value axis (default: the data, plus room for brackets)"),
    Param("value_headroom", float, 0.08, unit="fraction of the value range", range=(0, None),
          role="Room beyond the highest bracket"),
    Param("labels_title", str, None, role="Panel title (none: no title)"),
    Param("labels_xlabel", str, CODE_DEFAULT,
          role="x-axis title (default: value_col when horizontal, none when vertical)"),
    Param("labels_ylabel", str, CODE_DEFAULT,
          role="y-axis title (default: none when horizontal, value_col when vertical)"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Tick label size (default: rcParams)"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
])


def _kde(v: np.ndarray, factor, cut: float, points: int):
    """Gaussian kernel density of ``v`` on a grid reaching ``cut`` kernel widths past
    the data -- the outline of the drawn cloud (display arithmetic, as in violin)."""
    h = (factor if factor is not None else v.size ** -0.2) * v.std(ddof=1)
    grid = np.linspace(v.min() - cut * h, v.max() + cut * h, points)
    return grid, np.exp(-0.5 * ((grid[:, None] - v[None, :]) / h) ** 2).sum(axis=1)


@uses_schema(SCHEMA)
def render_raincloud(ax, df, params):
    """Draw one raincloud per category onto ``ax``; returns the summary drawn."""
    c_col, v_col, p_col = params.get("category_col", "group"), params.get("value_col", "value"), \
        params.get("pvalue_col")
    empty = pd.DataFrame(columns=["category", "position", "n", "median", "q1", "q3"])
    if c_col not in df.columns or v_col not in df.columns:
        return empty
    data = df.assign(**{v_col: pd.to_numeric(df[v_col], errors="coerce")}).dropna(subset=[c_col, v_col])
    seen = list(dict.fromkeys(data[c_col]))
    given = params.get("category_order")
    cats = [c for c in given if c in seen] if given else seen
    if not cats:
        return empty

    horizontal = params.get("orientation", "horizontal") == "horizontal"
    side = -1.0 if horizontal else 1.0                     # horizontal: y is inverted, so -1 is up
    if params.get("flip", False):
        side = -side

    def xy(pos, val):
        return (val, pos) if horizontal else (pos, val)

    colors = params.get("category_colors", {})
    cycle = matplotlib.rcParams["axes.prop_cycle"].by_key().get("color", [None])
    color_of = {c: colors.get(c) or cycle[i % len(cycle)] for i, c in enumerate(cats)}
    values = [data.loc[data[c_col] == c, v_col].to_numpy(float) for c in cats]
    orient = "horizontal" if horizontal else "vertical"

    cloud_w, cloud_off = float(params.get("cloud_width", 0.4)), float(params.get("cloud_offset", 0.08))
    reach = {i: (float(v.min()), float(v.max())) for i, v in enumerate(values) if v.size}  # value extent drawn
    if params.get("show_cloud", True):
        fill = ax.fill_between if horizontal else ax.fill_betweenx
        for i, (c, v) in enumerate(zip(cats, values)):
            if v.size < 2 or np.ptp(v) == 0:
                continue
            grid, dens = _kde(v, params.get("bandwidth"), float(params.get("cloud_cut", 2.0)),
                              int(params.get("cloud_points", 128)))
            base = i + side * cloud_off
            reach[i] = (min(reach[i][0], float(grid[0])), max(reach[i][1], float(grid[-1])))
            fill(grid, base, base + side * cloud_w * dens / dens.max(), facecolor=color_of[c],
                 alpha=float(params.get("cloud_alpha", 0.6)), edgecolor=params.get("cloud_edge_color", "#374151"),
                 linewidth=float(params.get("cloud_edge_width", 0.5)), zorder=1)

    box_w = float(params.get("box_width", 0.1))
    if params.get("show_box", True):
        edge, lw = params.get("box_edge_color", "#111827"), float(params.get("box_line_width", 0.7))
        keep = [i for i, v in enumerate(values) if v.size]
        ax.boxplot([values[i] for i in keep], positions=keep, widths=box_w, orientation=orient, showfliers=False,
                   patch_artist=True, whis=float(params.get("whisker_range", 1.5)), manage_ticks=False, zorder=3,
                   boxprops={"facecolor": params.get("box_color", "#ffffff"), "edgecolor": edge, "linewidth": lw},
                   whiskerprops={"color": edge, "linewidth": lw}, capprops={"color": edge, "linewidth": lw},
                   medianprops={"color": params.get("median_color", "#111827"),
                                "linewidth": float(params.get("median_line_width", 1.0))})

    rain_off, jit = float(params.get("rain_offset", 0.18)), float(params.get("rain_jitter", 0.06))
    if params.get("show_points", True):
        rng = np.random.default_rng(int(params.get("point_seed", 0)))
        for i, (c, v) in enumerate(zip(cats, values)):
            pos = i - side * rain_off + rng.uniform(-jit, jit, v.size)
            ax.scatter(*xy(pos, v), s=float(params.get("point_size", 6.0)),
                       color=params.get("point_color") or color_of[c], alpha=float(params.get("point_alpha", 0.7)),
                       linewidths=float(params.get("point_edge_width", 0.0)), zorder=2)

    lo = min(r[0] for r in reach.values())
    hi = max(r[1] for r in reach.values())
    span = (hi - lo) or 1.0
    top = hi
    ctrl = params.get("control_category")
    tick_sz = params.get("tick_label_size")
    if params.get("show_significance", True) and p_col and p_col in data.columns and ctrl in cats:
        thresholds = sorted((float(t), str(sym)) for t, sym in params.get(
            "sig_thresholds", [[0.001, "***"], [0.01, "**"], [0.05, "*"]]))
        ns = params.get("sig_ns_display", "ns")
        gap, tick = float(params.get("sig_gap", 0.04)) * span, float(params.get("sig_tick", 0.02)) * span
        step = float(params.get("sig_step", 0.09)) * span
        line_c, line_w = params.get("sig_line_color", "#333333"), float(params.get("sig_line_width", 0.8))
        sig_fs = params.get("sig_font_size", tick_sz)
        pad = float(params.get("sig_text_pad", 1.5))
        tops = {i: r[1] for i, r in reach.items()}
        pvals = data.dropna(subset=[p_col]).groupby(c_col)[p_col].first()
        ci = cats.index(ctrl)
        placed: list = []                                  # (p1, p2, level) of the brackets drawn
        for i, c in enumerate(cats):
            if c == ctrl or c not in pvals.index:
                continue
            sym = stars(float(pvals[c]), thresholds, ns)
            if not sym:
                continue
            p1, p2 = sorted((ci, i))
            level = max(t for k, t in tops.items() if p1 <= k <= p2) + gap
            for q1, q2, ql in placed:                      # stack beyond brackets that overlap this one
                if q1 <= p2 and p1 <= q2:
                    level = max(level, ql + step)
            ax.plot(*xy([p1, p1, p2, p2], [level, level + tick, level + tick, level]),
                    color=line_c, linewidth=line_w, zorder=5)
            ax.annotate(sym, xy=xy((p1 + p2) / 2, level + tick), xytext=(pad, 0) if horizontal else (0, pad),
                        textcoords="offset points", ha="left" if horizontal else "center",
                        va="center" if horizontal else "bottom", color=line_c, zorder=5,
                        **({} if sig_fs is None else {"fontsize": sig_fs}))
            placed.append((p1, p2, level))
            top = max(top, level + tick + step * 0.6)

    v_min, v_max = params.get("value_min"), params.get("value_max")
    upper = v_max if v_max is not None else (top + float(params.get("value_headroom", 0.08)) * span
                                             if top > hi else None)
    (ax.set_xlim if horizontal else ax.set_ylim)(v_min, upper)

    margin = float(params.get("category_margin", 0.05))
    reach_cloud = cloud_off + cloud_w if params.get("show_cloud", True) else box_w / 2
    reach_rain = rain_off + jit if params.get("show_points", True) else box_w / 2
    plus, minus = (reach_cloud, reach_rain) if side > 0 else (reach_rain, reach_cloud)
    lim = (-minus - margin, len(cats) - 1 + plus + margin)
    labels = [str(params.get("category_labels", {}).get(c, c)) for c in cats]
    if horizontal:
        ax.set_ylim(lim[1], lim[0])                        # first category at the top
        ax.set_yticks(range(len(cats)), labels)
    else:
        ax.set_xlim(*lim)
        ax.set_xticks(range(len(cats)), labels)

    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0))
    ax.set_xlabel(text_param(params, "labels_xlabel", v_col if horizontal else ""),
                  fontsize=params.get("axes_label_size"))
    ax.set_ylabel(text_param(params, "labels_ylabel", "" if horizontal else v_col),
                  fontsize=params.get("axes_label_size"))
    if tick_sz is not None:
        ax.tick_params(labelsize=tick_sz)
    if params.get("hide_top_right", True):
        ax.spines[["top", "right"]].set_visible(False)
    rows = [{"category": c, "position": i, "n": int(v.size), "median": float(np.median(v)),
             "q1": float(np.percentile(v, 25)), "q3": float(np.percentile(v, 75))}
            for i, (c, v) in enumerate(zip(cats, values)) if v.size]
    return pd.DataFrame(rows, columns=empty.columns)
