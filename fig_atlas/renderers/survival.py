"""Survival curves (Kaplan-Meier): the share still without the event over
time, one step curve per group, with ticks where observations were censored.

Data: one row per subject -- ``time_col`` (time to the event or to the last
follow-up) and ``event_col`` (1 or True: the event happened; 0 or False:
censored), and optionally ``group_col``. The estimate is computed here (no
survival package needed). No test is drawn: compare groups with a log-rank
test through fig_atlas.stats and quote it in the legend (AGENTS.md 4.6).
Returns the curve drawn (group, time, at_risk, events, censored, survival),
ready for ``fig_atlas.source_data.add``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..schema import Param, Schema, uses_schema
from ._basic import GROUPS, TEXT, X_AXIS, Y_AXIS, finish, groups, legend

SCHEMA = Schema("survival", extends=[GROUPS, X_AXIS, Y_AXIS, TEXT], params=[
    # [Data]
    Param("time_col", str, "time", role="Column with the time to the event or to the last follow-up"),
    Param("event_col", str, "event", role="Column: 1 (or True) if the event happened, 0 (or False) if censored"),
    Param("percent", bool, True, role="Show survival in % (0-100) instead of a fraction (0-1)"),
    # [Curves]
    Param("line_width", float, 1.2, unit="pt", range=(0, None), role="Curve width"),
    Param("show_censored", bool, True, role="Mark censored subjects with a tick on the curve"),
    Param("censor_marker", str, "|", role="Censor mark (matplotlib marker)"),
    Param("censor_size", float, 5.0, unit="pt", range=(0, None), role="Censor mark size"),
])


def kaplan_meier(time: np.ndarray, event: np.ndarray) -> pd.DataFrame:
    """The product-limit estimate at each distinct time (time 0 first)."""
    rows = [{"time": 0.0, "at_risk": int(time.size), "events": 0, "censored": 0, "survival": 1.0}]
    s = 1.0
    for t in np.unique(time):
        at_risk = int((time >= t).sum())
        d = int(((time == t) & event).sum())
        c = int(((time == t) & ~event).sum())
        if at_risk:
            s *= 1 - d / at_risk
        rows.append({"time": float(t), "at_risk": at_risk, "events": d, "censored": c, "survival": s})
    return pd.DataFrame(rows)


@uses_schema(SCHEMA)
def render_survival(ax, df, params):
    """Draw the Kaplan-Meier curves onto ``ax``; returns the estimates drawn."""
    t_col, e_col = params.get("time_col", "time"), params.get("event_col", "event")
    data = df.assign(**{t_col: pd.to_numeric(df[t_col], errors="coerce")}).dropna(subset=[t_col, e_col])
    scale = 100.0 if params.get("percent", True) else 1.0
    grouped = bool(params.get("group_col"))
    out = []
    for g, sub, color, label in groups(data, params):
        km = kaplan_meier(sub[t_col].to_numpy(float), sub[e_col].astype(bool).to_numpy())
        ax.step(km["time"], km["survival"] * scale, where="post", color=color, label=label,
                linewidth=params.get("line_width", 1.2))
        if params.get("show_censored", True):
            cens = km[km["censored"] > 0]
            ax.plot(cens["time"], cens["survival"] * scale, linestyle="none", color=color,
                    marker=params.get("censor_marker", "|"), markersize=params.get("censor_size", 5.0))
        out.append(km.assign(group=g))
    finish(ax, params, t_col, "survival (%)" if scale == 100.0 else "survival")
    legend(ax, params, grouped)
    return pd.concat(out, ignore_index=True)[["group", "time", "at_risk", "events", "censored", "survival"]]
