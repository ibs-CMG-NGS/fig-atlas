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

Fixed size: ``finish`` scales each panel to fill its cell. A panel that must
keep its printed size -- a diagram drawn in millimetres, a matrix of square
cells, an image or a panel shown at the size it is printed -- names that size
under its letter, ``figures.cells.<letter>.size_mm: [width, height]`` (mm,
the data area of all the panel's axes together): ``finish`` places it at the
cell's top-left corner and does not rescale it, so its tag keeps the column's
plumb line. Give the cell room for it and its labels (ratios, gaps, canvas
size); a panel larger than its cell overlaps its neighbour, which preflight
reports.

A panel whose size comes from what it shows -- an image at printed size,
axes set out in millimetres -- is drawn with ``mm_axes(cell, left, top,
width, height)`` (mm from the cell's top-left corner): ``finish`` keeps such
a panel as drawn and only moves it to the cell's top-left corner, so its
size is written once, where it is drawn, and not again under ``size_mm``.

Composition: a layout can be called on a cell of another layout instead of
the figure, to split that cell (plans/PLAN_LAYOUT_CATALOG.md section 16):

    lay = layouts.stack(fig, fcfg, letters=("a", "b", "e"))
    layouts.row(lay.cells["b"], fcfg, letters=("b", "c", "d"))    # cell b -> b | c | d
    ...
    layouts.finish(fig, lay, fcfg)                                 # once, on the outer layout

The inner layout starts with the cell's letter, so the figure reads a, b, c,
d, e. It registers itself on the cell, and ``finish`` splices it in: its
panels are fitted like the others and their letters join the outer plumb
lines and rows. Its values come from ``figures.cells.<letter>`` over the
rest of ``figures:`` (e.g. ``figures.cells.b.row.width_ratios``), so two
cells split the same way keep their own numbers. Two levels at most.
"""
from __future__ import annotations

import math
import string
from dataclasses import dataclass

__all__ = ["Layout", "finish", "mm_axes", "panel_cells", "_grid", "_check_letters", "_block", "_begin", "_register"]

MAX_DEPTH = 2                        # a layout in a cell of another, no deeper (plan section 16)
ALIGN_MM = 0.5                       # inner columns/rows of sibling cells closer than this share tag lines


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


def _begin(fig, fcfg: dict, letters) -> tuple[tuple[str, ...], dict]:
    """Validate ``letters`` and resolve the values for a layout drawn on ``fig``.

    ``fig`` is the figure, or a cell of another layout (composition). In a cell
    the first letter must be the cell's own, a cell holds one layout, and the
    values are ``figures.cells.<letter>`` over the rest of ``figures:``.
    """
    letters = _check_letters(letters)
    letter = getattr(fig, "_fa_letter", None)
    if letter is None:
        return letters, fcfg or {}
    depth = getattr(fig, "_fa_depth", 1)
    if depth >= MAX_DEPTH:
        raise ValueError(f"cell {letter!r} is already inside a cell: layouts nest {MAX_DEPTH} levels at most")
    if getattr(fig, "_fa_layout", None) is not None:
        raise ValueError(f"cell {letter!r} already holds a layout")
    if letters[0] != letter:
        raise ValueError(f"a layout in cell {letter!r} starts with {letter!r} (the cell's letter), "
                         f"not {letters[0]!r}")
    return letters, _cell_values(fcfg, letter)


def _cell_values(fcfg: dict, letter: str) -> dict:
    """``figures:`` without ``cells``, with ``figures.cells.<letter>`` over it (one level deep)."""
    own = _block(_block(fcfg, "cells"), letter)
    merged = {k: v for k, v in (fcfg or {}).items() if k != "cells"}
    for key, value in own.items():
        base = merged.get(key)
        merged[key] = {**base, **value} if isinstance(value, dict) and isinstance(base, dict) else value
    return merged


def _register(fig, layout: "Layout") -> "Layout":
    """Mark each cell with its letter and level; on a cell, record the layout for ``finish``."""
    depth = getattr(fig, "_fa_depth", 0) + 1
    for letter, cell in layout.cells.items():
        cell._fa_letter, cell._fa_depth = letter, depth
    if getattr(fig, "_fa_letter", None) is not None:
        fig._fa_layout = layout
    return layout


def _splice(layout: "Layout") -> "Layout":
    """The layout with the layouts drawn in its cells spliced in (composition).

    A split cell's letter is replaced, in its outer column and row, by the
    inner layout's first column and first row; the inner layout's other
    columns and rows join as groups of their own. Cells split alike in one
    outer column (or row) line up: their other columns that start at the same
    left edge (rows: the same top edge) become one group, so their letters
    share a plumb line too (AGENTS.md 1.5).
    """
    inner = {letter: cell._fa_layout for letter, cell in layout.cells.items()
             if getattr(cell, "_fa_layout", None) is not None}
    if not inner:
        return layout
    cells = {}
    for letter, cell in layout.cells.items():
        for name, sub in (inner[letter].cells.items() if letter in inner else [(letter, cell)]):
            if name in cells:
                raise ValueError(f"panel letter {name!r} is used twice (a layout in cell {letter!r} repeats it)")
            cells[name] = sub

    tol = ALIGN_MM / 25.4 * next(iter(cells.values())).dpi       # display px

    def aligned(groups, edge):
        """Join groups whose first cells start at the same ``edge`` (within ``ALIGN_MM``)."""
        out = []
        for group in groups:
            here = edge(cells[group[0]].bbox)
            match = next((g for g in out if abs(edge(cells[g[0]].bbox) - here) <= tol), None)
            if match is None:
                out.append(list(group))
            else:
                match += group
        return out

    def splice(groups, inner_groups, edge):
        out = []
        for group in groups:
            joined, extra = [], []
            for letter in group:
                if letter in inner:
                    first, *rest = inner_groups(inner[letter])
                    joined += first
                    extra += rest
                else:
                    joined.append(letter)
            out += [joined] + aligned(extra, edge)
        return out

    shape = layout.shape + "; " + ", ".join(f"cell {l}: {lay.shape}" for l, lay in inner.items())
    return Layout(cells, splice(layout.columns, lambda lay: lay.columns, lambda b: b.x0),
                  splice(layout.rows, lambda lay: lay.rows, lambda b: b.y1), shape)


def _size_mm(fcfg: dict, letter: str):
    """``figures.cells.<letter>.size_mm`` as ``(width, height)`` in mm, or None (fit to the cell)."""
    size = _block(_block(fcfg, "cells"), letter).get("size_mm")
    if size is None:
        return None
    try:
        w, h = (float(v) for v in size)
    except (TypeError, ValueError):
        raise ValueError(f"figures.cells.{letter}.size_mm must be [width, height] in mm, not {size!r}") from None
    if w <= 0 or h <= 0:
        raise ValueError(f"figures.cells.{letter}.size_mm must be positive, not {size!r}")
    return w, h


def mm_axes(cell, left: float, top: float, width: float, height: float):
    """Axes in ``cell`` at ``left``/``top`` mm from the cell's top-left corner,
    ``width`` x ``height`` mm. ``finish`` keeps a cell drawn this way at its
    drawn size and only moves it to the cell's corner (see "Fixed size")."""
    if width <= 0 or height <= 0:
        raise ValueError(f"mm_axes needs a positive width and height, not {width} x {height} mm")
    box, k = cell.bbox, cell.dpi / 25.4                 # the cell in pixels; pixels per mm
    ax = cell.add_axes([left * k / box.width, 1 - (top + height) * k / box.height,
                        width * k / box.width, height * k / box.height])
    cell._fa_drawn_mm = True
    return ax


def _kept_size(fcfg: dict, letter: str, cell):
    """How ``finish`` sizes a panel: ``(w, h)`` mm from ``size_mm``, "drawn"
    for a cell drawn with ``mm_axes``, or None (fit to the cell)."""
    size = _size_mm(fcfg, letter)
    if size is not None and getattr(cell, "_fa_drawn_mm", False):
        raise ValueError(f"cell {letter!r} is drawn with mm_axes, which keeps its drawn size: "
                         f"remove figures.cells.{letter}.size_mm")
    return "drawn" if getattr(cell, "_fa_drawn_mm", False) else size


def panel_cells(layout: "Layout") -> dict:
    """Every panel's cell by letter, including the cells of layouts drawn inside
    a cell (composition) -- draw each panel into ``panel_cells(lay)[letter]``.
    Call it after splitting the cells; a split cell itself is not a panel."""
    return dict(_splice(layout).cells)


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

    Call it once, on the outermost layout: layouts drawn in its cells are
    spliced in, so their panels are fitted and tagged with the rest
    (``panel_pad_mm`` and ``tags`` come from this ``fcfg``). A panel with
    ``figures.cells.<letter>.size_mm`` keeps that size, and one drawn with
    ``mm_axes`` keeps its drawn size (see "Fixed size").
    """
    from ..bundle_figure import fit_in_cells                    # lazy: no matplotlib at import
    from ..renderers.panels import place_panel_tags

    layout = _splice(layout)
    tags = (fcfg or {}).get("tags") or {}
    show = bool(tags.get("show", True))
    size = float(tags.get("size", 9.0))
    pad_pt = float(tags.get("pad_pt", 2.0))
    top_pt = size + pad_pt if show else 0.0
    panels = [(cell, list(cell.axes), _kept_size(fcfg, letter, cell))
              for letter, cell in layout.cells.items() if list(cell.axes)]
    fit_in_cells(fig, panels, pad_mm=float((fcfg or {}).get("panel_pad_mm", 1.0)),
                 top_reserve_pt=top_pt)
    if not show:
        return []
    columns = [[(letter, list(layout.cells[letter].axes)) for letter in group]
               for group in layout.columns]
    return place_panel_tags(fig, columns, size, pad_pt=pad_pt, align_rows=layout.rows)
