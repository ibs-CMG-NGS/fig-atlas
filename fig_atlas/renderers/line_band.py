"""Line + error band: a centre line per group over x, with a shaded band
(roadmap 6a.3, a domain-neutral renderer).

Two ways in:

* replicate rows (``x_col``, ``y_col``, optional ``group_col``): the renderer
  summarises each (group, x) -- mean or median, with SEM, SD or a 95 %
  t-interval as the band -- and can overlay the replicates as points;
* already summarised rows: set ``aggregate: none`` and give ``lower_col`` /
  ``upper_col`` (and ``y_col`` as the centre).

x can be numeric (time, dose; optionally on a log axis) or categorical with
``x_order``. Returns the summary it drew (group, x, n, centre, lower, upper),
ready for ``fig_atlas.source_data.add``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..params import text_param
from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("line_band", params=[
    # [Data]
    Param("x_col", str, "x", role="Column with the x values (numeric, or categories with x_order)"),
    Param("y_col", str, "y", role="Column with the values (replicates), or the centre when aggregate is none"),
    Param("group_col", str, None, role="Column splitting the lines (default: one line)"),
    Param("group_order", list, None, role="Group order in drawing and legend (default: order in the data)"),
    Param("x_order", list, None, role="Category order on x; set it to treat x as categories"),
    Param("aggregate", ("mean", "median", "none"), "mean",
          role="Centre of each (group, x): mean or median of the replicates, or none for summarised rows"),
    Param("error", ("sem", "sd", "ci95", "none"), "sem",
          role="Band around the centre: standard error, standard deviation, 95% t-interval, or none"),
    Param("lower_col", str, None, role="Lower band edge column (aggregate none)"),
    Param("upper_col", str, None, role="Upper band edge column (aggregate none)"),
    # [Lines, bands, points]
    Param("group_colors", dict, {}, open_keys=True, unit="hex color", role="Colour per group (default: matplotlib cycle)"),
    Param("group_labels", dict, {}, open_keys=True, role="Legend label per group"),
    Param("line_width", float, 1.2, unit="pt", range=(0, None), role="Centre line width"),
    Param("line_style", str, "-", role="Centre line style (matplotlib)"),
    Param("marker", str, "o", role="Marker at each x on the line ('' for none)"),
    Param("marker_size", float, 3.0, unit="pt", range=(0, None), role="Line marker size"),
    Param("band_alpha", float, 0.25, unit="[0-1] opacity", range=(0, 1), role="Band opacity", tune="lower when bands overlap"),
    Param("band_edge_width", float, 0.0, unit="pt", range=(0, None), role="Outline width of the band (0: none)"),
    Param("show_points", bool, False, role="Overlay the replicate values as points"),
    Param("point_size", float, 8.0, unit="pt^2 (marker area)", range=(0, None), role="Replicate point size"),
    Param("point_alpha", float, 0.6, unit="[0-1] opacity", range=(0, 1), role="Replicate point opacity"),
    Param("point_jitter", float, 0.0, unit="x units (categories are 1 apart)", range=(0, None),
          role="Horizontal scatter of the replicate points"),
    Param("point_seed", int, 0, unit="random seed", role="Seed of the jitter (fixed for reproducible output)"),
    # [Axes]
    Param("x_log", bool, False, role="Log-scaled x axis (numeric x)"),
    Param("x_min", float, None, unit="data coords", role="Lower x limit (both x_min and x_max needed)"),
    Param("x_max", float, None, unit="data coords", role="Upper x limit"),
    Param("y_min", float, None, unit="data coords", role="Lower y limit (both y_min and y_max needed)"),
    Param("y_max", float, None, unit="data coords", role="Upper y limit"),
    Param("zero_line", bool, False, role="Draw y = 0"),
    Param("zero_line_color", "color", "#9ca3af", unit="hex color", role="y = 0 line colour"),
    Param("zero_line_width", float, 0.5, unit="pt", range=(0, None), role="y = 0 line width"),
    Param("grid", bool, False, role="Draw a background grid"),
    Param("grid_alpha", float, 0.3, unit="[0-1] opacity", range=(0, 1), role="Grid opacity"),
    Param("spine_width", float, None, unit="pt", range=(0, None), role="Axis line width (default: rcParams)"),
    Param("hide_top_right", bool, True, role="Hide the top and right axis lines"),
    # [Text and legend]
    Param("labels_title", str, None, role="Panel title"),
    Param("labels_xlabel", str, CODE_DEFAULT, role="x-axis title (default: x_col)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default: y_col)"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Tick label size (default: rcParams)"),
    Param("show_legend", bool, True, role="Show the group legend (only with a group_col)"),
    Param("legend_loc", str, "best", role="Legend location (matplotlib loc)"),
    Param("legend_fontsize", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Legend font size (default: tick_label_size)"),
    Param("legend_frameon", bool, False, role="Draw a frame around the legend"),
])


def summarise(df: pd.DataFrame, x_col: str, y_col: str, group_col: str | None,
              aggregate: str = "mean", error: str = "sem") -> pd.DataFrame:
    """Per (group, x): n, centre and band edges. ``ci95`` is the two-sided
    95% t-interval of the mean (needs n >= 2; NaN otherwise)."""
    from scipy import stats as st
    keys = [group_col, x_col] if group_col else [x_col]
    rows = []
    for key, sub in df.groupby(keys, sort=False, dropna=False):
        v = pd.to_numeric(sub[y_col], errors="coerce").dropna().to_numpy()
        n = int(v.size)
        centre = float(np.median(v)) if aggregate == "median" else (float(v.mean()) if n else np.nan)
        sd = float(v.std(ddof=1)) if n > 1 else np.nan
        half = {"sd": sd, "sem": sd / np.sqrt(n) if n > 1 else np.nan,
                "ci95": float(st.t.ppf(0.975, n - 1)) * sd / np.sqrt(n) if n > 1 else np.nan,
                "none": 0.0}[error]
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(keys, key))
        row.update(n=n, centre=centre, lower=centre - half, upper=centre + half)
        rows.append(row)
    out = pd.DataFrame(rows)
    if not group_col:
        out.insert(0, "group", None)
    else:
        out = out.rename(columns={group_col: "group"})
    return out.rename(columns={x_col: "x"})[["group", "x", "n", "centre", "lower", "upper"]]


@uses_schema(SCHEMA)
def render_line_band(ax, df, params):
    """Draw the lines and bands onto ``ax``; returns the summary drawn."""
    x_col, y_col, g_col = params.get("x_col", "x"), params.get("y_col", "y"), params.get("group_col")
    agg = params.get("aggregate", "mean")
    if agg == "none":
        lo, hi = params.get("lower_col"), params.get("upper_col")
        cols = {x_col: "x", y_col: "centre"}
        if lo and hi:
            cols.update({lo: "lower", hi: "upper"})
        summary = df.rename(columns=cols).copy()
        summary["group"] = df[g_col] if g_col else None
        summary["n"] = np.nan
        for c in ("lower", "upper"):
            if c not in summary:
                summary[c] = summary["centre"]
        summary = summary[["group", "x", "n", "centre", "lower", "upper"]]
    else:
        summary = summarise(df, x_col, y_col, g_col, agg, params.get("error", "sem"))

    x_order = params.get("x_order")
    pos = {v: i for i, v in enumerate(x_order)} if x_order else None
    to_x = (lambda s: s.map(pos).astype(float)) if pos else (lambda s: pd.to_numeric(s, errors="coerce"))

    groups = params.get("group_order") or list(dict.fromkeys(summary["group"]))
    colors, labels = params.get("group_colors", {}), params.get("group_labels", {})
    rng = np.random.default_rng(int(params.get("point_seed", 0)))
    for g in groups:
        s = summary[summary["group"].isna()] if g is None else summary[summary["group"] == g]
        s = s.assign(_x=to_x(s["x"])).dropna(subset=["_x"]).sort_values("_x")
        kw = {"color": colors[g]} if g in colors else {}
        line, = ax.plot(s["_x"], s["centre"], linewidth=float(params.get("line_width", 1.2)),
                        linestyle=params.get("line_style", "-"), marker=params.get("marker", "o") or None,
                        markersize=float(params.get("marker_size", 3.0)),
                        label=str(labels.get(g, g)) if g is not None else None, **kw)
        if params.get("error", "sem") != "none" or agg == "none":
            ax.fill_between(s["_x"], s["lower"], s["upper"], color=line.get_color(),
                            alpha=float(params.get("band_alpha", 0.25)),
                            linewidth=float(params.get("band_edge_width", 0.0)))
        if params.get("show_points", False) and agg != "none":
            raw = df if g is None else df[df[g_col] == g]
            xs = to_x(raw[x_col]).to_numpy(dtype=float)
            jit = float(params.get("point_jitter", 0.0))
            if jit:
                xs = xs + rng.uniform(-jit, jit, xs.size)
            ax.scatter(xs, pd.to_numeric(raw[y_col], errors="coerce"), s=float(params.get("point_size", 8.0)),
                       color=line.get_color(), alpha=float(params.get("point_alpha", 0.6)), edgecolors="none")

    if pos:
        ax.set_xticks(range(len(x_order)))
        ax.set_xticklabels([str(v) for v in x_order])
    elif params.get("x_log", False):
        ax.set_xscale("log")
    if params.get("x_min") is not None and params.get("x_max") is not None:
        ax.set_xlim(float(params.get("x_min")), float(params.get("x_max")))
    if params.get("y_min") is not None and params.get("y_max") is not None:
        ax.set_ylim(float(params.get("y_min")), float(params.get("y_max")))
    if params.get("zero_line", False):
        ax.axhline(0, color=params.get("zero_line_color", "#9ca3af"),
                   linewidth=float(params.get("zero_line_width", 0.5)), zorder=0)
    if params.get("grid", False):
        ax.grid(True, alpha=float(params.get("grid_alpha", 0.3)))
    if params.get("hide_top_right", True):
        ax.spines[["top", "right"]].set_visible(False)
    if params.get("spine_width") is not None:
        for side in ("left", "bottom"):
            ax.spines[side].set_linewidth(float(params.get("spine_width")))

    a_sz = params.get("axes_label_size")
    label_kw = {} if a_sz is None else {"fontsize": a_sz}
    ax.set_xlabel(text_param(params, "labels_xlabel", x_col), **label_kw)
    ax.set_ylabel(text_param(params, "labels_ylabel", y_col), **label_kw)
    title = text_param(params, "labels_title", None)
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0), fontweight="bold")
    tick_sz = params.get("tick_label_size")
    if tick_sz is not None:
        ax.tick_params(labelsize=tick_sz)
    if g_col and params.get("show_legend", True):
        fs = params.get("legend_fontsize", tick_sz)
        ax.legend(loc=params.get("legend_loc", "best"), frameon=bool(params.get("legend_frameon", False)),
                  **({} if fs is None else {"fontsize": fs}))
    return summary
