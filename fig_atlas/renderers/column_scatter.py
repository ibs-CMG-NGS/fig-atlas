"""column_scatter: the values of each category as points, with a mean or
median line and error bars -- Prism's scatter dot plot.

Three point layouts:
- ``swarm`` (default) spreads the points sideways just enough that they do not
  overlap, at their true values (Prism's scatter dot plot). The spread is
  worked out at the axes' drawn size, so build the figure at its final size.
- ``jitter`` scatters them at random within point_jitter (seeded).
- ``aligned`` puts every point on the column's centre line.

The line and error bars are display arithmetic of the drawn values (mean or
median; SD, SEM, 95% CI or, with the median, the interquartile range).
Brackets compare each category with ``control_category``; their P values come
from the analysis script (fig-atlas docs/howto/analysis_recipes.md, section
3) in the column named by pvalue_col, on each category's rows. This renderer
never runs a test (ADR 0007).

Data: one row per value with the columns named by category_col and value_col
(and pvalue_col). Returns the summary it drew (category, x, n, centre, lower,
upper), ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

import matplotlib
import numpy as np
import pandas as pd

from fig_atlas.params import text_param
from fig_atlas.renderers.line_band import summarise
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema
from fig_atlas.stats import stars

FAMILY = "column"    # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("column_scatter", params=[
    # [Data]
    Param("category_col", str, "group", role="Column with the categories (one column of points each)"),
    Param("value_col", str, "value", role="Column with the values"),
    Param("pvalue_col", str, None,
          role="Column with each category's P value against control_category, from the analysis (default: none)"),
    Param("control_category", str, None, role="The category the brackets compare against (needed with pvalue_col)"),
    Param("category_order", list, None, role="Categories left to right (default: order in the data)"),
    Param("category_labels", dict, {}, open_keys=True, role="Tick label per category (default: the value)"),
    Param("category_colors", dict, {}, open_keys=True, unit="hex color",
          role="Point colour per category (default: matplotlib colour cycle)"),
    # [Points]
    Param("point_layout", ("swarm", "jitter", "aligned"), "swarm",
          role="swarm: spread sideways without overlap; jitter: random spread; aligned: one vertical line"),
    Param("point_size", float, 10.0, unit="pt^2 (marker area)", range=(0, None), role="Point size",
          tune="lower when a swarm grows wider than its column"),
    Param("point_alpha", float, 0.85, unit="[0-1] opacity", range=(0, 1), role="Point opacity"),
    Param("point_edge_color", "color", "#ffffff", unit="hex color", role="Point outline colour"),
    Param("point_edge_width", float, 0.0, unit="pt", range=(0, None), role="Point outline width (0: none)"),
    Param("point_marker", str, "o", role="Point marker (matplotlib marker)"),
    Param("swarm_spacing", float, 1.05, unit="multiple of the point diameter", range=(0, None),
          role="Distance kept between neighbouring points in a swarm", tune="raise for more air between points"),
    Param("max_spread", float, 0.8, unit="x units (categories are 1 apart)", range=(0, None),
          role="Widest a swarm may grow; a wider one is squeezed (points then overlap)"),
    Param("point_jitter", float, 0.15, unit="x units", range=(0, None), role="Half-width of the random spread (jitter)"),
    Param("point_seed", int, 0, unit="random seed", role="Seed of the jitter (fixed: the same picture every build)"),
    # [Summary line and error bars]
    Param("summary", ("mean", "median", "none"), "mean", role="Horizontal line at each category's mean or median"),
    Param("error", ("none", "sd", "sem", "ci95", "iqr"), "sd",
          role="Error bar: SD, SEM, 95% t-interval of the mean, or interquartile range (state it in the legend)"),
    Param("summary_width", float, 0.5, unit="x units", range=(0, None), role="Length of the summary line"),
    Param("summary_color", "color", "#111827", unit="hex color", role="Summary line and error bar colour"),
    Param("summary_line_width", float, 1.2, unit="pt", range=(0, None), role="Summary line width"),
    Param("error_width", float, 0.8, unit="pt", range=(0, None), role="Error bar line width"),
    Param("error_cap_size", float, 3.0, unit="pt", range=(0, None), role="Error bar cap length (0: no caps)"),
    # [Significance brackets]
    Param("show_significance", bool, True, role="Draw brackets when pvalue_col and control_category are given"),
    Param("sig_thresholds", list, [[0.001, "***"], [0.01, "**"], [0.05, "*"]], unit="P value",
          role="[threshold, symbol] pairs, P < threshold gets the symbol (state the rule in the legend)"),
    Param("sig_ns_display", str, "ns", role="Text for a P at or above every threshold ('' to draw no bracket)"),
    Param("sig_gap", float, 0.05, unit="fraction of the y range", range=(0, None),
          role="Gap between the highest point and a bracket"),
    Param("sig_tick", float, 0.02, unit="fraction of the y range", range=(0, None), role="Height of a bracket's end ticks"),
    Param("sig_step", float, 0.09, unit="fraction of the y range", range=(0, None),
          role="Vertical distance between stacked brackets", tune="raise if the stars of stacked brackets touch"),
    Param("sig_line_color", "color", "#333333", unit="hex color", role="Bracket colour"),
    Param("sig_line_width", float, 0.8, unit="pt", range=(0, None), role="Bracket line width"),
    Param("sig_font_size", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Star size (default: tick_label_size)"),
    # [Axes and text]
    Param("y_min", float, None, unit="data coords", role="Lower y limit (default: the data less y_pad)"),
    Param("y_max", float, None, unit="data coords", role="Upper y limit (default: the drawing plus y_pad)"),
    Param("y_pad", float, 0.06, unit="fraction of the y range", range=(0, None), role="Room below and above the marks"),
    Param("x_margin", float, 0.1, unit="x units", range=(0, None), role="Room left of the first and right of the last column"),
    Param("labels_title", str, None, role="Panel title (none: no title)"),
    Param("labels_xlabel", str, "", role="x-axis title (default: none; the ticks name the categories)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default: value_col)"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Tick label size (default: rcParams)"),
    Param("xtick_rotation", float, 0.0, unit="degrees", role="Rotation of the category labels", tune="45 for long names"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
])


def _swarm(y_px: np.ndarray, d: float) -> np.ndarray:
    """Sideways offsets (pixels) that keep points of diameter ``d`` at heights
    ``y_px`` from overlapping, each as close to the centre as it can be."""
    order = np.argsort(y_px, kind="stable")
    xs = np.zeros(len(y_px))
    placed: list = []                                      # (x, y) of the points placed
    for k in order:
        y = y_px[k]
        near = [(px, py) for px, py in placed if abs(py - y) < d]
        cands = [0.0] + [px + s * np.sqrt(d * d - (py - y) ** 2) for px, py in near for s in (-1, 1)]
        ok = [c for c in cands if all((c - px) ** 2 + (y - py) ** 2 >= d * d * (1 - 1e-9) for px, py in near)]
        xs[k] = min(ok, key=lambda c: (abs(c), c))
        placed.append((xs[k], y))
    return xs


@uses_schema(SCHEMA)
def render_column_scatter(ax, df, params):
    """Draw one column of points per category onto ``ax``; returns the summary drawn."""
    c_col, v_col, p_col = params.get("category_col", "group"), params.get("value_col", "value"), \
        params.get("pvalue_col")
    empty = pd.DataFrame(columns=["category", "x", "n", "centre", "lower", "upper"])
    if c_col not in df.columns or v_col not in df.columns:
        return empty
    data = df.assign(**{v_col: pd.to_numeric(df[v_col], errors="coerce")}).dropna(subset=[c_col, v_col])
    seen = list(dict.fromkeys(data[c_col]))
    given = params.get("category_order")
    cats = [c for c in given if c in seen] if given else seen
    data = data[data[c_col].isin(cats)]
    if data.empty:
        return empty

    colors = params.get("category_colors", {})
    cycle = matplotlib.rcParams["axes.prop_cycle"].by_key().get("color", [None])
    color_of = {c: colors.get(c) or cycle[i % len(cycle)] for i, c in enumerate(cats)}
    values = [data.loc[data[c_col] == c, v_col].to_numpy(float) for c in cats]

    agg, error = params.get("summary", "mean"), params.get("error", "sd")
    summ = summarise(pd.DataFrame({"category": data[c_col], "value": data[v_col]}), "category", "value", None,
                     "median" if agg == "median" else "mean", error if error in ("sd", "sem", "ci95") else "none")
    summ = summ.drop(columns="group").rename(columns={"x": "category"}).set_index("category").loc[cats].reset_index()
    if error == "iqr":
        summ["lower"] = [float(np.percentile(v, 25)) for v in values]
        summ["upper"] = [float(np.percentile(v, 75)) for v in values]
    summ.insert(1, "x", range(len(cats)))

    lo = min(float(v.min()) for v in values)
    hi = max(float(v.max()) for v in values)
    if agg != "none" and error != "none":
        lo, hi = min(lo, float(summ["lower"].min())), max(hi, float(summ["upper"].max()))
    span = (hi - lo) or 1.0
    top = hi
    ctrl = params.get("control_category")
    tick_sz = params.get("tick_label_size")
    if params.get("show_significance", True) and p_col and p_col in data.columns and ctrl in cats:
        thresholds = sorted((float(t), str(sym)) for t, sym in params.get(
            "sig_thresholds", [[0.001, "***"], [0.01, "**"], [0.05, "*"]]))
        ns = params.get("sig_ns_display", "ns")
        gap, tick = float(params.get("sig_gap", 0.05)) * span, float(params.get("sig_tick", 0.02)) * span
        step = float(params.get("sig_step", 0.09)) * span
        line_c, line_w = params.get("sig_line_color", "#333333"), float(params.get("sig_line_width", 0.8))
        sig_fs = params.get("sig_font_size", tick_sz)
        tops = {i: max(float(v.max()), float(summ["upper"].iloc[i]) if agg != "none" and error != "none"
                       else -np.inf) for i, v in enumerate(values)}
        pvals = data.dropna(subset=[p_col]).groupby(c_col)[p_col].first()
        ci = cats.index(ctrl)
        placed: list = []                                  # (x1, x2, y) of the brackets drawn
        for i, c in enumerate(cats):
            if c == ctrl or c not in pvals.index:
                continue
            sym = stars(float(pvals[c]), thresholds, ns)
            if not sym:
                continue
            x1, x2 = sorted((ci, i))
            y = max(t for k, t in tops.items() if x1 <= k <= x2) + gap
            for q1, q2, qy in placed:                      # stack above brackets that overlap this one
                if q1 <= x2 and x1 <= q2:
                    y = max(y, qy + step)
            ax.plot([x1, x1, x2, x2], [y, y + tick, y + tick, y], color=line_c, linewidth=line_w, zorder=5)
            ax.text((x1 + x2) / 2, y + tick, sym, ha="center", va="bottom", color=line_c, zorder=5,
                    **({} if sig_fs is None else {"fontsize": sig_fs}))
            placed.append((x1, x2, y))
            top = max(top, y + tick + step * 0.6)

    pad = float(params.get("y_pad", 0.06)) * span
    y_min, y_max = params.get("y_min"), params.get("y_max")
    ax.set_ylim(lo - pad if y_min is None else y_min, top + pad if y_max is None else y_max)
    margin = float(params.get("x_margin", 0.1))
    ax.set_xlim(-0.5 - margin, len(cats) - 0.5 + margin)

    layout = params.get("point_layout", "swarm")
    size = float(params.get("point_size", 10.0))
    rng = np.random.default_rng(int(params.get("point_seed", 0)))
    if layout == "swarm":                                  # pixels per x unit, at the axes' drawn size
        x0, x1 = ax.transData.transform([[0, 0], [1, 0]])[:, 0]
        px_per_x = abs(x1 - x0) or 1.0
        d = float(params.get("swarm_spacing", 1.05)) * np.sqrt(size) * ax.figure.dpi / 72.0
        limit = float(params.get("max_spread", 0.8)) / 2
    for i, (c, v) in enumerate(zip(cats, values)):
        if layout == "swarm":
            y_px = ax.transData.transform(np.column_stack([np.zeros(v.size), v]))[:, 1]
            off = _swarm(y_px, d) / px_per_x
            widest = np.abs(off).max() if off.size else 0.0
            if widest > limit:
                off *= limit / widest
        elif layout == "jitter":
            jit = float(params.get("point_jitter", 0.15))
            off = rng.uniform(-jit, jit, v.size)
        else:
            off = np.zeros(v.size)
        ax.scatter(i + off, v, s=size, color=color_of[c], alpha=float(params.get("point_alpha", 0.85)),
                   marker=params.get("point_marker", "o"), edgecolors=params.get("point_edge_color", "#ffffff"),
                   linewidths=float(params.get("point_edge_width", 0.0)), zorder=2)

    if agg != "none":
        color = params.get("summary_color", "#111827")
        half = float(params.get("summary_width", 0.5)) / 2
        ax.hlines(summ["centre"], summ["x"] - half, summ["x"] + half, color=color,
                  linewidth=float(params.get("summary_line_width", 1.2)), zorder=3)
        if error != "none":
            ok = summ["upper"].notna()
            r = summ[ok]
            ax.errorbar(r["x"].to_numpy(float), r["centre"].to_numpy(float),
                        yerr=[(r["centre"] - r["lower"]).to_numpy(float), (r["upper"] - r["centre"]).to_numpy(float)],
                        fmt="none", ecolor=color, elinewidth=float(params.get("error_width", 0.8)),
                        capsize=float(params.get("error_cap_size", 3.0)), zorder=3)

    c_labels = params.get("category_labels", {})
    rot = float(params.get("xtick_rotation", 0.0))
    ax.set_xticks(range(len(cats)), [str(c_labels.get(c, c)) for c in cats], rotation=rot,
                  ha="right" if rot else "center")
    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0))
    ax.set_xlabel(text_param(params, "labels_xlabel", ""), fontsize=params.get("axes_label_size"))
    ax.set_ylabel(text_param(params, "labels_ylabel", v_col), fontsize=params.get("axes_label_size"))
    if tick_sz is not None:
        ax.tick_params(labelsize=tick_sz)
    if params.get("hide_top_right", True):
        ax.spines[["top", "right"]].set_visible(False)
    return summ[["category", "x", "n", "centre", "lower", "upper"]]
