"""dot_matrix: a grid of rows x columns with one dot per filled cell -- dot
area from a count, colour from a category (e.g. genes x features, coloured by
where the variants come from). Empty cells stay blank, so the grid reads as a
sparse table.

Data: one row per (row, column) cell with the columns named by row_col and
col_col; size_col (a count; absent: every dot one size) and color_col
(a category; absent: one colour). Rows that repeat a cell are added
together. A cell with more than one category takes the first in
``color_order``, or, with ``multi: split``, shows one dot per category side by
side. A ``row_group_col`` draws a thin line between row groups
(e.g. one block of genes per sample). Returns the cells drawn, ready for
fig_atlas.source_data.add.
"""
from __future__ import annotations

import pandas as pd
from matplotlib.lines import Line2D

from ..params import text_param
from ..schema import Param, Schema, typography, uses_schema

SCHEMA = Schema("dot_matrix", params=[
    # [Data]
    Param("row_col", str, "row", role="Column with the row names"),
    Param("col_col", str, "column", role="Column with the column names"),
    Param("size_col", str, None, role="Column with the count that sets dot area (absent: one size)"),
    Param("color_col", str, None, role="Column with the category that sets dot colour (absent: one colour)"),
    Param("row_group_col", str, None, role="Column grouping rows into blocks with a line between them"),
    Param("row_order", list, None, role="Row order, top to bottom (default: order in the data)"),
    Param("col_order", list, None, role="Column order, left to right (default: order in the data)"),
    Param("col_labels", dict, {}, open_keys=True, role="Shown name per column"),
    # [Dots]
    Param("multi", ("first", "split"), "first",
          role="A cell with several categories: one dot coloured by the first in color_order, or one dot per category"),
    Param("split_offset", float, 0.22, unit="column units", range=(0, None),
          role="Distance between the dots of a split cell", tune="raise if they touch"),
    Param("color_order", list, None, role="Category priority and legend order (default: order in the data)"),
    Param("color_map", dict, {}, open_keys=True, unit="hex color", role="Colour per category"),
    Param("color_labels", dict, {}, open_keys=True, role="Legend text per category"),
    Param("default_color", "color", "#4b5563", unit="hex color", role="Dot colour without a category"),
    Param("size_per_unit", float, 12.0, unit="pt^2 per count", range=(0, None), role="Dot area per count"),
    Param("size_min", float, 10.0, unit="pt^2", range=(0, None), role="Smallest dot area"),
    Param("size_max", float, 120.0, unit="pt^2", range=(0, None), role="Largest dot area", tune="lower if dots touch"),
    Param("edge_color", "color", "#ffffff", unit="hex color", role="Dot outline colour"),
    Param("edge_width", float, 0.4, unit="pt", range=(0, None), role="Dot outline width"),
    Param("show_counts", bool, False, role="Write the count beside each dot"),
    Param("count_size", float, 5.0, unit="pt", range=(0, None), role="Size of those counts"),
    Param("count_offset", float, 0.28, unit="column units", role="Horizontal offset of the counts from the dot centre"),
    # [Grid]
    Param("grid", bool, True, role="Draw faint lines through the cells"),
    Param("grid_color", "color", "#e5e7eb", unit="hex color", role="Grid line colour"),
    Param("grid_width", float, 0.4, unit="pt", range=(0, None), role="Grid line width"),
    Param("group_line_color", "color", "#9ca3af", unit="hex color", role="Line between row groups"),
    Param("group_line_width", float, 0.6, unit="pt", range=(0, None), role="Width of that line"),
    Param("row_label_style", str, "normal", role="Font style of the row names (italic for genes)"),
    Param("tick_length", float, 0.0, unit="pt", range=(0, None), role="Tick mark length (0: names only)"),
    Param("x_tick_rotation", float, 0.0, unit="degrees", role="Rotation of the column names"),
    # [Legend and text]
    Param("show_legend", bool, True, role="Show the colour and size legends"),
    Param("legend_anchor", list, [1.02, 1.0], unit="axes fraction [x, y]", role="Upper-left corner of the legend"),
    Param("legend_loc", str, "upper left", role="Legend location (matplotlib loc)"),
    Param("legend_ncol", int, 1, unit="columns", range=(1, None), role="Number of legend columns"),
    Param("legend_frameon", bool, False, role="Draw a frame around the legend"),
    Param("legend_edge_width", float, 0.0, unit="pt", range=(0, None), role="Outline width of the legend dots"),
    Param("size_legend_counts", list, [1, 5], role="Counts shown in the size legend (empty: none)"),
    Param("size_legend_label", str, "{n}", role="Text of each size legend entry ({n}: the count)"),
    Param("labels_title", str, None, role="Panel title"),
    Param("labels_xlabel", str, None, role="x-axis title"),
    Param("labels_ylabel", str, None, role="y-axis title"),
    *typography(title_size=8.0),
    Param("title_pad", float, None, unit="pt", range=(0, None), role="Gap between panel title and plot"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Axis title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Row and column name size (default: rcParams)"),
    Param("legend_fontsize", float, None, unit="pt", range=(0, None), role="Legend text size (default: rcParams)"),
])


@uses_schema(SCHEMA)
def render_dot_matrix(ax, df, params):
    """Draw the dot matrix onto ``ax``; returns the cells drawn."""
    r_col, c_col = params.get("row_col", "row"), params.get("col_col", "column")
    s_col, k_col, g_col = params.get("size_col"), params.get("color_col"), params.get("row_group_col")
    data = df.copy()
    data["_n"] = pd.to_numeric(data[s_col], errors="coerce").fillna(0) if s_col else 1.0
    kinds = params.get("color_order") or (list(dict.fromkeys(data[k_col].dropna())) if k_col else [])
    rank = {k: i for i, k in enumerate(kinds)}
    keys = [r_col, c_col] + ([g_col] if g_col and g_col != r_col else [])
    split = bool(k_col) and params.get("multi", "first") == "split"
    data = data.assign(_rank=data[k_col].map(rank) if k_col else 0).sort_values("_rank", kind="stable")
    if split:
        cells = (data.groupby(keys + [k_col], sort=False).agg(n=("_n", "sum")).reset_index()
                 .rename(columns={k_col: "kind"}))
    else:
        cells = (data.groupby(keys, sort=False)
                 .agg(n=("_n", "sum"), **({"kind": (k_col, "first")} if k_col else {})).reset_index())
    rows = params.get("row_order") or list(dict.fromkeys(data[r_col]))
    cols = params.get("col_order") or list(dict.fromkeys(data[c_col]))
    y = {r: i for i, r in enumerate(rows)}
    x = {c: i for i, c in enumerate(cols)}
    cells = cells[cells[r_col].isin(y) & cells[c_col].isin(x)].copy()
    # Horizontal position: the column, shifted per category when a split cell holds several.
    off = float(params.get("split_offset", 0.22))
    k_in_cell = cells.groupby([r_col, c_col]).cumcount() if split else pd.Series(0, index=cells.index)
    n_in_cell = cells.groupby([r_col, c_col])[r_col].transform("size") if split else pd.Series(1, index=cells.index)
    cells["x"] = cells[c_col].map(x) + (k_in_cell - (n_in_cell - 1) / 2) * off

    if params.get("grid", True):
        gc, gw = params.get("grid_color", "#e5e7eb"), float(params.get("grid_width", 0.4))
        for i in range(len(rows)):
            ax.axhline(i, color=gc, linewidth=gw, zorder=0)
        for j in range(len(cols)):
            ax.axvline(j, color=gc, linewidth=gw, zorder=0)
    if g_col:
        groups = data.drop_duplicates(r_col).set_index(r_col)[g_col].reindex(rows)
        for i in range(1, len(rows)):
            if groups.iloc[i] != groups.iloc[i - 1]:
                ax.axhline(i - 0.5, color=params.get("group_line_color", "#9ca3af"),
                           linewidth=float(params.get("group_line_width", 0.6)), zorder=0)

    per, lo, hi = (float(params.get(k, d)) for k, d in (("size_per_unit", 12.0), ("size_min", 10.0), ("size_max", 120.0)))
    area = lambda n: min(max(n * per, lo), hi)                                    # noqa: E731
    cmap = params.get("color_map", {})
    colors = [cmap.get(k, params.get("default_color", "#4b5563")) for k in cells["kind"]] if k_col else \
        params.get("default_color", "#4b5563")
    ax.scatter(cells["x"], cells[r_col].map(y), s=[area(n) for n in cells["n"]], c=colors,
               edgecolors=params.get("edge_color", "#ffffff"), linewidths=float(params.get("edge_width", 0.4)),
               zorder=3)
    tick_sz = params.get("tick_label_size")
    if params.get("show_counts", False):
        for _, c in cells.iterrows():
            ax.text(c["x"] + float(params.get("count_offset", 0.28)), y[c[r_col]], f"{c['n']:g}",
                    ha="left", va="center", fontsize=float(params.get("count_size", 5.0)))

    ax.set_xlim(-0.5, len(cols) - 0.5)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    names = params.get("col_labels", {})
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([str(names.get(c, c)) for c in cols], rotation=float(params.get("x_tick_rotation", 0.0)),
                       ha="right" if params.get("x_tick_rotation", 0.0) else "center")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([str(r) for r in rows], style=params.get("row_label_style", "normal"))
    ax.tick_params(length=float(params.get("tick_length", 0.0)), **({} if tick_sz is None else {"labelsize": tick_sz}))
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    if params.get("show_legend", True):
        fs = params.get("legend_fontsize")
        handles = [Line2D([], [], linestyle="none", marker="o", markersize=area(1) ** 0.5,
                          markerfacecolor=cmap.get(k, params.get("default_color", "#4b5563")),
                          markeredgewidth=float(params.get("legend_edge_width", 0.0)), label=params.get("color_labels", {}).get(k, k))
                   for k in kinds if k in set(cells.get("kind", []))]
        for n in params.get("size_legend_counts", [1, 5]):
            handles.append(Line2D([], [], linestyle="none", marker="o", markersize=area(n) ** 0.5,
                                  markerfacecolor=params.get("default_color", "#4b5563"),
                                  markeredgewidth=float(params.get("legend_edge_width", 0.0)),
                                  label=params.get("size_legend_label", "{n}").format(n=n)))
        if handles:
            ax.legend(handles=handles, loc=params.get("legend_loc", "upper left"),
                      bbox_to_anchor=tuple(params.get("legend_anchor", [1.02, 1.0])),
                      ncol=int(params.get("legend_ncol", 1)),
                      frameon=params.get("legend_frameon", False),
                      **({} if fs is None else {"fontsize": fs}))
    a_sz = params.get("axes_label_size")
    for setter, key in ((ax.set_xlabel, "labels_xlabel"), (ax.set_ylabel, "labels_ylabel")):
        text = text_param(params, key, None)
        if text:
            setter(text, **({} if a_sz is None else {"fontsize": a_sz}))
    title = text_param(params, "labels_title", None)
    if title:
        pad = params.get("title_pad")
        ax.set_title(title, fontsize=params.get("title_size", 8.0),
                     **({} if pad is None else {"pad": float(pad)}))
    return cells
