"""A grid of cells, filled left to right, top to bottom.

    +---+---+---+
    | a | b | c |
    +---+---+---+
    | d | e | f |
    +---+---+---+
    | g | h |
    +---+---+

``grid(fig, fcfg, "abcdefgh")`` -- 8 panels, 3 columns (the default), 3 rows,
the last row part-filled. The cells are the ones ``draw_plots`` makes from the
same panel count and ``figures.columns`` (tests/test_layouts_core.py checks
it), so a script can move from ``draw_plots`` to an explicit layout without the
figure changing.

Use it for panels of equal weight: a 2x2 of comparisons, a 5x3 wall of small
multiples. Rows or columns of different sizes take ``width_ratios`` /
``height_ratios``; panels that span cells: ``wide_bottom`` (a strip under a
row), ``stack`` (a column), ``row`` (one band), ``matrix`` (dense small panels).

Config (``figures:``) -- copy the keys into the project config with a comment;
the values in brackets are the defaults:

- ``columns`` [3, or the panel count when smaller] -- cells per row.
- ``grid.width_ratios`` / ``grid.height_ratios`` [equal] -- one number per
  column / per row, e.g. ``[1.4, 1.0, 1.0]`` widens the first column; equal
  cells are the ones ``draw_plots`` makes.
- ``wspace`` [0] / ``hspace`` [0] -- gaps between cells, in fractions of the
  mean cell width/height; 0 gives exactly the cells ``draw_plots`` makes, so
  raise them to separate panels that would otherwise share an edge.
- ``panel_pad_mm`` [1.0] -- padding inside each cell, millimetres.
- ``tags.show`` [true], ``tags.size`` [9.0] (pt), ``tags.pad_pt`` [2.0] --
  the panel letters; see ``layouts.finish``.

Adapt by editing those keys, not this file.
"""
from __future__ import annotations

import math

from ._core import Layout, _begin, _block, _grid, _register


def _ratios(name: str, key: str, given, block: dict, count: int, what: str):
    """``given`` (an argument), else ``block[key]``, as a list of ``count`` numbers; None when unset."""
    ratios = given if given is not None else block.get(key)
    if ratios is None:
        return None
    ratios = [float(r) for r in ratios]
    if len(ratios) != count:
        raise ValueError(f"{name} {key} needs one number per {what} ({count}), not {len(ratios)}")
    return ratios


def grid(fig, fcfg: dict, letters, columns=None, width_ratios=None, height_ratios=None) -> Layout:
    """Arrange ``letters`` in a grid; returns the :class:`Layout`.

    ``columns`` (an argument, else ``figures.columns``) sets the cells per row;
    unset it is 3, or the panel count when that is smaller (as ``draw_plots``
    does). ``width_ratios`` / ``height_ratios`` (arguments, else
    ``figures.grid.*``) size the columns and rows; unset, the cells are equal.
    Draw each panel into ``layout.cells[letter]``, then call
    ``layouts.finish(fig, layout, fcfg)``.
    """
    letters, fcfg = _begin(fig, fcfg, letters)
    n = len(letters)
    cols = int(columns if columns is not None else (fcfg or {}).get("columns") or min(n, 3))
    if cols < 1:
        raise ValueError(f"grid columns must be at least 1, not {cols}")
    rows = math.ceil(n / cols)
    block = _block(fcfg, "grid")
    widths = _ratios("grid", "width_ratios", width_ratios, block, cols, "column")
    heights = _ratios("grid", "height_ratios", height_ratios, block, rows, "row")
    gs = _grid(fig, fcfg, rows, cols, width_ratios=widths, height_ratios=heights)
    cells = {letter: fig.add_subfigure(gs.at(i // cols, i % cols)) for i, letter in enumerate(letters)}
    tag_columns = [[l for i, l in enumerate(letters) if i % cols == c] for c in range(cols)]
    tag_rows = [[l for i, l in enumerate(letters) if i // cols == r] for r in range(rows)]
    return _register(fig, Layout(cells, [g for g in tag_columns if g], [g for g in tag_rows if g],
                                  f"{rows}x{cols} {'equal grid' if widths is None and heights is None else 'grid'}"))
