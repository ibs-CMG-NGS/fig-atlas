"""Figure layouts: named arrangements of panels (plans/PLAN_LAYOUT_CATALOG.md).

A layout turns the config's ``figures:`` block into named cells. Draw each
panel into its cell, then call ``finish`` to fit the panels into their cells
and place the panel letters:

    fcfg = CFG.get("figures", {})
    lay = layouts.wide_bottom(fig, fcfg, top=("a", "b"), bottom="c")
    render_volcano(lay.cells["a"], df_a, params["a"])
    ...
    layouts.finish(fig, lay, fcfg)

Structure is code, values are config: the layout decides *where* the cells
are, and every number it uses (ratios, gaps, padding, tag size) comes from
``figures:`` with a default. A one-panel figure is ``grid(..., columns=1)``;
a figure that draws itself on the canvas (a schematic) is a renderer with the
``(fig, df)`` shape, not a layout.
"""
from __future__ import annotations

import math
import string
from dataclasses import dataclass

__all__ = ["Layout", "finish", "_grid", "_check_letters", "_block"]


@dataclass(frozen=True)
class Layout:
    """The cells of one figure layout.

    ``cells`` maps a panel letter to its subfigure (draw into it),
    ``columns`` and ``rows`` are the letter groups panel tags align on
    (``place_panel_tags``), and ``shape`` describes the arrangement in words.
    """

    cells: dict
    columns: list
    rows: list
    shape: str


def _check_letters(letters) -> tuple[str, ...]:
    """Validate panel letters: one lower-case ascii letter each, no repeats."""
    letters = tuple(letters)
    if not letters:
        raise ValueError("a layout needs at least one panel letter")
    seen = set()
    for letter in letters:
        if not isinstance(letter, str) or len(letter) != 1 or letter not in string.ascii_lowercase:
            raise ValueError(f"panel letter {letter!r}: use one lower-case letter a-z")
        if letter in seen:
            raise ValueError(f"panel letter {letter!r} is used twice")
        seen.add(letter)
    return letters


def _block(fcfg: dict, name: str) -> dict:
    """The layout's own ``figures.<name>`` block (empty when unset)."""
    block = (fcfg or {}).get(name) or {}
    if not isinstance(block, dict):
        raise ValueError(f"figures.{name} must be a mapping, not {type(block).__name__}")
    return block


class Cells:
    """SubplotSpec lookup for a layout grid (``at`` / ``span_row``).

    Gaps are real separator rows and columns, not ``wspace``/``hspace``:
    matplotlib places a SubFigure at the *raw* GridSpec cell and ignores the
    spacing (``SubFigure._redo_transform_rel_fig`` uses the ratios only), so a
    ``wspace`` given to the GridSpec would do nothing. A separator of ratio
    ``wspace * mean(cell)`` reproduces exactly the spacing ``add_subplot``
    gives the same GridSpec.
    """

    def __init__(self, grid, rows: int, cols: int, step: int):
        self.grid, self.rows, self.cols, self.step = grid, rows, cols, step

    def at(self, row: int, col: int):
        """The cell at ``row``/``col``; call ``fig.add_subfigure`` on it."""
        return self.grid[row * self.step, col * self.step]

    def span_row(self, row: int):
        """One row, spanning every column (gaps included)."""
        return self.grid[row * self.step, :]


def _with_gaps(ratios: list, gap: float) -> list:
    """``[r0, r1]`` -> ``[r0, gap, r1]`` (a separator between each pair)."""
    out = [ratios[0]]
    for ratio in ratios[1:]:
        out.extend([gap, ratio])
    return out


def _grid(fig, fcfg: dict, rows: int, cols: int, *, height_ratios=None, width_ratios=None,
          wspace=None, hspace=None) -> Cells:
    """A GridSpec of ``rows`` x ``cols`` cells on the whole canvas (0..1).

    ``wspace`` / ``hspace`` (default ``figures.wspace`` / ``figures.hspace``,
    else 0) are gaps in fractions of the mean cell width/height, the GridSpec
    convention. Zero -- the default -- gives the cells ``draw_plots`` makes, so
    a script can move between the two without the figure changing.
    """
    if rows < 1 or cols < 1:
        raise ValueError(f"a grid needs at least one row and one column ({rows} x {cols})")
    wspace = float(fcfg.get("wspace", 0.0) if wspace is None else wspace)
    hspace = float(fcfg.get("hspace", 0.0) if hspace is None else hspace)
    if wspace < 0 or hspace < 0:
        raise ValueError(f"gaps cannot be negative (wspace={wspace}, hspace={hspace})")
    widths = [float(r) for r in width_ratios] if width_ratios is not None else [1.0] * cols
    heights = [float(r) for r in height_ratios] if height_ratios is not None else [1.0] * rows
    if len(widths) != cols:
        raise ValueError(f"width_ratios needs {cols} numbers, not {len(widths)}")
    if len(heights) != rows:
        raise ValueError(f"height_ratios needs {rows} numbers, not {len(heights)}")
    if wspace == 0 and hspace == 0:
        grid = fig.add_gridspec(rows, cols, left=0, right=1, bottom=0, top=1,
                                width_ratios=widths, height_ratios=heights)
        return Cells(grid, rows, cols, 1)
    col_ratios = _with_gaps(widths, wspace * sum(widths) / cols)
    row_ratios = _with_gaps(heights, hspace * sum(heights) / rows)
    grid = fig.add_gridspec(2 * rows - 1, 2 * cols - 1, left=0, right=1, bottom=0, top=1,
                            width_ratios=col_ratios, height_ratios=row_ratios)
    return Cells(grid, rows, cols, 2)


def finish(fig, layout: Layout, fcfg: dict) -> list:
    """Fit every panel into its cell and place the panel letters.

    Call after everything is drawn: the fitting measures the panels' outer
    bounding boxes (tick labels, titles and legends included), and the tags
    sit on that outer edge, ``figures.tags.pad_pt`` above the panel
    (AGENTS.md 1.5). ``figures.tags.show: false`` places no letters.
    """
    from ..bundle_figure import fit_in_cells                    # lazy: no matplotlib at import
    from ..renderers.panels import place_panel_tags

    tags = (fcfg or {}).get("tags") or {}
    show = bool(tags.get("show", True))
    size = float(tags.get("size", 9.0))
    pad_pt = float(tags.get("pad_pt", 2.0))
    top_pt = size + pad_pt if show else 0.0
    panels = [(cell, list(cell.axes)) for cell in layout.cells.values() if list(cell.axes)]
    fit_in_cells(fig, panels, pad_mm=float((fcfg or {}).get("panel_pad_mm", 1.0)),
                 top_reserve_pt=top_pt)
    if not show:
        return []
    columns = [[(letter, list(layout.cells[letter].axes)) for letter in group]
               for group in layout.columns]
    return place_panel_tags(fig, columns, size, pad_pt=pad_pt, align_rows=layout.rows)
