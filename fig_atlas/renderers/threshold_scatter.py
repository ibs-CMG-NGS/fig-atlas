"""Threshold scatter: points classed up / down / not significant by an effect
size and a significance value, with cut-off lines and optional point labels
(roadmap 6a.3, a domain-neutral renderer).

Every point has an effect (signed; its sign gives the direction) and a
significance value (smaller = stronger). A point is "up" when effect >=
effect_threshold and significance <= sig_threshold, "down" when effect <=
-effect_threshold and significance <= sig_threshold, otherwise "ns". Which
columns are x and y, and how they are transformed, is configuration: a
volcano plot is x = effect, y = -log10(significance); an MA plot is
x = log10(mean), y = effect; an effect size vs P plot from any field is the
same renderer. Domain packs ship such set-ups as recipes (fig_atlas.recipes).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..params import text_param
from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("threshold_scatter", params=[
    # [Data: column roles and transforms]
    Param("x_col", str, None, role="Column plotted on x"),
    Param("y_col", str, None, role="Column plotted on y"),
    Param("effect_col", str, None, role="Signed effect column; its sign gives up / down"),
    Param("sig_col", str, None, role="Significance column (smaller = stronger, e.g. an adjusted P)"),
    Param("x_transform", ("none", "log10", "neg_log10"), "none", role="Transform of x before plotting"),
    Param("y_transform", ("none", "log10", "neg_log10"), "none", role="Transform of y before plotting"),
    Param("empty_is_missing", bool, False, role="Show the missing-data message for an empty table too"),
    Param("missing_text", str, "Required columns not found", role="Message drawn when the columns are missing"),
    Param("missing_text_size", float, None, unit="pt", range=(0, None),
          role="Size of the missing-data message (default: title_size)"),
    # [Classes]
    Param("effect_threshold", float, 1.0, unit="effect units", range=(0, None),
          role="|effect| cut-off for up / down points", tune="raise to call only stronger effects"),
    Param("sig_threshold", float, 0.05, unit="significance units", range=(0, None),
          role="Significance cut-off for up / down points"),
    Param("up_color", "color", "#ff0000", unit="hex color", role="Colour of up points"),
    Param("down_color", "color", "#0000ff", unit="hex color", role="Colour of down points"),
    Param("ns_color", "color", "#808080", unit="hex color", role="Colour of non-significant points"),
    Param("dot_size", float, 20, unit="pt^2 (marker area)", range=(0, None), role="Point size", tune="lower for dense plots"),
    Param("ns_alpha", float, 0.6, unit="[0-1] opacity", range=(0, 1), role="Opacity of non-significant points"),
    Param("sig_alpha", float, 0.6, unit="[0-1] opacity", range=(0, 1), role="Opacity of up / down points"),
    Param("ns_zorder", float, None, unit="matplotlib zorder", role="Drawing order of the ns points (default: matplotlib's)"),
    Param("sig_zorder", float, None, unit="matplotlib zorder", role="Drawing order of the up / down points"),
    # [Cut-off lines]
    Param("show_cutoff_lines", bool, True, role="Draw the cut-off lines"),
    Param("cutoff_lines", list, None,
          role="Lines to draw: list of {axis: h|v, at: effect|-effect|sig|<number>, "
               "width_scale, alpha_scale, style}; 'sig' is the transformed significance cut-off"),
    Param("cutoff_line_color", "color", "black", unit="color", role="Cut-off line colour"),
    Param("cutoff_line_style", str, "--", role="Cut-off line style (matplotlib)"),
    Param("cutoff_line_width", float, 1, unit="pt", range=(0, None), role="Cut-off line width"),
    Param("cutoff_line_alpha", float, 0.5, unit="[0-1] opacity", range=(0, 1), role="Cut-off line opacity"),
    # [Point labels]
    Param("label_mode", ("none", "top_n", "custom"), "none",
          role="Label points: none, the top_n strongest (|effect| x -log10 significance), or label_custom"),
    Param("label_cols", list, ["nearest_gene", "gene_name", "symbol", "gene_id"],
          role="Candidate label columns; the first present is used"),
    Param("label_top_n", int, 10, unit="points", range=(0, None), role="Points labelled in top_n mode"),
    Param("label_custom", list, None, role="Labels to show in custom mode (matched case-insensitively)"),
    Param("label_size", float, 8, unit="pt", range=(0, None), role="Point label size"),
    Param("label_color", "color", "black", unit="color", role="Point label colour"),
    Param("label_box_alpha", float, 0.7, unit="[0-1] opacity", range=(0, 1), role="Opacity of the box behind labels"),
    Param("label_arrow_color", "color", "grey", unit="color", role="Colour of the label leader lines"),
    Param("label_arrow_width", float, 0.5, unit="pt", range=(0, None), role="Width of the label leader lines"),
    Param("label_expand", list, [1.15, 1.4], unit="multiple of the label box (x, y)",
          role="Room adjustText keeps around each label", tune="raise if labels still touch"),
    Param("label_force", list, [0.4, 0.6], unit="adjustText force (x, y)", role="How hard labels push apart"),
    Param("label_iter_lim", int, 1000, unit="iterations", range=(1, None),
          role="Label-placement steps (a fixed count, so every build places the labels the same way)",
          tune="raise if labels still overlap; lower for a faster build"),
    # [Axes and text]
    Param("x_min", float, None, unit="data coords (after transform)", role="Lower x limit (both x_min and x_max needed)"),
    Param("x_max", float, None, unit="data coords (after transform)", role="Upper x limit"),
    Param("y_min", float, None, unit="data coords (after transform)", role="Lower y limit (both y_min and y_max needed)"),
    Param("y_max", float, None, unit="data coords (after transform)", role="Upper y limit"),
    Param("grid", bool, False, role="Draw a background grid"),
    Param("grid_alpha", float, 0.3, unit="[0-1] opacity", range=(0, 1), role="Grid opacity"),
    Param("labels_title", str, None, role="Panel title"),
    Param("labels_xlabel", str, CODE_DEFAULT, role="x-axis title (default: the x column name)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default: the y column name)"),
    Param("title_size", float, 10, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Tick label size (default: rcParams)"),
    Param("show_xticklabels", bool, True, role="Show x tick labels"),
    Param("show_yticklabels", bool, True, role="Show y tick labels"),
    Param("show_legend", bool, True, role="Show the up / down / ns legend with counts"),
    Param("legend_position", str, "best", role="Legend anchor (matplotlib loc, or 'outside right')"),
    Param("legend_fontsize", str, CODE_DEFAULT, unit="pt or matplotlib size name",
          role="Legend font size (default: tick_label_size, else 'small')"),
    Param("legend_framealpha", float, None, unit="[0-1] opacity", range=(0, 1), role="Legend frame opacity (default: rcParams)"),
    # [Fit the axes to its column]
    Param("fit_axes_width", bool, False,
          role="Widen the axes to fill its column, keeping room for the y tick labels"),
    Param("fit_pad_in", float, 0.3, unit="inches", range=(0, None), role="Room left of the y tick labels when fitting"),
    Param("fit_left_min", float, 0.09, unit="fraction of the column", range=(0, 1), role="Smallest left margin when fitting"),
    Param("fit_left_max", float, 0.30, unit="fraction of the column", range=(0, 1), role="Largest left margin when fitting"),
    Param("fit_right", float, 0.98, unit="fraction of the column", range=(0, 1), role="Right edge of the axes when fitting"),
])

_CLASSES = ("ns", "down", "up")


def _transform(values: pd.Series, how: str) -> pd.Series:
    if how == "neg_log10":
        return -np.log10(values.replace(0, 1e-300))
    if how == "log10":
        return np.log10(values.clip(lower=1e-6))
    return values


def _cutoff_position(at, params, effect_thr: float, sig_thr: float, axis: str):
    if at == "effect":
        return effect_thr
    if at == "-effect":
        return -effect_thr
    if at == "sig":
        how = params.get("y_transform", "none") if axis == "h" else params.get("x_transform", "none")
        return float(_transform(pd.Series([sig_thr]), how).iloc[0])
    return float(at)


def _draw_labels(ax, df, xs, ys, regulation, effect, sig, params):
    mode = params.get("label_mode", "none")
    if mode in (None, "", "none"):
        return
    col = next((c for c in params.get("label_cols", ["nearest_gene", "gene_name", "symbol", "gene_id"])
                if c in df.columns), None)
    if col is None:
        return
    if mode == "top_n":
        mask = regulation.isin(["up", "down"])
        if not mask.any():
            return
        score = effect[mask].abs() * _transform(sig[mask], "neg_log10")
        idx = score.nlargest(int(params.get("label_top_n", 10))).index
    else:
        custom = params.get("label_custom") or []
        if isinstance(custom, str):
            import ast
            try:
                custom = ast.literal_eval(custom)
            except Exception:
                custom = []
        if not custom:
            return
        wanted = {str(g).upper() for g in custom}
        idx = df.index[df[col].astype(str).str.upper().isin(wanted)]
        if len(idx) == 0:
            return
    texts = [ax.text(xs[i], ys[i], str(df.at[i, col]),
                     fontsize=int(params.get("label_size", 8)), fontweight="bold",
                     color=params.get("label_color", "black"), ha="center", va="center",
                     bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                               alpha=float(params.get("label_box_alpha", 0.7))),
                     zorder=500)
             for i in idx]
    if not texts:
        return
    try:
        from adjustText import adjust_text
    except ImportError:
        return
    adjust_text(
        texts, ax=ax,
        arrowprops=dict(arrowstyle="-", color=params.get("label_arrow_color", "grey"),
                        lw=float(params.get("label_arrow_width", 0.5))),
        expand=tuple(params.get("label_expand", [1.15, 1.4])),
        force_text=tuple(params.get("label_force", [0.4, 0.6])),
        only_move={"text": "xy"}, max_move=None,
        # A step count, not adjustText's default 1-second time limit, so the
        # result does not depend on machine speed or load.
        iter_lim=int(params.get("label_iter_lim", 1000)),
    )


def _fit_width(ax, params):
    """Widen the axes to fill its column; the left margin comes from the
    rendered y tick labels (short numbers), not a guess."""
    root_fig = getattr(ax.figure, "figure", ax.figure)
    renderer = root_fig.canvas.get_renderer()
    label_px = max((t.get_window_extent(renderer=renderer).width for t in ax.get_yticklabels()), default=0)
    pos = ax.get_position()
    panel_px = pos.width * ax.figure.bbox.width
    needed = ((label_px + float(params.get("fit_pad_in", 0.3)) * root_fig.dpi) / panel_px
              if panel_px > 0 else 0.15)
    left = min(float(params.get("fit_left_max", 0.30)), max(float(params.get("fit_left_min", 0.09)), needed))
    ax.set_position([left, pos.y0, float(params.get("fit_right", 0.98)) - left, pos.height])


@uses_schema(SCHEMA)
def render_threshold_scatter(ax, df, params):
    """Draw the threshold scatter onto ``ax``; returns the table with a
    ``regulation`` column (up / down / ns), or None when columns are missing."""
    cols = [params.get(k) for k in ("x_col", "y_col", "effect_col", "sig_col")]
    empty = df is None or (params.get("empty_is_missing", False) and df.empty)
    if empty or any(c is None or c not in df.columns for c in cols):
        size = params.get("missing_text_size")
        ax.text(0.5, 0.5, params.get("missing_text", "Required columns not found"), ha="center", va="center",
                fontsize=float(size) if size is not None else params.get("title_size", 10), transform=ax.transAxes)
        return None
    df = df.copy()
    x_col, y_col, effect_col, sig_col = cols
    effect = pd.to_numeric(df[effect_col], errors="coerce")
    sig = pd.to_numeric(df[sig_col], errors="coerce")
    xs = _transform(pd.to_numeric(df[x_col], errors="coerce"), params.get("x_transform", "none"))
    ys = _transform(pd.to_numeric(df[y_col], errors="coerce"), params.get("y_transform", "none"))

    effect_thr = float(params.get("effect_threshold", 1.0))
    sig_thr = float(params.get("sig_threshold", 0.05))
    regulation = pd.Series("ns", index=df.index)
    regulation[(effect >= effect_thr) & (sig <= sig_thr)] = "up"
    regulation[(effect <= -effect_thr) & (sig <= sig_thr)] = "down"
    df["regulation"] = regulation

    colors = {"up": params.get("up_color", "#ff0000"), "down": params.get("down_color", "#0000ff"),
              "ns": params.get("ns_color", "#808080")}
    for cat in _CLASSES:
        mask = regulation == cat
        kw = {}
        z = params.get("ns_zorder") if cat == "ns" else params.get("sig_zorder")
        if z is not None:
            kw["zorder"] = float(z)
        alpha = params.get("ns_alpha", 0.6) if cat == "ns" else params.get("sig_alpha", 0.6)
        ax.scatter(xs[mask], ys[mask], c=colors[cat], s=float(params.get("dot_size", 20)), alpha=float(alpha),
                   label=f"{cat.upper()} ({int(mask.sum())})", edgecolors="none", **kw)

    if params.get("show_cutoff_lines", True):
        width = float(params.get("cutoff_line_width", 1))
        alpha = float(params.get("cutoff_line_alpha", 0.5))
        for line in params.get("cutoff_lines") or []:
            axis = line.get("axis", "h")
            at = _cutoff_position(line.get("at", 0), params, effect_thr, sig_thr, axis)
            kw = dict(color=params.get("cutoff_line_color", "black"),
                      linestyle=line.get("style") or params.get("cutoff_line_style", "--"),
                      linewidth=width * float(line.get("width_scale", 1)),
                      alpha=alpha * float(line.get("alpha_scale", 1)))
            (ax.axhline if axis == "h" else ax.axvline)(at, **kw)

    xmin, xmax = params.get("x_min"), params.get("x_max")
    if xmin is not None and xmax is not None:
        ax.set_xlim(float(xmin), float(xmax))
    ymin, ymax = params.get("y_min"), params.get("y_max")
    if ymin is not None and ymax is not None:
        ax.set_ylim(float(ymin), float(ymax))
    if params.get("grid", False):
        ax.grid(True, alpha=float(params.get("grid_alpha", 0.3)))

    _draw_labels(ax, df, xs, ys, regulation, effect, sig, params)

    a_sz = params.get("axes_label_size")
    label_kw = {} if a_sz is None else {"fontsize": a_sz}
    ax.set_xlabel(text_param(params, "labels_xlabel", x_col), **label_kw)
    ax.set_ylabel(text_param(params, "labels_ylabel", y_col), **label_kw)
    title = text_param(params, "labels_title", None)
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 10), fontweight="bold")
    tick_sz = params.get("tick_label_size")
    if tick_sz is not None:
        ax.tick_params(labelsize=tick_sz)
    if not params.get("show_xticklabels", True):
        ax.tick_params(axis="x", labelbottom=False)
    if not params.get("show_yticklabels", True):
        ax.tick_params(axis="y", labelleft=False)
    if params.get("show_legend", True):
        fs = params.get("legend_fontsize", tick_sz if tick_sz is not None else "small")
        leg_kw = {"fontsize": fs}
        if params.get("legend_framealpha") is not None:
            leg_kw["framealpha"] = float(params.get("legend_framealpha"))
        loc = params.get("legend_position", "best")
        if loc == "outside right":
            ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), **leg_kw)
        else:
            ax.legend(loc=loc, **leg_kw)

    if params.get("fit_axes_width", False):
        _fit_width(ax, params)
    return df
