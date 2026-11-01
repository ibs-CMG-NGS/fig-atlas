"""correlation_scatter: two variables -- the points, a regression line with its
band, and r and P per group.

The line, the band and the numbers are results of a fit, so they come from the
analysis script (fig-atlas docs/howto/analysis_recipes.md, section 4), never
from this renderer (ADR 0007):

- the line and band are coordinates on extra rows of the same table: a grid of
  x values in fit_x_col with the fitted y in fit_y_col and, for a band, its
  edges in band_lower_col and band_upper_col (a confidence or a prediction
  band -- the script decides which, the legend says it). Fit rows carry the
  group they belong to; a fit row with no group is a line over all points.
- r and P are columns (r_col, p_col) holding one value per group, repeated on
  that group's rows. The text also offers r^2 and the number of points drawn.

Data: one row per item with the columns named by x_col and y_col (and
group_col), plus the fit rows. Returns the points drawn (group, x, y), ready
for fig_atlas.source_data.add.
"""
from __future__ import annotations

import pandas as pd
from matplotlib.font_manager import FontProperties

from fig_atlas.schema import Param, Schema, uses_schema

from ._basic import GROUPS, TEXT, X_AXIS, Y_AXIS, finish, groups, legend

FAMILY = "xy"    # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("correlation_scatter", extends=[GROUPS, X_AXIS, Y_AXIS, TEXT], params=[
    # [Data] points; the fit and the numbers arrive as columns from the analysis
    Param("x_col", str, "x", role="Column with the x values"),
    Param("y_col", str, "y", role="Column with the y values"),
    Param("fit_x_col", str, None, role="Column with the x grid of the fitted line, on fit rows (default: no line)"),
    Param("fit_y_col", str, None, role="Column with the fitted y at each fit_x"),
    Param("band_lower_col", str, None, role="Column with the band's lower edge at each fit_x (default: no band)"),
    Param("band_upper_col", str, None, role="Column with the band's upper edge at each fit_x"),
    Param("r_col", str, None, role="Column with each group's correlation r, from the analysis (default: no text)"),
    Param("p_col", str, None, role="Column with the P value that goes with r_col"),
    # [Points]
    Param("point_size", float, 12.0, unit="pt^2 (marker area)", range=(0, None), role="Point size",
          tune="lower for dense data"),
    Param("point_alpha", float, 0.8, unit="[0-1] opacity", range=(0, 1), role="Point opacity"),
    Param("point_edge_color", "color", "#ffffff", unit="hex color", role="Point outline colour"),
    Param("point_edge_width", float, 0.3, unit="pt", range=(0, None), role="Point outline width (0: none)"),
    # [Line and band]
    Param("show_fit", bool, True, role="Draw the fitted line when fit_x_col and fit_y_col are given"),
    Param("show_band", bool, True, role="Draw the band when band_lower_col and band_upper_col are given"),
    Param("fit_color", "color", None, unit="hex color",
          role="Line and band colour (default: the group's colour; a line over all groups uses color)"),
    Param("fit_line_width", float, 1.0, unit="pt", range=(0, None), role="Fitted line width"),
    Param("fit_line_style", str, "-", role="Fitted line style (matplotlib linestyle)"),
    Param("band_alpha", float, 0.18, unit="[0-1] opacity", range=(0, 1), role="Band fill opacity",
          tune="lower when bands of several groups overlap"),
    Param("band_edge_width", float, 0.0, unit="pt", range=(0, None), role="Band outline width (0: none)"),
    # [Statistics text] one line per group, printed from r_col / p_col
    Param("show_stats", bool, True, role="Print r and P when r_col and p_col are given"),
    Param("stats_format", str, "r = {r:.2f}, {p_text}",
          role="Text of one line; fields r, r2 (r squared), p (number), p_text ('P = 0.012' or 'P < 0.0001'), "
               "n (points drawn) and group (its label)"),
    Param("p_floor", float, 0.0001, unit="P value", range=(0, 1), role="Smaller P values print as 'P < p_floor'"),
    Param("p_digits", int, 2, unit="significant digits", range=(1, None), role="Digits of a printed P"),
    Param("stats_loc", ("upper left", "upper right", "lower left", "lower right"), "upper left",
          role="Corner of the axes holding the text", tune="move it away from the points"),
    Param("stats_pad", float, 0.03, unit="axes fraction", range=(0, None), role="Distance of the text from the corner"),
    Param("stats_line_spacing", float, 1.3, unit="multiple of the font size", range=(0, None),
          role="Distance between the lines of several groups"),
    Param("stats_fontsize", float, None, unit="pt", range=(0, None), role="Text size (default: tick_label_size)"),
    Param("stats_color_by_group", bool, True, role="Write each group's line in the group's colour"),
    Param("stats_color", "color", "#111827", unit="hex color", role="Text colour (one group, or colouring off)"),
])


def _p_text(p: float, floor: float, digits: int) -> str:
    return f"P < {floor:g}" if p < floor else f"P = {p:.{digits}g}"


def _first(rows: pd.DataFrame, col: str | None):
    if not col or col not in rows.columns:
        return None
    vals = rows[col].dropna()
    return float(vals.iloc[0]) if len(vals) else None


@uses_schema(SCHEMA)
def render_correlation_scatter(ax, df, params):
    """Draw the points, the fitted line and band, and the r/P text onto ``ax``;
    returns the points drawn."""
    x_col, y_col, g_col = params.get("x_col", "x"), params.get("y_col", "y"), params.get("group_col")
    fx_col, fy_col = params.get("fit_x_col"), params.get("fit_y_col")
    lo_col, hi_col = params.get("band_lower_col"), params.get("band_upper_col")
    if g_col and g_col not in df.columns:
        raise ValueError(f"correlation_scatter: group_col {g_col!r} is not a column of the data")
    points = df.dropna(subset=[c for c in (x_col, y_col) if c in df.columns]) if {x_col, y_col} <= set(df.columns) \
        else df.iloc[0:0]
    if points.empty:
        return pd.DataFrame(columns=["group", "x", "y"])

    has_fit = bool(params.get("show_fit", True) and fx_col and fy_col and fx_col in df.columns and fy_col in df.columns)
    has_band = bool(has_fit and params.get("show_band", True) and lo_col and hi_col
                    and lo_col in df.columns and hi_col in df.columns)
    fits = df.dropna(subset=[fx_col, fy_col]).sort_values(fx_col) if has_fit else df.iloc[0:0]
    fit_color = params.get("fit_color")
    width, style = float(params.get("fit_line_width", 1.0)), params.get("fit_line_style", "-")
    band_alpha = float(params.get("band_alpha", 0.18))

    def draw_fit(rows, color):
        if rows.empty:
            return
        if has_band:
            band = rows.dropna(subset=[lo_col, hi_col])
            ax.fill_between(band[fx_col].to_numpy(float), band[lo_col].to_numpy(float), band[hi_col].to_numpy(float),
                            color=color, alpha=band_alpha, linewidth=float(params.get("band_edge_width", 0.0)), zorder=1)
        ax.plot(rows[fx_col].to_numpy(float), rows[fy_col].to_numpy(float), color=color, linewidth=width,
                linestyle=style, zorder=2)

    drawn, lines = [], []
    for g, rows, color, label in groups(points, params):
        ax.scatter(rows[x_col], rows[y_col], s=float(params.get("point_size", 12.0)), color=color,
                   alpha=float(params.get("point_alpha", 0.8)), edgecolors=params.get("point_edge_color", "#ffffff"),
                   linewidths=float(params.get("point_edge_width", 0.3)), label=label, zorder=3)
        drawn.append(pd.DataFrame({"group": g, "x": rows[x_col].to_numpy(), "y": rows[y_col].to_numpy()}))
        if has_fit and g_col:
            draw_fit(fits[fits[g_col] == g], fit_color or color)
        stat_rows = df[df[g_col] == g] if g_col else df
        lines.append((label, color, len(rows), _first(stat_rows, params.get("r_col")),
                      _first(stat_rows, params.get("p_col"))))
    if has_fit:                                            # a line over all points: fit rows without a group
        draw_fit(fits[fits[g_col].isna()] if g_col else fits, fit_color or params.get("color", "#4b5563"))

    if params.get("show_stats", True) and params.get("r_col") and params.get("p_col"):
        for col in (params["r_col"], params["p_col"]):
            if col not in df.columns:
                raise ValueError(f"correlation_scatter: column {col!r} is missing; the analysis script writes r and P "
                                 "(docs/howto/analysis_recipes.md, section 4)")
        loc = params.get("stats_loc", "upper left")
        pad = float(params.get("stats_pad", 0.03))
        x0 = pad if "left" in loc else 1 - pad
        y0 = 1 - pad if "upper" in loc else pad
        size = params.get("stats_fontsize")
        if size is None:
            size = params.get("tick_label_size")
        pts = FontProperties(size=size).get_size_in_points()
        step = float(params.get("stats_line_spacing", 1.3)) * pts
        shown = [ln for ln in lines if ln[3] is not None and ln[4] is not None]
        if "lower" in loc:
            shown = shown[::-1]                            # the first group stays on top
        fmt, floor, digits = params.get("stats_format", "r = {r:.2f}, {p_text}"), \
            float(params.get("p_floor", 0.0001)), int(params.get("p_digits", 2))
        by_group = bool(params.get("stats_color_by_group", True)) and g_col
        for i, (label, color, n, r, p) in enumerate(shown):
            text = fmt.format(r=r, r2=r * r, p=p, p_text=_p_text(p, floor, digits), n=n, group=label or "")
            ax.annotate(text, xy=(x0, y0), xycoords="axes fraction", xytext=(0, (-i if "upper" in loc else i) * step),
                        textcoords="offset points", ha="left" if "left" in loc else "right",
                        va="top" if "upper" in loc else "bottom", fontsize=pts,
                        color=color if by_group else params.get("stats_color", "#111827"), zorder=6)

    finish(ax, params, x_col, y_col)
    legend(ax, params, bool(g_col))
    return pd.concat(drawn, ignore_index=True)
