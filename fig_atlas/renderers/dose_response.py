"""Dose-response: replicate responses per dose (mean +/- error, or every
point) with a four-parameter logistic fit per group, on a log dose axis.

Data: one row per replicate -- ``x_col`` (dose, > 0), ``y_col`` (response) and
optionally ``group_col`` (compound, cell line, ...). The fit is
y = bottom + (top - bottom) / (1 + (EC50 / x) ** hill), by least squares.
Returns one row per group: the fitted bottom, top, EC50 and hill, and n --
the numbers a legend would quote -- ready for ``fig_atlas.source_data.add``.
A group whose fit does not converge is drawn without a curve (fit_ok False).
"""
from __future__ import annotations

FAMILY = "xy"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd

from ..schema import Param, Schema, uses_schema
from ._basic import GROUPS, TEXT, X_AXIS, Y_AXIS, finish, groups, legend

SCHEMA = Schema("dose_response", extends=[GROUPS, X_AXIS, Y_AXIS, TEXT], params=[
    # [Data]
    Param("x_col", str, "dose", role="Column with the doses (positive numbers)"),
    Param("y_col", str, "response", role="Column with the responses (one row per replicate)"),
    Param("x_log", bool, True, role="Log-scaled dose axis (the usual way to show a dose series)"),
    # [Points]
    Param("points", ("mean", "all"), "mean", role="Per dose: the mean with an error bar, or every replicate"),
    Param("error", ("sem", "sd"), "sem", role="Error bar of the mean: standard error or standard deviation"),
    Param("marker_size", float, 4.0, unit="pt", range=(0, None), role="Point size"),
    Param("capsize", float, 2.0, unit="pt", range=(0, None), role="Width of the error-bar caps"),
    Param("error_width", float, 0.8, unit="pt", range=(0, None), role="Error-bar line width"),
    # [Fit]
    Param("fit", bool, True, role="Draw the four-parameter logistic fit"),
    Param("fit_line_width", float, 1.2, unit="pt", range=(0, None), role="Fit curve width"),
    Param("fit_points", int, 200, unit="points along the dose range", range=(10, None), role="Smoothness of the fit curve"),
    Param("show_ec50", bool, False, role="Mark each fitted EC50 with a dashed vertical line"),
    Param("ec50_line_width", float, 0.6, unit="pt", range=(0, None), role="EC50 line width"),
])


def four_pl(x, bottom, top, ec50, hill):
    return bottom + (top - bottom) / (1 + (ec50 / x) ** hill)


def fit_four_pl(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray | None, bool]:
    """Least-squares 4PL; starting values from the data. (params, converged)."""
    from scipy.optimize import curve_fit
    start = [float(np.min(y)), float(np.max(y)), float(np.median(x)), 1.0]
    try:
        p, _ = curve_fit(four_pl, x, y, p0=start, bounds=([-np.inf, -np.inf, 0, -np.inf], [np.inf] * 4),
                         maxfev=20000)
        return p, True
    except (RuntimeError, ValueError):
        return None, False


@uses_schema(SCHEMA)
def render_dose_response(ax, df, params):
    """Draw the points and fitted curves onto ``ax``; returns the fits."""
    x_col, y_col = params.get("x_col", "dose"), params.get("y_col", "response")
    data = df.assign(**{x_col: pd.to_numeric(df[x_col], errors="coerce"),
                        y_col: pd.to_numeric(df[y_col], errors="coerce")}).dropna(subset=[x_col, y_col])
    data = data[data[x_col] > 0]
    grouped = bool(params.get("group_col"))
    rows = []
    for g, sub, color, label in groups(data, params):
        if params.get("points", "mean") == "all":
            ax.plot(sub[x_col], sub[y_col], linestyle="none", marker="o", color=color,
                    markersize=params.get("marker_size", 4.0), label=label)
        else:
            s = sub.groupby(x_col)[y_col].agg(["mean", "std", "count"]).reset_index()
            err = s["std"] / np.sqrt(s["count"]) if params.get("error", "sem") == "sem" else s["std"]
            ax.errorbar(s[x_col], s["mean"], yerr=err, linestyle="none", marker="o", color=color,
                        markersize=params.get("marker_size", 4.0), capsize=params.get("capsize", 2.0),
                        elinewidth=params.get("error_width", 0.8), label=label)
        p, ok = fit_four_pl(sub[x_col].to_numpy(float), sub[y_col].to_numpy(float)) if params.get("fit", True) \
            else (None, False)
        if ok:
            xs = np.geomspace(sub[x_col].min(), sub[x_col].max(), int(params.get("fit_points", 200)))
            ax.plot(xs, four_pl(xs, *p), color=color, linewidth=params.get("fit_line_width", 1.2))
            if params.get("show_ec50", False):
                ax.axvline(p[2], color=color, linestyle="--", linewidth=params.get("ec50_line_width", 0.6))
        rows.append({"group": g, "n": len(sub), "fit_ok": ok,
                     **dict(zip(("bottom", "top", "ec50", "hill"), p if ok else [np.nan] * 4))})
    finish(ax, params, x_col, y_col)
    legend(ax, params, grouped)
    return pd.DataFrame(rows)
