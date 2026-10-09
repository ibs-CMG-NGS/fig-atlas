"""DE/DA count-summary diverging bar chart, ported from count_summary_bundle.

render_count_summary mirrors the cmg-seqviewer inline renderer 1:1: input is
long-format per-gene rows (dataset/log2fc/adj_pvalue), classified and counted
here from fdr_max/lfc_min. One bar per dataset, UP rising above zero and DOWN
dropping below it (not grouped side-by-side).
"""

from __future__ import annotations

import ast

import pandas as pd
from matplotlib.ticker import FuncFormatter

from fig_atlas.params import text_param


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("count_summary", params=[
    # [Counting]
    Param("fdr_max", float, 0.05, unit="FDR", range=(0, 1), role="Only rows with FDR at or below this are counted"),
    Param("lfc_min", float, 0.585, unit="|log2FC|", range=(0, None), role="Only rows with |log2FC| at or above this are counted"),
    Param("as_pct", bool, False, role="Show each dataset's counts as a percentage of its rows"),
    Param("unit", str, "genes", role="Noun used in the default axis title and title"),
    Param("order", list, None, role="Dataset order, left to right (default: order in the data)"),
    Param("label_rename_map", dict, {}, open_keys=True, role="Display label per dataset"),
    # [Bars]
    Param("up_color", "color", "#c0392b", unit="hex color", role="Colour of the up bars (above zero)"),
    Param("down_color", "color", "#2c6fbb", unit="hex color", role="Colour of the down bars (below zero)"),
    Param("zero_line_color", "color", "#333333", unit="hex color", role="Zero line colour"),
    Param("zero_line_width", float, 0.8, unit="pt", range=(0, None), role="Zero line width"),
    Param("show_value_labels", bool, True, role="Print the count on each bar"),
    Param("value_label_fontsize", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Count label size (default tick_label_size)"),
    # [Legend and labels]
    Param("show_legend", bool, True, role="Show the up/down legend"),
    Param("legend_loc", str, "upper right", role="Legend location (matplotlib loc string)"),
    Param("labels_title", str, CODE_DEFAULT, role="Panel title (default names the cutoffs)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default 'Number of <unit>' or '% of <unit>')"),
    Param("xtick_rotation", float, 30, unit="degrees", role="Dataset label rotation"),
    Param("title_size", float, 13, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", range=(0, None), role="Tick label font size"),
])


def _as_list(v):
    if isinstance(v, str):
        try:
            return list(ast.literal_eval(v))
        except Exception:
            return []
    return list(v) if v else []


@uses_schema(SCHEMA)
def render_count_summary(ax, df, params):
    """Draw a zero-baseline diverging UP/DOWN count bar chart onto ``ax``.

    params: fdr_max, lfc_min, as_pct(bool), unit(str, e.g. 'genes'),
            order (list of dataset labels; MUST match the raw `dataset`
            column values exactly since it's used to filter rows, not just
            display -- default = first-seen order), label_rename_map (dict
            mapping an `order` value to what's actually shown on the x-axis,
            for display text that doesn't need to match the raw data),
            up_color, down_color, zero_line_color, zero_line_width,
            xtick_rotation, show_value_labels, value_label_fontsize,
            show_legend, legend_loc, labels_title, labels_ylabel,
            axes_label_size, tick_label_size, title_size
    """
    a_sz = params.get("axes_label_size", 11)
    title_sz = params.get("title_size", 13)
    tick_sz = params.get("tick_label_size", 8)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or "dataset" not in df.columns:
        ax.text(0.5, 0.5, "No datasets to plot.", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes, color="#888888")
        return pd.DataFrame()

    fdr_max = float(params.get("fdr_max", 0.05))
    lfc_min = float(params.get("lfc_min", 0.585))
    as_pct = bool(params.get("as_pct", False))
    unit = params.get("unit", "genes")
    up_color = params.get("up_color", "#c0392b")
    down_color = params.get("down_color", "#2c6fbb")

    order = _as_list(params.get("order")) or list(pd.unique(df["dataset"]))
    lfc = pd.to_numeric(df.get("log2fc"), errors="coerce")
    padj = pd.to_numeric(df.get("adj_pvalue"), errors="coerce")
    df = df.assign(_lfc=lfc, _padj=padj)

    rows = []
    for label in order:
        sub = df[df["dataset"] == label]
        total = int(sub["_lfc"].notna().sum())
        sig = sub[(sub["_padj"] <= fdr_max) & (sub["_lfc"].abs() >= lfc_min)]
        up = int((sig["_lfc"] > 0).sum())
        down = int((sig["_lfc"] < 0).sum())
        rows.append({"label": label, "up": up, "down": down, "total": total})
    counts = pd.DataFrame(rows)
    if counts.empty:
        ax.text(0.5, 0.5, "No datasets to plot.", ha="center", va="center",
                fontsize=title_sz, transform=ax.transAxes, color="#888888")
        return counts

    ups = counts["up"].astype(float).tolist()
    downs = counts["down"].astype(float).tolist()
    if as_pct:
        totals = [t if t else 1 for t in counts["total"].tolist()]
        ups = [100.0 * u / t for u, t in zip(ups, totals)]
        downs = [100.0 * d / t for d, t in zip(downs, totals)]

    x = list(range(len(counts)))
    ax.bar(x, ups, color=up_color, label="Up-regulated")
    ax.bar(x, [-d for d in downs], color=down_color, label="Down-regulated")
    ax.axhline(0, color=params.get("zero_line_color", "#333333"),
              linewidth=float(params.get("zero_line_width", 0.8)))

    if params.get("show_value_labels", True):
        fs = params.get("value_label_fontsize", tick_sz)
        for xi, yu, n in zip(x, ups, counts["up"].tolist()):
            if n > 0:
                ax.text(xi, yu, f"{n:,}", ha="center", va="bottom", fontsize=fs)
        for xi, yd, n in zip(x, downs, counts["down"].tolist()):
            if n > 0:
                ax.text(xi, -yd, f"{n:,}", ha="center", va="top", fontsize=fs)

    rename_map = params.get("label_rename_map", {})
    tick_labels = [rename_map.get(l, l) for l in counts["label"].tolist()]
    rotation = float(params.get("xtick_rotation", 30))
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, rotation=rotation, ha="right", fontsize=tick_sz)
    ax.tick_params(axis="y", labelsize=tick_sz)

    if as_pct:
        ax.set_ylabel(text_param(params, "labels_ylabel", f"% of {unit}"),
                      fontsize=a_sz, fontweight="bold")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{abs(v):.0f}"))
    else:
        ax.set_ylabel(text_param(params, "labels_ylabel", f"Number of {unit}"),
                      fontsize=a_sz, fontweight="bold")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{abs(int(v)):,}"))

    default_title = f"Significant {unit} (FDR ≤ {fdr_max:g}, |log2FC| ≥ {lfc_min:g})"
    title = text_param(params, "labels_title", default_title)
    ax.set_title(title, fontsize=title_sz, fontweight="bold")

    if params.get("show_legend", True):
        ax.legend(loc=params.get("legend_loc", "upper right"), fontsize=tick_sz, frameon=False)

    ax.margins(y=0.15)
    return counts
