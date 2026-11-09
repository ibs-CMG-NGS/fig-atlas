"""upset: the intersections of several sets as bars above a membership grid.

A Venn diagram stops being readable at four sets; this shape stays readable:
one bar per intersection that actually occurs (largest first), and below it one
row per set with a filled dot where the set belongs to that intersection. It
reads a long membership table -- one row per (set, item) -- and counts the
intersections itself, so the input needs no pre-computed combination column.

Data: ``dataset_col`` (the set) and ``item_col`` (the member); an item that is
in no set is not listed. Returns one row per drawn intersection with ``sets``
(joined by " & ") and ``count``, ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

FAMILY = "parts_of_whole"    # gallery family (fig_atlas/family.py): the shape this module draws

import pandas as pd

from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("upset", params=[
    # [Data]
    Param("dataset_col", str, "dataset", role="Column with the set name"),
    Param("item_col", str, "item", role="Column with the item (member) name"),
    Param("set_order", list, None, role="Set order, top to bottom in the membership grid (default: order in the data)"),
    Param("min_size", int, 1, unit="items", range=(1, None), role="Intersections smaller than this are left out"),
    Param("max_columns", int, 40, unit="intersections", range=(1, None), role="Largest number of intersections shown"),
    Param("sort_by", ("size", "degree"), "size",
          role="Intersection order: by size, or by the number of sets (then size)"),
    # [Bars]
    Param("bar_color", "color", "#4b5563", unit="hex color", role="Intersection bar colour"),
    Param("bar_width", float, 0.7, unit="column units", range=(0, 1), role="Bar width"),
    Param("show_counts", bool, True, role="Write the intersection size above its bar"),
    Param("count_size", float, 5.0, unit="pt", range=(0, None), role="Size of those counts"),
    # [Membership grid]
    Param("dot_size", float, 12.0, unit="pt^2 (marker area)", range=(0, None), role="Dot area where a set is in the intersection"),
    Param("dot_color", "color", "#111827", unit="hex color", role="Colour of those dots"),
    Param("inactive_size", float, 4.0, unit="pt^2 (marker area)", range=(0, None), role="Dot area where a set is not in the intersection"),
    Param("inactive_color", "color", "#d1d5db", unit="hex color", role="Colour of those dots"),
    Param("connector_width", float, 0.8, unit="pt", range=(0, None), role="Line joining the dots of one intersection"),
    Param("grid_line_width", float, 0.4, unit="pt", range=(0, None), role="Faint line through each set row"),
    Param("grid_line_color", "color", "#e5e7eb", unit="hex color", role="Colour of that line"),
    Param("set_label_size", float, None, unit="pt", range=(0, None), role="Set name size (default tick_label_size)"),
    # [Layout and text]
    Param("left_margin", float, 0.2, unit="fraction of the axes width", range=(0, 0.6),
          role="Room left of the grid for the set names", tune="raise if long set names are clipped"),
    Param("labels_title", str, None, role="Panel title"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Set name size (default: rcParams)"),
])


@uses_schema(SCHEMA)
def render_upset(ax, df, params):
    """Draw the UpSet plot onto ``ax``; returns one row per intersection."""
    d_col, i_col = params.get("dataset_col", "dataset"), params.get("item_col", "item")
    ax.set_axis_off()
    if df is None or d_col not in getattr(df, "columns", []) or i_col not in df.columns:
        ax.text(0.5, 0.5, "Required columns not found", ha="center", va="center")
        return None

    data = df.dropna(subset=[d_col, i_col])
    sets = params.get("set_order") or list(dict.fromkeys(data[d_col]))
    if not sets:
        return None
    known = set(sets)
    combos = (data.groupby(i_col, sort=False)[d_col]
              .apply(lambda s: tuple(x for x in sets if x in set(s))))
    counts = combos.value_counts()
    rows = [{"sets": combo, "count": int(n)} for combo, n in counts.items()
            if len(combo) and n >= int(params.get("min_size", 1))]
    if params.get("sort_by", "size") == "degree":
        rows.sort(key=lambda r: (-len(r["sets"]), -r["count"], r["sets"]))
    else:
        rows.sort(key=lambda r: (-r["count"], -len(r["sets"]), r["sets"]))
    rows = rows[: int(params.get("max_columns", 40))]
    if not rows:
        return None

    n = len(rows)
    y_index = {s: i for i, s in enumerate(sets)}
    left = float(params.get("left_margin", 0.2))
    bar_ax = ax.inset_axes([left, 0.46, 1 - left, 0.5])
    mx_ax = ax.inset_axes([left, 0.02, 1 - left, 0.36])
    xs = list(range(n))

    bar_ax.bar(xs, [r["count"] for r in rows], width=float(params.get("bar_width", 0.7)),
               color=params.get("bar_color", "#4b5563"), zorder=2)
    top = max(r["count"] for r in rows)
    bar_ax.set_xlim(-0.5, n - 0.5)
    bar_ax.set_ylim(0, top * 1.18 if top else 1)
    bar_ax.axis("off")
    if params.get("show_counts", True):
        for x, r in zip(xs, rows):
            bar_ax.text(x, r["count"], str(r["count"]), ha="center", va="bottom",
                        fontsize=float(params.get("count_size", 5.0)))

    mx_ax.set_xlim(-0.5, n - 0.5)
    mx_ax.set_ylim(len(sets) - 0.5, -0.5)
    for i in range(len(sets)):
        mx_ax.axhline(i, color=params.get("grid_line_color", "#e5e7eb"),
                      linewidth=float(params.get("grid_line_width", 0.4)), zorder=0)
    dot_size = float(params.get("dot_size", 12.0))
    idle_size = float(params.get("inactive_size", 4.0))
    dot_color = params.get("dot_color", "#111827")
    for x, r in zip(xs, rows):
        included = [y_index[s] for s in r["sets"] if s in y_index]
        if len(included) > 1:
            mx_ax.plot([x, x], [min(included), max(included)], color=dot_color,
                       linewidth=float(params.get("connector_width", 0.8)), zorder=2)
        for s in sets:
            on = s in r["sets"]
            mx_ax.scatter([x], [y_index[s]], s=dot_size if on else idle_size,
                          color=dot_color if on else params.get("inactive_color", "#d1d5db"),
                          linewidths=0, zorder=3)
    mx_ax.set_xticks([])
    mx_ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        mx_ax.spines[side].set_visible(False)
    size = params.get("set_label_size")
    if size is None:
        size = params.get("tick_label_size")
    for i, s in enumerate(sets):
        mx_ax.text(-0.62, i, str(s), ha="right", va="center", clip_on=False,
                   **({} if size is None else {"fontsize": float(size)}))

    title = params.get("labels_title")
    if title:
        ax.set_title(str(title), fontsize=float(params.get("title_size", 8.0)))
    return pd.DataFrame([{"sets": " & ".join(r["sets"]), "count": r["count"]} for r in rows])
