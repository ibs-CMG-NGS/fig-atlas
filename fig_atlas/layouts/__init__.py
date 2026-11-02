"""Figure layouts: named arrangements of panels (plans/PLAN_LAYOUT_CATALOG.md).

Structure is code, values are config. A layout decides *where* the cells are;
every number it uses (gaps, ratios, padding, tag size) comes from the project
config's ``figures:`` block, with a default. A script reads

    from fig_atlas import layouts

    fcfg = CFG.get("figures", {})
    lay = layouts.wide_bottom(fig, fcfg, top=("a", "b"), bottom="c")
    render_volcano(lay.cells["a"], df_a, params["a"])
    render_line_band(lay.cells["b"], df_b, params["b"])
    render_dot_matrix(lay.cells["c"], df_c, params["c"])
    layouts.finish(fig, lay, fcfg)

| layout        | shape                                            | use for                                  |
|---------------|--------------------------------------------------|------------------------------------------|
| `wide_bottom` | n columns on top, one panel spanning below        | the common publication shape             |
| `stack`       | one column of n rows                              | panels read top to bottom                |
| `grid`        | rows x columns, one panel per cell (ratios opt.)  | panels of equal weight (same as draw_plots) |
| `matrix`      | dense rows x columns, tighter gaps                | small multiples, many small panels       |
| `row`         | one row of n cells                                | one band compared left to right          |

A one-panel figure is ``grid(..., columns=1)``. A figure that draws itself on
the canvas (a schematic, a timeline) is a renderer with the ``(fig, df)``
shape, not a layout. Nothing here imports matplotlib at package load: the
drawing helpers are imported inside ``finish``.
"""
from ._core import Layout, finish
from .grid import grid
from .matrix import matrix
from .row import row
from .stack import stack
from .wide_bottom import wide_bottom

__all__ = ["Layout", "finish", "grid", "wide_bottom", "stack", "matrix", "row"]
