"""Effect estimates with confidence intervals: one row per item, one dot +
whisker per series (e.g. unadjusted vs adjusted), dodged vertically. Styling
from ``params``.

Colours come from the series (``color_by: series``), or, with ``color_by:
threshold``, from each estimate's direction and a significance column: up
(``sig_col`` <= ``sig_threshold`` and estimate > 0), down (significant and
< 0) or not significant -- e.g. log2 fold changes coloured by adjusted P."""
from __future__ import annotations

import pandas as pd


from ..schema import Param, Schema, uses_schema
from ._basic import with_roles

SCHEMA = Schema("effect_dots", params=[
    # [Rows and series]
    Param("item_col", str, "item", role="Column with the row names (what each estimate is about)"),
    Param("series_col", str, "series", role="Column with the series (e.g. unadjusted / adjusted; absent: one)"),
    Param("estimate_col", str, "estimate", role="Column with the estimate (dot)"),
    Param("low_col", str, "ci_low", role="Column with the lower confidence limit"),
    Param("high_col", str, "ci_high", role="Column with the upper confidence limit"),
    Param("item_order", list, None, role="Row order, top to bottom (default: order in the data)"),
    Param("item_sort", ("data", "estimate_desc", "estimate_asc"), "data",
          role="Row order when item_order is unset: as in the data, or by the (first series') estimate, "
               "largest on top (estimate_desc) or smallest on top"),
    Param("item_labels", dict, {}, open_keys=True, role="Display label per item"),
    Param("series_order", list, None, role="Series order (default: order in the data)"),
    Param("series_colors", dict, {}, open_keys=True, role="Colour per series"),
    Param("series_labels", dict, {}, open_keys=True, role="Legend label per series"),
    Param("dodge", float, 0.18, unit="row units", range=(0, None), role="Vertical offset between series within a row",
          tune="raise if the series' intervals overlap"),
    # [Colour by significance]
    Param("color_by", ("series", "threshold"), "series",
          role="Colour each series (series_colors), or each estimate by direction and significance (threshold)"),
    Param("sig_col", str, None, role="threshold: column with the significance value (smaller = stronger, e.g. padj)"),
    Param("sig_threshold", float, 0.05, unit="significance units", range=(0, None),
          role="threshold: estimates with sig_col at or below this are up / down"),
    Param("up_color", "color", "#D55E00", unit="hex color", role="threshold: colour of significant positive estimates"),
    Param("down_color", "color", "#0072B2", unit="hex color", role="threshold: colour of significant negative estimates"),
    Param("ns_color", "color", "#9CA3AF", unit="hex color", role="threshold: colour of the others"),
    Param("class_labels", dict, {"up": "Up", "down": "Down", "ns": "n.s."}, open_keys=True,
          role="threshold: legend label per class (keys up, down, ns)"),
    # [Marks]
    Param("marker_size", float, 16, unit="pt^2 (marker area)", range=(0, None), role="Point estimate marker size"),
    Param("ci_width", float, 0.8, unit="pt", range=(0, None), role="Confidence interval line width"),
    Param("zero_line", bool, True, role="Draw the no-effect line at x = 0"),
    Param("zero_line_color", "color", "#6b7280", unit="hex color", role="No-effect line colour"),
    Param("zero_line_width", float, 0.5, unit="pt", range=(0, None), role="No-effect line width"),
    Param("zero_line_style", str, "-", unit="matplotlib line style", role="No-effect line style ('-', '--', ':')"),
    Param("xlim", list, None, unit="data coords [min, max]", role="x-axis range (default: data)"),
    Param("spine_width", float, 0.6, unit="pt", range=(0, None), role="Axis spine width"),
    # [Legend]
    Param("legend", bool, True, role="Show the series legend"),
    Param("legend_loc", str, "lower right", role="Legend location (matplotlib loc string)"),
    Param("legend_anchor", list, None, unit="axes fraction (x, y)", role="bbox_to_anchor for the legend"),
    Param("legend_ncol", int, 1, unit="columns", range=(1, None), role="Legend columns"),
    Param("legend_fontsize", float, 5.0, unit="pt", range=(0, None), role="Legend font size"),
    # [Labels]
    Param("title", str, None, role="Panel title"),
    Param("xlabel", str, None, role="x-axis title"),
    Param("title_pad", float, 3.0, unit="pt", range=(0, None), role="Gap between title and axes"),
    Param("title_size", float, 6.5, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 6.0, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 5.5, unit="pt", range=(0, None), role="Tick and row label font size"),
])


@uses_schema(SCHEMA)
def render_effect_dots(ax, df: pd.DataFrame, params: dict):
    """``df`` columns: item, series, estimate, ci_low, ci_high.

    params: item_order, item_labels, series_order, series_colors, series_labels,
      dodge (0.18: vertical offset between series, row units), marker_size (16),
      ci_width (0.8), zero_line (True), zero_line_color ('#6b7280'), zero_line_width (0.5),
      xlabel, xlim, axes_label_size (6.0), tick_label_size (5.5),
      legend (True), legend_fontsize (5.0), legend_loc ('lower right'), legend_anchor (None:
      axes-fraction anchor for legend_loc), legend_ncol (1),
      title, title_size (6.5), title_pad (3.0), spine_width (0.6)
    """
    df = with_roles(df, params, {"item_col": ("item", "item"), "series_col": ("series", "series"),
                                 "estimate_col": ("estimate", "estimate"), "low_col": ("ci_low", "ci_low"),
                                 "high_col": ("ci_high", "ci_high"), "sig_col": (None, "sig")},
                    fill={"series": "estimate"})
    series = params.get("series_order") or list(pd.unique(df["series"]))
    items = params.get("item_order") or list(pd.unique(df["item"]))
    sort = params.get("item_sort", "data")
    if not params.get("item_order") and sort != "data":
        first = df[df["series"] == series[0]].set_index("item")["estimate"]
        items = sorted(items, key=lambda i: first.get(i, float("nan")), reverse=(sort == "estimate_desc"))
    colors, s_lab = params.get("series_colors", {}), params.get("series_labels", {})
    dodge = float(params.get("dodge", 0.18))
    if params.get("zero_line", True):
        ax.axvline(0, color=params.get("zero_line_color", "#6b7280"), lw=float(params.get("zero_line_width", 0.5)),
                   ls=params.get("zero_line_style", "-"), zorder=1)
    by_threshold = params.get("color_by", "series") == "threshold"
    if by_threshold and "sig" not in df.columns:
        raise ValueError("effect_dots: color_by threshold needs sig_col, a column of the data "
                         f"(got {params.get('sig_col')!r})")
    labels_by_class = {"up": "Up", "down": "Down", "ns": "n.s.",
                       **(params.get("class_labels", {"up": "Up", "down": "Down", "ns": "n.s."}) or {})}
    class_colors = {"up": params.get("up_color", "#D55E00"), "down": params.get("down_color", "#0072B2"),
                    "ns": params.get("ns_color", "#9CA3AF")}
    for si, s in enumerate(series):
        off = (si - (len(series) - 1) / 2) * dodge
        d = df[df["series"] == s].set_index("item").reindex(items)
        ys = pd.Series([i + off for i in range(len(items))], index=d.index)
        if by_threshold:
            sig = pd.to_numeric(d["sig"], errors="coerce") <= float(params.get("sig_threshold", 0.05))
            cls = pd.Series("ns", index=d.index).mask(sig & (d["estimate"] > 0), "up").mask(sig & (d["estimate"] < 0), "down")
            groups = [(k, cls == k, class_colors[k], labels_by_class[k]) for k in ("up", "down", "ns") if (cls == k).any()]
        else:
            groups = [(s, slice(None), colors.get(s, "#374151"), s_lab.get(s, s))]
        for _, m, c, label in groups:
            ax.hlines(ys[m], d["ci_low"][m], d["ci_high"][m], color=c, lw=float(params.get("ci_width", 0.8)), zorder=2)
            ax.scatter(d["estimate"][m], ys[m], s=float(params.get("marker_size", 16)), color=c, zorder=3, label=label)
    lab = params.get("item_labels", {})
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([lab.get(i, i) for i in items], fontsize=float(params.get("tick_label_size", 5.5)))
    ax.invert_yaxis()
    if params.get("xlim") is not None:
        ax.set_xlim(*params["xlim"])
    if params.get("xlabel"):
        ax.set_xlabel(params["xlabel"], fontsize=float(params.get("axes_label_size", 6.0)))
    ax.tick_params(axis="x", labelsize=float(params.get("tick_label_size", 5.5)), length=2)
    ax.tick_params(axis="y", length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(float(params.get("spine_width", 0.6)))
    if params.get("legend", True):
        anchor = params.get("legend_anchor")
        ax.legend(fontsize=float(params.get("legend_fontsize", 5.0)), loc=params.get("legend_loc", "lower right"),
                  bbox_to_anchor=tuple(anchor) if anchor else None, ncol=int(params.get("legend_ncol", 1)),
                  frameon=False, handletextpad=0.2)
    if params.get("title"):
        ax.set_title(params["title"], fontsize=float(params.get("title_size", 6.5)), fontweight="bold",
                     pad=float(params.get("title_pad", 3.0)))
    return ax
