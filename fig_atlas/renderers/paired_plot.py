"""paired_plot: a before-after plot -- each subject's values joined across conditions.

One line per subject from condition to condition (before -> after, or more
than two time points), points at the values, an optional group summary (mean
or median) drawn over them, and an optional significance bracket per group.
With a group_col the groups sit side by side, each with its own conditions
(Prism's grouped before-after).

The bracket prints a P value the analysis script computed (a paired t-test or
Wilcoxon signed-rank; fig-atlas docs/howto/analysis_recipes.md, section 2) and
wrote into the column named by pvalue_col; this renderer never runs a test
(ADR 0007). The star rule comes from sig_thresholds.

Data: long format, one row per (subject, condition) with the columns named by
subject_col, condition_col and value_col (and group_col, pvalue_col). Returns
the rows it drew (subject, group, condition, x, value), ready for
fig_atlas.source_data.add.
"""
from __future__ import annotations

from fig_atlas.params import text_param
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema
from fig_atlas.stats import stars

FAMILY = "column"    # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("paired_plot", params=[
    # [Data]
    Param("subject_col", str, "subject", role="Column naming the subject each value belongs to (one line per subject)"),
    Param("condition_col", str, "condition", role="Column with the condition (x position): before, after, ..."),
    Param("value_col", str, "value", role="Column with the measured values (y)"),
    Param("group_col", str, None, role="Column with a second factor; its groups sit side by side (default: one group)"),
    Param("pvalue_col", str, None,
          role="Column with each group's P value from the analysis (paired test); draws the bracket (default: none)"),
    Param("condition_order", list, None, role="Conditions left to right (default: order in the data)"),
    Param("group_order", list, None, role="Groups left to right (default: order in the data)"),
    Param("condition_labels", dict, {}, open_keys=True, role="Tick label per condition (default: the value)"),
    Param("group_labels", dict, {}, open_keys=True, role="Label per group under its conditions (default: the value)"),
    # [Lines and points]
    Param("line_color_by", ("group", "direction"), "group",
          role="Colour a subject's line by its group, or by whether it went up or down from the first condition"),
    Param("group_colors", dict, {}, open_keys=True, unit="hex color", role="Colour per group (default: color)"),
    Param("color", "color", "#4b5563", unit="hex color", role="Line and point colour without a group colour"),
    Param("up_color", "color", "#dc2626", unit="hex color", role="Line colour of a subject that went up (line_color_by: direction)"),
    Param("down_color", "color", "#2563eb", unit="hex color", role="Line colour of a subject that went down (line_color_by: direction)"),
    Param("line_width", float, 0.8, unit="pt", range=(0, None), role="Subject line width"),
    Param("line_alpha", float, 0.7, unit="[0-1] opacity", range=(0, 1), role="Subject line opacity",
          tune="lower when many subjects overlap"),
    Param("point_size", float, 12.0, unit="pt^2 (marker area)", range=(0, None), role="Point size"),
    Param("point_alpha", float, 0.9, unit="[0-1] opacity", range=(0, 1), role="Point opacity"),
    Param("marker", str, "o", role="Point marker (matplotlib marker; '' for none)"),
    Param("point_edge_width", float, 0.0, unit="pt", range=(0, None), role="Outline width of the points and summary markers (0: none)"),
    # [Group summary]
    Param("summary", ("none", "mean", "median"), "none", role="Summary line drawn over the subjects"),
    Param("summary_color", "color", "#111827", unit="hex color", role="Summary line colour"),
    Param("summary_width", float, 2.0, unit="pt", range=(0, None), role="Summary line width"),
    Param("summary_marker_size", float, 30.0, unit="pt^2 (marker area)", range=(0, None), role="Summary marker size"),
    # [Layout]
    Param("condition_gap", float, 1.0, unit="x units between conditions", range=(0, None),
          role="Distance between neighbouring conditions"),
    Param("group_gap", float, 0.8, unit="x units", range=(0, None),
          role="Extra space between groups", tune="raise to separate the groups more"),
    Param("x_margin", float, 0.4, unit="x units", range=(0, None), role="Space left of the first and right of the last condition"),
    Param("y_min", float, None, unit="data coords", role="Lower y limit (default: matplotlib)"),
    Param("y_max", float, None, unit="data coords", role="Upper y limit (default: data top plus room for the brackets)"),
    Param("y_headroom", float, 0.12, unit="fraction of the data range", range=(0, None),
          role="Room above the data for the brackets", tune="raise if the stars touch the top"),
    # [Significance bracket]
    Param("show_significance", bool, True, role="Draw a bracket per group when pvalue_col is given"),
    Param("sig_thresholds", list, [[0.001, "***"], [0.01, "**"], [0.05, "*"]], unit="P value",
          role="[threshold, symbol] pairs, P < threshold gets the symbol (state the rule in the legend)"),
    Param("sig_ns_display", str, "ns", role="Text for a P at or above every threshold ('' to draw nothing)"),
    Param("sig_gap", float, 0.04, unit="fraction of the data range", range=(0, None), role="Gap between the data and the bracket"),
    Param("sig_tick", float, 0.02, unit="fraction of the data range", range=(0, None), role="Height of the bracket's end ticks"),
    Param("sig_line_color", "color", "#333333", unit="hex color", role="Bracket colour"),
    Param("sig_line_width", float, 0.8, unit="pt", range=(0, None), role="Bracket line width"),
    Param("sig_font_size", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Star size (default: tick_label_size)"),
    # [Text and axes]
    Param("labels_title", str, None, role="Panel title (none: no title)"),
    Param("labels_xlabel", str, "", role="x-axis title (default: none; the ticks name the conditions)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default: value_col)"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Tick label size (default: rcParams)"),
    Param("group_label_size", float, CODE_DEFAULT, unit="pt", range=(0, None),
          role="Size of the group labels under the ticks (default: tick_label_size)"),
    Param("group_label_pad", float, 14.0, unit="pt", range=(0, None),
          role="Distance of the group labels below the axis", tune="raise if they touch the tick labels"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
])


def _order(values, given):
    seen = list(dict.fromkeys(values))
    return [v for v in given if v in seen] if given else seen


@uses_schema(SCHEMA)
def render_paired_plot(ax, df, params):
    """Draw the before-after plot onto ``ax``; returns the rows drawn."""
    s_col = params.get("subject_col", "subject")
    c_col = params.get("condition_col", "condition")
    v_col = params.get("value_col", "value")
    g_col, p_col = params.get("group_col"), params.get("pvalue_col")
    cols = [c for c in (s_col, c_col, v_col, g_col, p_col) if c and c in df.columns]
    data = df[cols].dropna(subset=[s_col, c_col, v_col]).copy()
    if g_col is None:
        data["_group"] = ""
        g_key = "_group"
    else:
        g_key = g_col
    conditions = _order(data[c_col], params.get("condition_order"))
    groups = _order(data[g_key], params.get("group_order")) if g_col else [""]
    data = data[data[c_col].isin(conditions) & data[g_key].isin(groups)]

    step = float(params.get("condition_gap", 1.0))
    width = step * (len(conditions) - 1)
    block = width + float(params.get("group_gap", 0.8)) + step
    x_of = {(g, c): gi * block + ci * step for gi, g in enumerate(groups) for ci, c in enumerate(conditions)}
    data["x"] = [x_of[(g, c)] for g, c in zip(data[g_key], data[c_col])]

    colors = params.get("group_colors", {})
    base = params.get("color", "#4b5563")
    by_dir = params.get("line_color_by", "group") == "direction"
    lw, la = float(params.get("line_width", 0.8)), float(params.get("line_alpha", 0.7))
    ps, pa = float(params.get("point_size", 12.0)), float(params.get("point_alpha", 0.9))
    marker = params.get("marker", "o")
    edge_w = float(params.get("point_edge_width", 0.0))
    rank = {c: i for i, c in enumerate(conditions)}
    for (g, _), rows in data.groupby([g_key, s_col], sort=False):
        rows = rows.sort_values(c_col, key=lambda s: s.map(rank))
        color = colors.get(g, base)
        if by_dir and len(rows) > 1:
            first, last = rows[v_col].iloc[0], rows[v_col].iloc[-1]
            line_c = params.get("up_color", "#dc2626") if last > first else params.get("down_color", "#2563eb")
        else:
            line_c = color
        ax.plot(rows["x"], rows[v_col], color=line_c, linewidth=lw, alpha=la, zorder=2)
        if marker:
            ax.scatter(rows["x"], rows[v_col], s=ps, alpha=pa, color=color, marker=marker, zorder=3, linewidths=edge_w)

    how = params.get("summary", "none")
    if how != "none" and len(data):
        agg = data.groupby([g_key, c_col], sort=False)[v_col].agg(how).reset_index()
        agg["x"] = [x_of[(g, c)] for g, c in zip(agg[g_key], agg[c_col])]
        for _, rows in agg.groupby(g_key, sort=False):
            rows = rows.sort_values("x")
            ax.plot(rows["x"], rows[v_col], color=params.get("summary_color", "#111827"),
                    linewidth=float(params.get("summary_width", 2.0)), zorder=4)
            ax.scatter(rows["x"], rows[v_col], s=float(params.get("summary_marker_size", 30.0)),
                       color=params.get("summary_color", "#111827"), zorder=5, linewidths=edge_w)

    tick_sz = params.get("tick_label_size")
    lo, hi = (float(data[v_col].min()), float(data[v_col].max())) if len(data) else (0.0, 1.0)
    span = (hi - lo) or abs(hi) or 1.0
    if params.get("show_significance", True) and p_col and p_col in data.columns and len(conditions) > 1:
        thresholds = sorted((float(t), str(sym)) for t, sym in params.get(
            "sig_thresholds", [[0.001, "***"], [0.01, "**"], [0.05, "*"]]))
        ns = params.get("sig_ns_display", "ns")
        gap, tick = float(params.get("sig_gap", 0.04)) * span, float(params.get("sig_tick", 0.02)) * span
        line_c, line_w = params.get("sig_line_color", "#333333"), float(params.get("sig_line_width", 0.8))
        sig_fs = params.get("sig_font_size", tick_sz)
        for g in groups:
            rows = data[data[g_key] == g]
            pvals = rows[p_col].dropna()
            sym = stars(float(pvals.iloc[0]), thresholds, ns) if len(pvals) else ""
            if not sym:
                continue
            x1, x2 = x_of[(g, conditions[0])], x_of[(g, conditions[-1])]
            y = float(rows[v_col].max()) + gap
            ax.plot([x1, x1, x2, x2], [y, y + tick, y + tick, y], color=line_c, linewidth=line_w, zorder=6)
            ax.text((x1 + x2) / 2, y + tick, sym, ha="center", va="bottom", color=line_c, zorder=6,
                    **({} if sig_fs is None else {"fontsize": sig_fs}))

    margin = float(params.get("x_margin", 0.4))
    ax.set_xlim(-margin, x_of[(groups[-1], conditions[-1])] + margin if conditions else 1.0)
    y_min, y_max = params.get("y_min"), params.get("y_max")
    ax.set_ylim(bottom=y_min, top=y_max if y_max is not None else hi + float(params.get("y_headroom", 0.12)) * span
                + (float(params.get("sig_gap", 0.04)) + float(params.get("sig_tick", 0.02))) * span
                if p_col else None)
    c_labels = params.get("condition_labels", {})
    ax.set_xticks([x_of[(g, c)] for g in groups for c in conditions],
                  [str(c_labels.get(c, c)) for _ in groups for c in conditions])
    if g_col:
        g_labels = params.get("group_labels", {})
        g_fs = params.get("group_label_size", tick_sz)
        for g in groups:
            ax.annotate(str(g_labels.get(g, g)), xy=((x_of[(g, conditions[0])] + x_of[(g, conditions[-1])]) / 2, 0),
                        xycoords=("data", "axes fraction"), xytext=(0, -float(params.get("group_label_pad", 14.0))),
                        textcoords="offset points", ha="center", va="top",
                        **({} if g_fs is None else {"fontsize": g_fs}))

    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0))
    ax.set_xlabel(text_param(params, "labels_xlabel", ""), fontsize=params.get("axes_label_size"))
    ax.set_ylabel(text_param(params, "labels_ylabel", v_col), fontsize=params.get("axes_label_size"))
    if tick_sz is not None:
        ax.tick_params(labelsize=tick_sz)
    if params.get("hide_top_right", True):
        ax.spines[["top", "right"]].set_visible(False)
    out = data.rename(columns={s_col: "subject", c_col: "condition", v_col: "value", g_key: "group"})
    return out[["subject", "group", "condition", "x", "value"]].reset_index(drop=True)
