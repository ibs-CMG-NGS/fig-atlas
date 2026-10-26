"""Stacked bars: one vertical bar per category, split into the parts that make
it up (cell types per sample, outcome classes per treatment), as counts or as
shares of 100 %.

Data: one row per (category, part) -- ``x_col``, ``stack_col`` and
``value_col`` (a count); rows that repeat a pair are added together. Returns
the table drawn (category, part, value, share), ready for
``fig_atlas.source_data.add``.
"""
from __future__ import annotations

FAMILY = "parts_of_whole"    # gallery family (fig_atlas/family.py): the shape this module draws

import pandas as pd

from ..schema import CODE_DEFAULT, Param, Schema, uses_schema
from ._basic import TEXT, Y_AXIS, finish

SCHEMA = Schema("stacked_bar", extends=[Y_AXIS, TEXT], params=[
    # [Data]
    Param("x_col", str, "category", role="Column with the categories (one bar each)"),
    Param("stack_col", str, "part", role="Column with the parts stacked in each bar"),
    Param("value_col", str, "count", role="Column with the counts"),
    Param("x_order", list, None, role="Bar order (default: order in the data)"),
    Param("stack_order", list, None, role="Part order from the bottom up (default: order in the data)"),
    Param("x_labels", dict, {}, open_keys=True, role="Shown name per category (default: the category)"),
    Param("percent", bool, True, role="Each bar as shares of 100 % (False: counts)"),
    # [Bars]
    Param("stack_colors", dict, {}, open_keys=True, unit="hex color",
          role="Colour per part (default: matplotlib colour cycle)"),
    Param("stack_labels", dict, {}, open_keys=True, role="Legend label per part (default: the part)"),
    Param("bar_width", float, 0.7, unit="x units (bars are 1 apart)", range=(0, 1), role="Bar width"),
    Param("edge_color", "color", "#ffffff", unit="hex color", role="Line between the parts"),
    Param("edge_width", float, 0.5, unit="pt", range=(0, None), role="Width of that line"),
    Param("x_tick_rotation", float, 0.0, unit="degrees", role="Rotation of the category names",
          tune="raise (e.g. 45) when long names collide"),
    Param("legend_outside", bool, True, role="Put the legend right of the bars (so it never covers them)"),
    Param("legend_anchor", list, [1.02, 0.5], unit="axes fraction [x, y]",
          role="Where the legend's left middle sits when outside", tune="raise x for more gap from the bars"),
    Param("legend_ncol", int, 1, unit="columns", role="Number of columns in the legend"),
    Param("legend_loc", str, CODE_DEFAULT,
          role="Legend anchor (matplotlib loc); the default follows legend_outside: 'center left' outside, 'best' inside"),
])


@uses_schema(SCHEMA)
def render_stacked_bar(ax, df, params):
    """Draw the stacked bars onto ``ax``; returns the table drawn."""
    import matplotlib
    x_col, s_col, v_col = params.get("x_col", "category"), params.get("stack_col", "part"), params.get("value_col", "count")
    t = (df.assign(**{v_col: pd.to_numeric(df[v_col], errors="coerce")})
         .groupby([x_col, s_col], sort=False)[v_col].sum().unstack(fill_value=0))
    xs = params.get("x_order") or list(dict.fromkeys(df[x_col].dropna()))
    parts = params.get("stack_order") or list(dict.fromkeys(df[s_col].dropna()))
    t = t.reindex(index=xs, columns=parts, fill_value=0)
    share = t.div(t.sum(axis=1).replace(0, float("nan")), axis=0) * 100
    shown = share if params.get("percent", True) else t
    colors, labels = params.get("stack_colors", {}), params.get("stack_labels", {})
    cycle = matplotlib.rcParams["axes.prop_cycle"].by_key().get("color", [None])
    bottom = pd.Series(0.0, index=xs)
    for i, p in enumerate(parts):
        ax.bar(range(len(xs)), shown[p].fillna(0), bottom=bottom, width=params.get("bar_width", 0.7),
               color=colors.get(p) or cycle[i % len(cycle)], label=str(labels.get(p, p)),
               edgecolor=params.get("edge_color", "#ffffff"), linewidth=params.get("edge_width", 0.5))
        bottom = bottom + shown[p].fillna(0)
    names = params.get("x_labels", {})
    rot = params.get("x_tick_rotation", 0.0)
    ax.set_xticks(range(len(xs)), [str(names.get(x, x)) for x in xs], rotation=rot, ha="right" if rot else "center")
    finish(ax, params, x_col, "share (%)" if params.get("percent", True) else v_col, numeric_x=False)
    if params.get("show_legend", True):
        size = params.get("legend_fontsize")
        handles, texts = ax.get_legend_handles_labels()
        ncol = params.get("legend_ncol", 1)
        loc = params.get("legend_loc", "center left" if params.get("legend_outside", True) else "best")
        where = (dict(loc=loc, bbox_to_anchor=tuple(params.get("legend_anchor", [1.02, 0.5])))
                 if params.get("legend_outside", True) else dict(loc=loc))
        ax.legend(handles[::-1], texts[::-1], frameon=params.get("legend_frameon", False),
                  fontsize=size if size is not None else params.get("tick_label_size"), ncol=ncol, **where)
    long = t.stack().rename("value").reset_index().rename(columns={x_col: "category", s_col: "part"})
    long["share"] = share.to_numpy().ravel()     # same row-major order as t.stack(); an empty bar keeps NaN
    return long
