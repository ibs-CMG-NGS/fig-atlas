"""Many small panels in a dense, even wall.

    +---+---+---+---+---+
    | a | b | c | d | e |
    +---+---+---+---+---+
    | f | g | h | i | j |
    +---+---+---+---+---+
    | k | l | m |
    +---+---+---+

``matrix(fig, fcfg, "abcdefghijklm")`` -- 5 columns by default: screens of
small multiples (one sample per cell, a grid of dot plots) where the single
figure is the point and each panel is read at a glance.

It is ``grid`` with the small-panel defaults: tighter gaps of its own
(``figures.matrix.wspace`` / ``hspace``), so the dense wall stays readable
without retuning the gaps of every other figure in the project. Panels of
equal number and weight that need more air use ``grid``; one band of panels
uses ``row``; unequal panels use ``wide_bottom`` or ``stack``.

Config (``figures:``) -- copy the keys into the project config with a comment;
values in brackets are the defaults:

- ``matrix.wspace`` [0.06] / ``matrix.hspace`` [0.12] -- gaps within the wall
  (fractions of the mean cell width/height); smaller than ``grid``'s because
  the panels are small.
- ``matrix.columns`` [5, or the panel count when smaller] -- cells per row.
- ``matrix.width_ratios`` / ``matrix.height_ratios`` [equal] -- one number per
  column / per row, e.g. a wider first column for a heatmap beside dot plots.
- ``panel_pad_mm`` [1.0] -- padding inside each cell, millimetres; lower it
  (e.g. 0.5) to buy space for more cells.
- ``tags.show`` [true], ``tags.size`` [9.0] (pt), ``tags.pad_pt`` [2.0] --
  the panel letters; see ``layouts.finish``.

Adapt by editing those keys, not this file.
"""
from __future__ import annotations

import math

from ._core import Layout, _block, _check_letters, _grid
from .grid import _ratios


def matrix(fig, fcfg: dict, letters, columns=None, width_ratios=None, height_ratios=None) -> Layout:
    """A dense wall of ``letters`` (``columns`` wide, 5 by default).

    ``width_ratios`` / ``height_ratios`` (arguments, else ``figures.matrix.*``)
    size the columns and rows; unset, the cells are equal. Draw each panel into
    ``layout.cells[letter]``, then call ``layouts.finish(fig, layout, fcfg)``.
    """
    letters = _check_letters(letters)
    n = len(letters)
    block = _block(fcfg, "matrix")
    cols = int(columns if columns is not None else block.get("columns") or min(n, 5))
    if cols < 1:
        raise ValueError(f"matrix columns must be at least 1, not {cols}")
    rows = math.ceil(n / cols)
    widths = _ratios("matrix", "width_ratios", width_ratios, block, cols, "column")
    heights = _ratios("matrix", "height_ratios", height_ratios, block, rows, "row")
    gs = _grid(fig, fcfg, rows, cols, width_ratios=widths, height_ratios=heights,
               wspace=block.get("wspace", 0.06), hspace=block.get("hspace", 0.12))
    cells = {letter: fig.add_subfigure(gs.at(i // cols, i % cols)) for i, letter in enumerate(letters)}
    tag_columns = [[l for i, l in enumerate(letters) if i % cols == c] for c in range(cols)]
    tag_rows = [[l for i, l in enumerate(letters) if i // cols == r] for r in range(rows)]
    return Layout(cells, [g for g in tag_columns if g], [g for g in tag_rows if g],
                  f"{rows}x{cols} matrix")
