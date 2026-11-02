"""roc_curve: receiver operating characteristic curves -- one per marker --
with the chance line and each curve's AUC (and its confidence interval) in
the legend.

The curve is a result of ranking and the AUC a result of the curve, so both
come from the analysis script (fig-atlas docs/howto/analysis_recipes.md,
section 5), never from this renderer (ADR 0007): the curve as rows of false
and true positive rates (fpr_col, tpr_col), the AUC and its interval as
columns repeated on a marker's rows (auc_col, auc_low_col, auc_high_col). A
threshold the analysis picked (e.g. the Youden point) is marked by a truthy
operating_point_col on its row.

Data: one row per curve point with the columns named by fpr_col and tpr_col
(and group_col for several markers). Returns the curve points drawn (group,
fpr, tpr), ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

import pandas as pd

from fig_atlas.params import text_param
from fig_atlas.schema import Param, Schema, uses_schema

from ._basic import GROUPS, TEXT, groups, legend

FAMILY = "diagnostic"    # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("roc_curve", extends=[GROUPS, TEXT], params=[
    # [Data] the curve and the numbers arrive as columns from the analysis
    Param("fpr_col", str, "fpr", role="Column with the false positive rate (1 - specificity) of each curve point"),
    Param("tpr_col", str, "tpr", role="Column with the true positive rate (sensitivity) of each curve point"),
    Param("auc_col", str, None, role="Column with each curve's AUC, from the analysis (default: no AUC in the legend)"),
    Param("auc_low_col", str, None, role="Column with the lower end of the AUC's confidence interval"),
    Param("auc_high_col", str, None, role="Column with the upper end of the AUC's confidence interval"),
    Param("operating_point_col", str, None,
          role="Column that is true on the curve point to mark (a threshold the analysis picked)"),
    # [Curves]
    Param("line_width", float, 1.2, unit="pt", range=(0, None), role="Curve width"),
    Param("line_style", str, "-", role="Curve style (matplotlib linestyle)"),
    Param("show_chance", bool, True, role="Draw the diagonal of a classifier no better than chance"),
    Param("chance_color", "color", "#9ca3af", unit="hex color", role="Chance line colour"),
    Param("chance_width", float, 0.7, unit="pt", range=(0, None), role="Chance line width"),
    Param("chance_style", str, "--", role="Chance line style (matplotlib linestyle)"),
    Param("point_size", float, 18.0, unit="pt^2 (marker area)", range=(0, None), role="Operating point size"),
    Param("point_marker", str, "o", role="Operating point marker (matplotlib marker)"),
    Param("point_edge_color", "color", "#ffffff", unit="hex color", role="Operating point outline colour"),
    Param("point_edge_width", float, 0.6, unit="pt", range=(0, None), role="Operating point outline width"),
    # [Legend text] printed from the columns
    Param("legend_format", str, "{label} (AUC {auc:.2f}, {low:.2f}–{high:.2f})",
          role="Legend entry of a curve with an AUC and its interval; fields label, auc, low, high"),
    Param("legend_format_no_ci", str, "{label} (AUC {auc:.2f})",
          role="Legend entry of a curve with an AUC but no interval; fields label, auc"),
    # [Axes]
    Param("as_percent", bool, False, role="Show the rates as percentages (0-100) instead of fractions (0-1)"),
    Param("axis_pad", float, 0.02, unit="fraction of the axis", range=(0, None),
          role="Room beyond 0 and 1 so the curve's ends stay visible"),
    Param("square", bool, True, role="Draw the axes as a square (equal aspect)"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
])


def _first(rows: pd.DataFrame, col: str | None):
    if not col or col not in rows.columns:
        return None
    vals = rows[col].dropna()
    return float(vals.iloc[0]) if len(vals) else None


@uses_schema(SCHEMA)
def render_roc_curve(ax, df, params):
    """Draw one ROC curve per group onto ``ax``; returns the curve points drawn."""
    f_col, t_col, g_col = params.get("fpr_col", "fpr"), params.get("tpr_col", "tpr"), params.get("group_col")
    for col in (params.get("auc_col"), params.get("auc_low_col"), params.get("auc_high_col"),
                params.get("operating_point_col"), g_col):
        if col and col not in df.columns:
            raise ValueError(f"roc_curve: column {col!r} is missing; the analysis script writes the curve and its "
                             "AUC (docs/howto/analysis_recipes.md, section 5)")
    if f_col not in df.columns or t_col not in df.columns:
        return pd.DataFrame(columns=["group", "fpr", "tpr"])
    points = df.dropna(subset=[f_col, t_col])
    if points.empty:
        return pd.DataFrame(columns=["group", "fpr", "tpr"])

    scale = 100.0 if params.get("as_percent", False) else 1.0
    pad = float(params.get("axis_pad", 0.02)) * scale
    if params.get("show_chance", True):
        ax.plot([0, scale], [0, scale], color=params.get("chance_color", "#9ca3af"),
                linewidth=float(params.get("chance_width", 0.7)), linestyle=params.get("chance_style", "--"), zorder=1)

    op_col = params.get("operating_point_col")
    fmt_ci = params.get("legend_format", "{label} (AUC {auc:.2f}, {low:.2f}–{high:.2f})")
    fmt = params.get("legend_format_no_ci", "{label} (AUC {auc:.2f})")
    drawn = []
    for g, rows, color, label in groups(points, params):
        if rows.empty:
            continue
        auc = _first(rows, params.get("auc_col"))
        low, high = _first(rows, params.get("auc_low_col")), _first(rows, params.get("auc_high_col"))
        name = label or ""
        if auc is not None:
            name = (fmt_ci.format(label=name, auc=auc, low=low, high=high) if low is not None and high is not None
                    else fmt.format(label=name, auc=auc)).strip()
        x, y = rows[f_col].to_numpy(float) * scale, rows[t_col].to_numpy(float) * scale
        ax.plot(x, y, color=color, linewidth=float(params.get("line_width", 1.2)),
                linestyle=params.get("line_style", "-"), label=name or None, zorder=2)
        if op_col:
            mark = rows[rows[op_col].fillna(False).astype(bool)]
            if len(mark):
                ax.scatter(mark[f_col].to_numpy(float) * scale, mark[t_col].to_numpy(float) * scale,
                           s=float(params.get("point_size", 18.0)), marker=params.get("point_marker", "o"),
                           color=color, edgecolors=params.get("point_edge_color", "#ffffff"),
                           linewidths=float(params.get("point_edge_width", 0.6)), zorder=3)
        drawn.append(pd.DataFrame({"group": g, "fpr": rows[f_col].to_numpy(), "tpr": rows[t_col].to_numpy()}))

    ax.set_xlim(-pad, scale + pad)
    ax.set_ylim(-pad, scale + pad)
    if params.get("square", True):
        ax.set_aspect("equal", adjustable="box")
    pct = " (%)" if scale == 100.0 else ""
    title = params.get("labels_title")
    if title:
        kw = {"fontsize": params.get("title_size", 8.0)}
        if params.get("title_pad") is not None:
            kw["pad"] = params.get("title_pad")
        ax.set_title(title, **kw)
    ax.set_xlabel(text_param(params, "labels_xlabel", f"1 − specificity{pct}"),
                  fontsize=params.get("axes_label_size"))
    ax.set_ylabel(text_param(params, "labels_ylabel", f"Sensitivity{pct}"), fontsize=params.get("axes_label_size"))
    if params.get("tick_label_size") is not None:
        ax.tick_params(labelsize=params.get("tick_label_size"))
    if params.get("hide_top_right", True):
        ax.spines[["top", "right"]].set_visible(False)
    legend(ax, params, bool(g_col) or params.get("auc_col") is not None)
    return pd.concat(drawn, ignore_index=True)
