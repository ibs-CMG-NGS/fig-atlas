"""grouped_bar: grouped bars -- two factors, a bar per group within each category.

Each bar is the mean (or median) of a group's replicates in one category, with
an SD, SEM or 95% CI error bar and the replicates drawn on top. Two
arrangements (Prism's grouped bar graphs): ``interleaved`` puts the groups side
by side within each category; ``separated`` gives each group its own block of
categories.

Brackets compare each group with a control group within a category (Dunnett
style). The P values come from the analysis script -- a post-hoc test against
the control (fig-atlas docs/howto/analysis_recipes.md, section 3) -- in the
column named by pvalue_col: on each (category, group) row, that group's P
against ``control_group``. This renderer never runs a test (ADR 0007).

Data: long format, one row per replicate with the columns named by
category_col, group_col and value_col (and pvalue_col). Returns the summary it
drew (category, group, x, n, centre, lower, upper), ready for
fig_atlas.source_data.add.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from fig_atlas.params import text_param
from fig_atlas.renderers.line_band import summarise
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema
from fig_atlas.stats import stars

FAMILY = "grouped"   # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("grouped_bar", params=[
    # [Data]
    Param("category_col", str, "category", role="Column with the first factor (x categories)"),
    Param("group_col", str, "group", role="Column with the second factor (bar colour)"),
    Param("value_col", str, "value", role="Column with the replicate values"),
    Param("pvalue_col", str, None,
          role="Column with each (category, group)'s P value against control_group, from the analysis (default: none)"),
    Param("control_group", str, None, role="The group the brackets compare against (needed with pvalue_col)"),
    Param("category_order", list, None, role="Categories left to right (default: order in the data)"),
    Param("group_order", list, None, role="Groups in each cluster or block (default: order in the data)"),
    Param("category_labels", dict, {}, open_keys=True, role="Tick label per category (default: the value)"),
    Param("group_labels", dict, {}, open_keys=True, role="Legend or block label per group (default: the value)"),
    # [Arrangement]
    Param("arrangement", ("interleaved", "separated"), "interleaved",
          role="interleaved: groups side by side in each category; separated: one block of categories per group"),
    Param("bar_width", float, 0.8, unit="x units (categories are 1 apart)", range=(0, None),
          role="Width of a cluster of groups (interleaved) or of one bar (separated)", tune="lower for thinner bars"),
    Param("block_gap", float, 0.8, unit="x units", range=(0, None), role="Extra space between blocks (separated)"),
    # [Bars and error]
    Param("summary", ("mean", "median"), "mean", role="Bar height"),
    Param("error", ("none", "sd", "sem", "ci95"), "sem",
          role="Error bar: SD, SEM or 95% t-interval of the mean (state it in the legend)"),
    Param("group_colors", dict, {}, open_keys=True, unit="hex color", role="Colour per group (default: color)"),
    Param("color", "color", "#9ca3af", unit="hex color", role="Bar colour without a group colour"),
    Param("bar_alpha", float, 0.85, unit="[0-1] opacity", range=(0, 1), role="Bar fill opacity"),
    Param("bar_edge_color", "color", "#374151", unit="hex color", role="Bar outline colour"),
    Param("bar_edge_width", float, 0.6, unit="pt", range=(0, None), role="Bar outline width"),
    Param("error_color", "color", "#111827", unit="hex color", role="Error bar colour"),
    Param("error_width", float, 0.8, unit="pt", range=(0, None), role="Error bar line width"),
    Param("error_cap_size", float, 2.5, unit="pt", range=(0, None), role="Error bar cap length (0: no caps)"),
    # [Replicate points]
    Param("show_points", bool, True, role="Draw the replicates over the bars"),
    Param("point_color", "color", "#111827", unit="hex color", role="Replicate point colour"),
    Param("point_size", float, 8.0, unit="pt^2 (marker area)", range=(0, None), role="Replicate point size"),
    Param("point_alpha", float, 0.8, unit="[0-1] opacity", range=(0, 1), role="Replicate point opacity"),
    Param("point_edge_width", float, 0.0, unit="pt", range=(0, None), role="Replicate point outline width (0: none)"),
    Param("point_jitter", float, 0.25, unit="fraction of a bar's width", range=(0, 1),
          role="Horizontal scatter of the points within a bar", tune="0 puts them in one column"),
    Param("point_seed", int, 0, unit="random seed", role="Seed of the jitter (fixed: the same picture every build)"),
    # [Significance brackets]
    Param("show_significance", bool, True, role="Draw brackets when pvalue_col and control_group are given"),
    Param("sig_thresholds", list, [[0.001, "***"], [0.01, "**"], [0.05, "*"]], unit="P value",
          role="[threshold, symbol] pairs, P < threshold gets the symbol (state the rule in the legend)"),
    Param("sig_ns_display", str, "ns", role="Text for a P at or above every threshold ('' to draw no bracket)"),
    Param("sig_gap", float, 0.04, unit="fraction of the y range", range=(0, None), role="Gap between the bars and a bracket"),
    Param("sig_tick", float, 0.02, unit="fraction of the y range", range=(0, None), role="Height of a bracket's end ticks"),
    Param("sig_step", float, 0.09, unit="fraction of the y range", range=(0, None),
          role="Vertical distance between stacked brackets", tune="raise if the stars of stacked brackets touch"),
    Param("sig_line_color", "color", "#333333", unit="hex color", role="Bracket colour"),
    Param("sig_line_width", float, 0.8, unit="pt", range=(0, None), role="Bracket line width"),
    Param("sig_font_size", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Star size (default: tick_label_size)"),
    # [Axes, text and legend]
    Param("y_min", float, None, unit="data coords", role="Lower y limit (default: 0 for non-negative data)"),
    Param("y_max", float, None, unit="data coords", role="Upper y limit (default: the top of the drawing plus y_headroom)"),
    Param("y_headroom", float, 0.06, unit="fraction of the y range", range=(0, None), role="Room above the highest mark"),
    Param("labels_title", str, None, role="Panel title (none: no title)"),
    Param("labels_xlabel", str, "", role="x-axis title (default: none; the ticks name the categories)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default: value_col)"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Tick label size (default: rcParams)"),
    Param("xtick_rotation", float, 0.0, unit="degrees", role="Rotation of the category labels", tune="45 for long names"),
    Param("block_label_pad", float, 14.0, unit="pt", range=(0, None),
          role="Distance of the block labels below the axis (separated)", tune="raise if they touch the tick labels"),
    Param("show_legend", bool, True, role="Show the group legend (interleaved)"),
    Param("legend_loc", str, "best", role="Legend location (matplotlib loc)"),
    Param("legend_anchor", list, None, unit="axes fraction (x, y)",
          role="bbox_to_anchor for the legend (default: inside, at legend_loc)"),
    Param("legend_frameon", bool, False, role="Draw a frame around the legend"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
])


def _order(values, given):
    seen = list(dict.fromkeys(values))
    return [v for v in given if v in seen] if given else seen


@uses_schema(SCHEMA)
def render_grouped_bar(ax, df, params):
    """Draw the grouped bars onto ``ax``; returns the summary drawn."""
    c_col = params.get("category_col", "category")
    g_col = params.get("group_col", "group")
    v_col = params.get("value_col", "value")
    p_col = params.get("pvalue_col")
    keep = [c for c in (c_col, g_col, v_col, p_col) if c and c in df.columns]
    data = df[keep].dropna(subset=[c_col, g_col, v_col])
    cats = _order(data[c_col], params.get("category_order"))
    groups = _order(data[g_col], params.get("group_order"))
    data = data[data[c_col].isin(cats) & data[g_col].isin(groups)]
    if data.empty:
        return pd.DataFrame(columns=["category", "group", "x", "n", "centre", "lower", "upper"])

    width = float(params.get("bar_width", 0.8))
    if params.get("arrangement", "interleaved") == "separated":
        gap = float(params.get("block_gap", 0.8))
        bar_w = width
        x_of = {(c, g): gi * (len(cats) + gap) + ci for gi, g in enumerate(groups) for ci, c in enumerate(cats)}
    else:
        bar_w = width / max(len(groups), 1)
        x_of = {(c, g): ci + (gi - (len(groups) - 1) / 2) * bar_w
                for gi, g in enumerate(groups) for ci, c in enumerate(cats)}

    summ = summarise(data, c_col, v_col, g_col, params.get("summary", "mean"), params.get("error", "sem"))
    summ = summ.rename(columns={"x": "category"})
    summ["x"] = [x_of[(c, g)] for c, g in zip(summ["category"], summ["group"])]
    colors, base = params.get("group_colors", {}), params.get("color", "#9ca3af")
    labels = params.get("group_labels", {})
    tops: dict = {}                                        # x -> highest mark drawn there
    for g in groups:
        rows = summ[summ["group"] == g]
        ax.bar(rows["x"], rows["centre"], width=bar_w, color=colors.get(g, base),
               alpha=float(params.get("bar_alpha", 0.85)), edgecolor=params.get("bar_edge_color", "#374151"),
               linewidth=float(params.get("bar_edge_width", 0.6)), label=str(labels.get(g, g)), zorder=1)
        if params.get("error", "sem") != "none":
            ok = rows["upper"].notna()
            r = rows[ok]
            ax.errorbar(r["x"].to_numpy(float), r["centre"].to_numpy(float),
                        yerr=[(r["centre"] - r["lower"]).to_numpy(float), (r["upper"] - r["centre"]).to_numpy(float)],
                        fmt="none", ecolor=params.get("error_color", "#111827"),
                        elinewidth=float(params.get("error_width", 0.8)),
                        capsize=float(params.get("error_cap_size", 2.5)), zorder=3)
        for x, top in zip(rows["x"], rows[["centre", "upper"]].max(axis=1)):
            tops[x] = max(tops.get(x, -np.inf), float(top))

    if params.get("show_points", True) and len(data):
        rng = np.random.default_rng(int(params.get("point_seed", 0)))
        jit = float(params.get("point_jitter", 0.25)) * bar_w
        xs = np.array([x_of[(c, g)] for c, g in zip(data[c_col], data[g_col])], dtype=float)
        xs = xs + rng.uniform(-jit, jit, len(xs))
        ax.scatter(xs, data[v_col], s=float(params.get("point_size", 8.0)), color=params.get("point_color", "#111827"),
                   alpha=float(params.get("point_alpha", 0.8)),
                   linewidths=float(params.get("point_edge_width", 0.0)), zorder=4)
        for (c, g), v in data.groupby([c_col, g_col])[v_col].max().items():
            tops[x_of[(c, g)]] = max(tops.get(x_of[(c, g)], -np.inf), float(v))

    lo = min(0.0, float(data[v_col].min())) if len(data) else 0.0
    hi = max(tops.values(), default=1.0)
    span = (hi - lo) or 1.0
    ctrl = params.get("control_group")
    tick_sz = params.get("tick_label_size")
    if params.get("show_significance", True) and p_col and p_col in data.columns and ctrl in groups:
        thresholds = sorted((float(t), str(sym)) for t, sym in params.get(
            "sig_thresholds", [[0.001, "***"], [0.01, "**"], [0.05, "*"]]))
        ns = params.get("sig_ns_display", "ns")
        gap, tick = float(params.get("sig_gap", 0.04)) * span, float(params.get("sig_tick", 0.02)) * span
        step = float(params.get("sig_step", 0.09)) * span
        line_c, line_w = params.get("sig_line_color", "#333333"), float(params.get("sig_line_width", 0.8))
        sig_fs = params.get("sig_font_size", tick_sz)
        pvals = data.dropna(subset=[p_col]).groupby([c_col, g_col])[p_col].first()
        placed: list = []                                  # (x1, x2, y) of the brackets drawn
        for c in cats:
            for g in groups:
                if g == ctrl or (c, g) not in pvals.index:
                    continue
                sym = stars(float(pvals[(c, g)]), thresholds, ns)
                if not sym:
                    continue
                x1, x2 = sorted((x_of[(c, ctrl)], x_of[(c, g)]))
                y = max(t for x, t in tops.items() if x1 - 1e-9 <= x <= x2 + 1e-9) + gap
                for px1, px2, py in placed:                # stack above brackets that overlap this one
                    if px1 <= x2 and x1 <= px2:
                        y = max(y, py + step)
                ax.plot([x1, x1, x2, x2], [y, y + tick, y + tick, y], color=line_c, linewidth=line_w, zorder=5)
                ax.text((x1 + x2) / 2, y + tick, sym, ha="center", va="bottom", color=line_c, zorder=5,
                        **({} if sig_fs is None else {"fontsize": sig_fs}))
                placed.append((x1, x2, y))
                hi = max(hi, y + tick + step * 0.6)

    y_min = params.get("y_min")
    ax.set_ylim(bottom=0.0 if y_min is None and lo >= 0 else y_min,
                top=params.get("y_max") if params.get("y_max") is not None
                else hi + float(params.get("y_headroom", 0.06)) * span)
    c_labels = params.get("category_labels", {})
    rot = float(params.get("xtick_rotation", 0.0))
    if params.get("arrangement", "interleaved") == "separated":
        ax.set_xticks([x_of[(c, g)] for g in groups for c in cats],
                      [str(c_labels.get(c, c)) for _ in groups for c in cats], rotation=rot,
                      ha="right" if rot else "center")
        for g in groups:
            mid = (x_of[(cats[0], g)] + x_of[(cats[-1], g)]) / 2
            ax.annotate(str(labels.get(g, g)), xy=(mid, 0), xycoords=("data", "axes fraction"),
                        xytext=(0, -float(params.get("block_label_pad", 14.0))), textcoords="offset points",
                        ha="center", va="top", **({} if tick_sz is None else {"fontsize": tick_sz}))
    else:
        ax.set_xticks(range(len(cats)), [str(c_labels.get(c, c)) for c in cats], rotation=rot,
                      ha="right" if rot else "center")
        if params.get("show_legend", True) and len(groups) > 1:
            anchor = params.get("legend_anchor")
            ax.legend(loc=params.get("legend_loc", "best"), frameon=bool(params.get("legend_frameon", False)),
                      **({} if anchor is None else {"bbox_to_anchor": tuple(anchor)}),
                      **({} if tick_sz is None else {"fontsize": tick_sz}))

    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0))
    ax.set_xlabel(text_param(params, "labels_xlabel", ""), fontsize=params.get("axes_label_size"))
    ax.set_ylabel(text_param(params, "labels_ylabel", v_col), fontsize=params.get("axes_label_size"))
    if tick_sz is not None:
        ax.tick_params(labelsize=tick_sz)
    if params.get("hide_top_right", True):
        ax.spines[["top", "right"]].set_visible(False)
    return summ[["category", "group", "x", "n", "centre", "lower", "upper"]].reset_index(drop=True)
