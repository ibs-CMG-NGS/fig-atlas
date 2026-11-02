"""bland_altman: agreement of two measurement methods -- each sample's
difference against its mean, with the bias and the limits of agreement.

Each point's mean and difference (or percent difference) are a change of axes
of the two measurements, worked out here. The bias and the limits of
agreement are results -- the mean difference and, usually, bias +/- 1.96 SD,
or limits from a regression or a non-parametric method -- so they come from
the analysis script as columns (bias_col, loa_low_col, loa_high_col), one
value repeated on every row (fig-atlas docs/howto/analysis_recipes.md, ADR
0007). The renderer draws the lines and prints their values at the right
edge with formats from the config.

Data: one row per sample with the columns named by a_col and b_col (and
group_col). Returns the points drawn (group, mean, difference), ready for
fig_atlas.source_data.add.
"""
from __future__ import annotations

import matplotlib
import numpy as np
import pandas as pd

from fig_atlas.params import text_param
from fig_atlas.schema import Param, Schema, uses_schema

from ._basic import GROUPS, TEXT, groups, legend

FAMILY = "diagnostic"    # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("bland_altman", extends=[GROUPS, TEXT], params=[
    # [Data] the two measurements; the lines arrive as columns from the analysis
    Param("a_col", str, "method_a", role="Column with the first method's measurement of each sample"),
    Param("b_col", str, "method_b", role="Column with the second method's measurement of each sample"),
    Param("difference", ("difference", "percent"), "difference",
          role="y axis: a - b, or 100 * (a - b) / mean of a and b (use the same in the analysis)"),
    Param("bias_col", str, None, role="Column with the bias (mean difference), from the analysis (default: no line)"),
    Param("loa_low_col", str, None, role="Column with the lower limit of agreement, from the analysis"),
    Param("loa_high_col", str, None, role="Column with the upper limit of agreement, from the analysis"),
    # [Points]
    Param("point_size", float, 12.0, unit="pt^2 (marker area)", range=(0, None), role="Point size"),
    Param("point_alpha", float, 0.8, unit="[0-1] opacity", range=(0, 1), role="Point opacity"),
    Param("point_edge_color", "color", "#ffffff", unit="hex color", role="Point outline colour"),
    Param("point_edge_width", float, 0.3, unit="pt", range=(0, None), role="Point outline width (0: none)"),
    # [Lines]
    Param("bias_color", "color", "#111827", unit="hex color", role="Bias line colour"),
    Param("bias_width", float, 1.0, unit="pt", range=(0, None), role="Bias line width"),
    Param("bias_style", str, "-", role="Bias line style (matplotlib linestyle)"),
    Param("loa_color", "color", "#6b7280", unit="hex color", role="Limits of agreement colour"),
    Param("loa_width", float, 0.8, unit="pt", range=(0, None), role="Limits of agreement line width"),
    Param("loa_style", str, "--", role="Limits of agreement line style (matplotlib linestyle)"),
    Param("show_zero", bool, True, role="Draw the line of no difference"),
    Param("zero_color", "color", "#d1d5db", unit="hex color", role="Line of no difference colour"),
    Param("zero_width", float, 0.6, unit="pt", range=(0, None), role="Line of no difference width"),
    # [Line labels] printed from the columns at the right edge
    Param("show_line_labels", bool, True, role="Write each line's value at its right end"),
    Param("bias_label", str, "Mean {value:.2f}", role="Bias label; field value"),
    Param("loa_high_label", str, "+1.96 SD {value:.2f}",
          role="Upper limit label; field value (say how the analysis made the limit)"),
    Param("loa_low_label", str, "−1.96 SD {value:.2f}", role="Lower limit label; field value"),
    Param("line_label_size", float, None, unit="pt", range=(0, None), role="Label size (default: tick_label_size)"),
    Param("line_label_pad", float, 1.5, unit="pt", range=(0, None), role="Gap between a label and its line"),
    # [Axes]
    Param("y_pad", float, 0.12, unit="fraction of the y range", range=(0, None),
          role="Room below and above the points and lines", tune="raise if a label touches the axes edge"),
    Param("y_min", float, None, unit="data coords", role="Lower y limit (default: the drawing less y_pad)"),
    Param("y_max", float, None, unit="data coords", role="Upper y limit (default: the drawing plus y_pad)"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
])


def _first(df: pd.DataFrame, col: str | None):
    if not col:
        return None
    if col not in df.columns:
        raise ValueError(f"bland_altman: column {col!r} is missing; the analysis script writes the bias and the "
                         "limits of agreement (ADR 0007)")
    vals = df[col].dropna()
    return float(vals.iloc[0]) if len(vals) else None


class _Signed(float):
    """A value that formats its minus sign the way the axes do (axes.unicode_minus)."""

    def __format__(self, spec):
        text = format(float(self), spec)
        return text.replace("-", "−") if matplotlib.rcParams["axes.unicode_minus"] else text


@uses_schema(SCHEMA)
def render_bland_altman(ax, df, params):
    """Draw the Bland-Altman plot onto ``ax``; returns the points drawn."""
    a_col, b_col, g_col = params.get("a_col", "method_a"), params.get("b_col", "method_b"), params.get("group_col")
    bias = _first(df, params.get("bias_col"))
    low, high = _first(df, params.get("loa_low_col")), _first(df, params.get("loa_high_col"))
    empty = pd.DataFrame(columns=["group", "mean", "difference"])
    if a_col not in df.columns or b_col not in df.columns:
        return empty
    a, b = pd.to_numeric(df[a_col], errors="coerce"), pd.to_numeric(df[b_col], errors="coerce")
    pts = df.assign(_mean=(a + b) / 2, _diff=a - b)
    if params.get("difference", "difference") == "percent":
        pts["_diff"] = 100.0 * pts["_diff"] / pts["_mean"]
    pts = pts.dropna(subset=["_mean", "_diff"])
    if pts.empty:
        return empty

    drawn = []
    for g, rows, color, label in groups(pts, params):
        ax.scatter(rows["_mean"], rows["_diff"], s=float(params.get("point_size", 12.0)), color=color,
                   alpha=float(params.get("point_alpha", 0.8)), edgecolors=params.get("point_edge_color", "#ffffff"),
                   linewidths=float(params.get("point_edge_width", 0.3)), label=label, zorder=3)
        drawn.append(pd.DataFrame({"group": g, "mean": rows["_mean"].to_numpy(), "difference": rows["_diff"].to_numpy()}))

    if params.get("show_zero", True):
        ax.axhline(0, color=params.get("zero_color", "#d1d5db"), linewidth=float(params.get("zero_width", 0.6)),
                   zorder=1)
    size = params.get("line_label_size")
    if size is None:
        size = params.get("tick_label_size")
    pad = float(params.get("line_label_pad", 1.5))
    lines = [(bias, "bias", "Mean {value:.2f}"), (high, "loa_high", "+1.96 SD {value:.2f}"),
             (low, "loa_low", "−1.96 SD {value:.2f}")]
    for value, key, default in lines:
        if value is None:
            continue
        kind = "bias" if key == "bias" else "loa"
        color = params.get(f"{kind}_color", "#111827" if kind == "bias" else "#6b7280")
        ax.axhline(value, color=color, linewidth=float(params.get(f"{kind}_width", 1.0 if kind == "bias" else 0.8)),
                   linestyle=params.get(f"{kind}_style", "-" if kind == "bias" else "--"), zorder=2)
        if params.get("show_line_labels", True):
            below = key == "loa_low"                       # the lower limit's label sits under its line
            ax.annotate(params.get(f"{key}_label", default).format(value=_Signed(value)), xy=(1, value),
                        xycoords=("axes fraction", "data"), xytext=(-pad, -pad if below else pad),
                        textcoords="offset points", ha="right", va="top" if below else "bottom", color=color,
                        zorder=4, **({} if size is None else {"fontsize": size}))

    ys = np.r_[pts["_diff"].to_numpy(float), [v for v in (bias, low, high) if v is not None], 0.0]
    lo, hi = float(ys.min()), float(ys.max())
    span = (hi - lo) or 1.0
    y_pad = float(params.get("y_pad", 0.12)) * span
    y_min, y_max = params.get("y_min"), params.get("y_max")
    ax.set_ylim(lo - y_pad if y_min is None else y_min, hi + y_pad if y_max is None else y_max)

    title = params.get("labels_title")
    if title:
        kw = {"fontsize": params.get("title_size", 8.0)}
        if params.get("title_pad") is not None:
            kw["pad"] = params.get("title_pad")
        ax.set_title(title, **kw)
    ylabel = "Difference (%)" if params.get("difference", "difference") == "percent" \
        else f"Difference ({a_col} − {b_col})"
    ax.set_xlabel(text_param(params, "labels_xlabel", f"Mean of {a_col} and {b_col}"),
                  fontsize=params.get("axes_label_size"))
    ax.set_ylabel(text_param(params, "labels_ylabel", ylabel), fontsize=params.get("axes_label_size"))
    if params.get("tick_label_size") is not None:
        ax.tick_params(labelsize=params.get("tick_label_size"))
    if params.get("hide_top_right", True):
        ax.spines[["top", "right"]].set_visible(False)
    legend(ax, params, bool(g_col))
    return pd.concat(drawn, ignore_index=True)
