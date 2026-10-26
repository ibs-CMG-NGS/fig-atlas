"""Histogram: how a value is distributed, one histogram per group drawn over
each other (outlines or translucent bars) on shared bins.

Data: one row per observation -- ``x_col`` (the value) and optionally
``group_col``. Returns the counts drawn (group, bin_left, bin_right, count or
density), ready for ``fig_atlas.source_data.add``.
"""
from __future__ import annotations

FAMILY = "column"    # gallery family (fig_atlas/family.py): the shape this module draws

import numpy as np
import pandas as pd

from ..schema import Param, Schema, uses_schema
from ._basic import GROUPS, TEXT, X_AXIS, Y_AXIS, finish, groups, legend

SCHEMA = Schema("histogram", extends=[GROUPS, X_AXIS, Y_AXIS, TEXT], params=[
    # [Data]
    Param("x_col", str, "value", role="Column with the values"),
    Param("bins", int, 20, unit="number of bins", range=(1, None), role="Number of equal-width bins (shared by all groups)",
          tune="lower for small samples, raise for large ones"),
    Param("bin_min", float, None, unit="data coords", role="Left edge of the first bin (default: smallest value)"),
    Param("bin_max", float, None, unit="data coords", role="Right edge of the last bin (default: largest value)"),
    Param("density", bool, False, role="Show density (area 1 per group) instead of counts, so groups of different size compare"),
    # [Bars]
    Param("style", ("step", "bar"), "step", role="Outlines (step) or filled bars (bar); outlines read better with several groups"),
    Param("line_width", float, 1.0, unit="pt", range=(0, None), role="Outline width"),
    Param("fill_alpha", float, 0.35, unit="[0-1] opacity", range=(0, 1), role="Fill opacity of bars (style bar)"),
])


@uses_schema(SCHEMA)
def render_histogram(ax, df, params):
    """Draw the histograms onto ``ax``; returns the counts drawn."""
    x_col = params.get("x_col", "value")
    values = pd.to_numeric(df[x_col], errors="coerce")
    lo = params.get("bin_min") if params.get("bin_min") is not None else float(values.min())
    hi = params.get("bin_max") if params.get("bin_max") is not None else float(values.max())
    edges = np.linspace(lo, hi, int(params.get("bins", 20)) + 1)
    density, style = params.get("density", False), params.get("style", "step")
    rows = []
    grouped = bool(params.get("group_col"))
    for g, sub, color, label in groups(df.assign(**{x_col: values}).dropna(subset=[x_col]), params):
        v = sub[x_col].to_numpy()
        counts, _ = np.histogram(v, bins=edges, density=density)
        if style == "step":
            ax.hist(v, bins=edges, density=density, histtype="step", color=color, label=label,
                    linewidth=params.get("line_width", 1.0))
        else:
            ax.hist(v, bins=edges, density=density, histtype="stepfilled", color=color, label=label,
                    alpha=params.get("fill_alpha", 0.35), edgecolor=color, linewidth=params.get("line_width", 1.0))
        rows += [{"group": g, "bin_left": a, "bin_right": b, "density" if density else "count": c}
                 for a, b, c in zip(edges[:-1], edges[1:], counts)]
    finish(ax, params, x_col, "density" if density else "count")
    legend(ax, params, grouped)
    return pd.DataFrame(rows)
