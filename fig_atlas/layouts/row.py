"""One row of panels, side by side.

    +-------+-------+-------+
    |   a   |   b   |   c   |
    +-------+-------+-------+

``row(fig, fcfg, "abc")`` -- one band of panels compared left to right: three
conditions, a before/after/both triptych, five time points. Every panel sits in
one layout row, so their tags share a baseline even when the titles differ in
height.

``row`` is the one-row case of ``grid``; use it rather than ``grid(columns=3)``
when the panels' widths differ (``row.width_ratios``) or when the figure is
deliberately one band and you want the intent to read from the code.

Config (``figures:``) -- copy the keys into the project config with a comment;
values in brackets are the defaults:

- ``row.width_ratios`` [equal] -- e.g. ``[1.0, 1.6, 1.0]`` gives the middle
  panel more width (a wider heatmap, a longer legend); one number per panel.
- ``wspace`` [0] -- the gap between panels (fraction of the mean width).
- ``panel_pad_mm`` [1.0] -- padding inside each cell, millimetres.
- ``tags.show`` [true], ``tags.size`` [9.0] (pt), ``tags.pad_pt`` [2.0] --
  the panel letters; see ``layouts.finish``.

Adapt by editing those keys, not this file.
"""
from __future__ import annotations

from ._core import Layout, _block, _check_letters, _grid


def row(fig, fcfg: dict, letters, width_ratios=None) -> Layout:
    """One row: ``letters`` from left to right; returns the :class:`Layout`.

    ``width_ratios`` (an argument, else ``figures.row.width_ratios``) sizes the
    cells. Draw each panel into ``layout.cells[letter]``, then call
    ``layouts.finish(fig, layout, fcfg)``.
    """
    letters = _check_letters(letters)
    ratios = width_ratios if width_ratios is not None else _block(fcfg, "row").get("width_ratios")
    if ratios is not None:
        ratios = list(ratios)
        if len(ratios) != len(letters):
            raise ValueError(f"row needs one width ratio per panel ({len(letters)}), "
                             f"not {len(ratios)}")
    gs = _grid(fig, fcfg, 1, len(letters), width_ratios=ratios)
    cells = {letter: fig.add_subfigure(gs.at(0, i)) for i, letter in enumerate(letters)}
    return Layout(cells, [[letter] for letter in letters], [list(letters)],
                  f"1x{len(letters)} row")
