"""A row of panels with one full-width panel beneath it.

    +-------+-------+
    |   a   |   b   |
    +-------+-------+
    |       c       |
    +---------------+

``wide_bottom(fig, fcfg, top=("a", "b"), bottom="c")`` -- the commonest
publication shape: data panels on top, a wide summary, legend strip, timeline
or schematic underneath. The bottom cell spans every column, so its left edge
lines up with panel ``a``; its tag belongs to that first column and shares the
column's plumb line.

More than two top panels is fine (``top=("a", "b", "c")``); one top panel is
a stack of two with unequal heights -- use ``stack`` for that instead.

Config (``figures:``) -- copy the keys into the project config with a comment;
values in brackets are the defaults:

- ``wide_bottom.height_ratios`` [equal] -- e.g. ``[1.0, 1.4]`` makes the
  bottom row taller than the top; the list needs one number per row.
- ``wspace`` [0] / ``hspace`` [0] -- gaps between cells (fractions of the
  mean cell width/height); raise them to separate panels that share an edge.
- ``panel_pad_mm`` [1.0] -- padding inside each cell, millimetres.
- ``tags.show`` [true], ``tags.size`` [9.0] (pt), ``tags.pad_pt`` [2.0] --
  the panel letters; see ``layouts.finish``.

Adapt by editing those keys, not this file.
"""
from __future__ import annotations

from ._core import Layout, _block, _check_letters, _grid


def wide_bottom(fig, fcfg: dict, top, bottom) -> Layout:
    """Top row of ``top`` panels, ``bottom`` spanning the full width below.

    Draw each panel into ``layout.cells[letter]``, then call
    ``layouts.finish(fig, layout, fcfg)``.
    """
    top = tuple(top)
    letters = _check_letters(top + (bottom,))
    if len(top) < 2:
        raise ValueError("wide_bottom needs at least two top panels; "
                         "for one top panel and one below, use stack")
    ratios = _block(fcfg, "wide_bottom").get("height_ratios")
    if ratios is not None:
        ratios = list(ratios)
        if len(ratios) != 2:
            raise ValueError(f"figures.wide_bottom.height_ratios needs 2 numbers (one per row), "
                             f"not {len(ratios)}")
    gs = _grid(fig, fcfg, 2, len(top), height_ratios=ratios)
    cells = {letter: fig.add_subfigure(gs.at(0, i)) for i, letter in enumerate(top)}
    cells[bottom] = fig.add_subfigure(gs.span_row(1))
    tag_columns = [[letter] for letter in top]
    tag_columns[0] = [top[0], bottom]          # the wide panel starts in column 0
    return Layout(cells, tag_columns, [list(top), [bottom]],
                  f"{len(top)} columns + full-width bottom row")
