"""One column of panels, one above another.

    +-------+
    |   a   |
    +-------+
    |   b   |
    +-------+
    |   c   |
    +-------+

``stack(fig, fcfg, "abc")`` -- panels that read top to bottom: a timeline and
its measurements, a heatmap and the row/column summaries beside it, a series
of steps. All tags sit on one plumb line, the left edge of the cluster.

For a figure whose panels should be compared side by side use ``row``; for
data on top and a wide strip below, ``wide_bottom``.

Config (``figures:``) -- copy the keys into the project config with a comment;
values in brackets are the defaults:

- ``stack.height_ratios`` [equal] -- e.g. ``[1.0, 2.0]`` for two rows; the
  list needs one number per panel, top to bottom.
- ``hspace`` [0] -- the gap between rows (fraction of the mean row height);
  raise it when the panel above has x tick labels.
- ``panel_pad_mm`` [1.0] -- padding inside each cell, millimetres.
- ``tags.show`` [true], ``tags.size`` [9.0] (pt), ``tags.pad_pt`` [2.0] --
  the panel letters; see ``layouts.finish``.

Adapt by editing those keys, not this file.
"""
from __future__ import annotations

from ._core import Layout, _begin, _block, _grid, _register


def stack(fig, fcfg: dict, letters, height_ratios=None) -> Layout:
    """One column: ``letters`` from top to bottom; returns the :class:`Layout`.

    ``height_ratios`` (an argument, else ``figures.stack.height_ratios``)
    sizes the rows. Draw each panel into ``layout.cells[letter]``, then call
    ``layouts.finish(fig, layout, fcfg)``.
    """
    letters, fcfg = _begin(fig, fcfg, letters)
    ratios = height_ratios if height_ratios is not None else _block(fcfg, "stack").get("height_ratios")
    if ratios is not None:
        ratios = list(ratios)
        if len(ratios) != len(letters):
            raise ValueError(f"stack needs one height ratio per panel ({len(letters)}), "
                             f"not {len(ratios)}")
    gs = _grid(fig, fcfg, len(letters), 1, height_ratios=ratios)
    cells = {letter: fig.add_subfigure(gs.at(i, 0)) for i, letter in enumerate(letters)}
    return _register(fig, Layout(cells, [list(letters)], [[letter] for letter in letters],
                                  f"{len(letters)} stacked rows"))
