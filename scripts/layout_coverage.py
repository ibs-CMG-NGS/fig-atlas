"""How much of a project repository's layout code the layout catalog covers
(plans/PLAN_LAYOUT_CATALOG.md, card L-10; the evidence of section 1).

    python scripts/layout_coverage.py --repo ../cmg-figures                    # summary
    python scripts/layout_coverage.py --repo ../cmg-figures --csv coverage.csv  # + one row per script

Reads the projects' analysis scripts, ``analysis/<domain>/<level>/*_analysis.py``
(levels ``exploratory`` and ``paper`` by default; helper modules beside them
are not projects), without running them: each script is parsed with ``ast``
and its layout calls are read from the source.

Per script (CSV columns):

- ``project``, ``level`` -- the script's name without ``_analysis.py``, and its folder.
- ``grid`` -- the shape of the top-level grid, ``RxC`` (``?`` when a number is
  computed at run time, empty when the script makes no grid).
- ``ratios`` / ``spans`` / ``nested`` / ``manual`` -- 1 when the script sets
  height/width ratios, gives a panel more than one cell (``gs[1, :]``), nests a
  grid of several cells in another (``subgridspec``, ``add_gridspec`` on a
  subfigure, or a second grid on the figure; a subfigure taking one cell is a
  panel, not nesting), or places axes by figure coordinates (``add_axes`` on
  the figure, ``set_position``; ``add_axes`` inside a cell is the panel's own
  business and does not count).
- ``draw_plots`` -- 1 when the figure is drawn by ``draw_plots``.
- ``placement`` -- what the placement by coordinates does, ``;``-separated:
  ``align`` (an axes moved to line up with another's box, ``set_position``
  built from ``x0``/``width``/...), ``overlay`` (a legend, banner, card or
  colour bar put over the panels), ``band`` (a second grid laid over one band
  of the first, to give that row its own columns or width), ``canvas`` (an axes
  over the whole figure), ``coordinates`` (anything else placed by numbers).
- ``matched_layout`` -- the layout of ``fig_atlas.layouts`` that draws the same
  top-level arrangement today, or empty; ``reason`` says why none does. A cell
  that holds its own grid (``nested``) still matches: the layout gives the
  cells, and the inner grid stays the panel's own code.
- ``composed_layout`` -- the outer layout if layouts could be put inside a cell
  of another (composition): a band grid becomes a layout in that band, and a
  grid whose panels each sit in one row (``gs[r, c0:c1]``, also when the number
  of columns is computed) becomes a ``stack`` of rows, one whose panels each sit
  in one column (``gs[:, 0]``) a ``row`` of columns, and a count computed at run
  time is no obstacle (a layout takes its letters at run time). ``composed_needs``
  lists what it would still take: ``ratios`` (a ``grid``/``matrix`` of unequal
  rows or columns), ``align`` / ``overlay`` helpers; empty when the composition
  alone is enough. A ``set_position`` on an axes made inside a cell lines up two
  axes of one panel: it is the panel's own business, not ``align``. Empty ``composed_layout`` with a reason in
  ``reason`` means composition does not reach it either.
- ``loc_before`` -- lines of layout code: the statements that build grids,
  take a cell (``add_subplot``), place axes by hand, or fit and tag the panels.
- ``loc_after`` -- for a script matched today, the same work with the layout:
  the layout call, ``layouts.finish``, one line per cell taken, and the inner
  grids unchanged. An estimate of what the layout replaces, not a measured rewrite.

Matching, in order: ``draw_plots`` -> ``grid``; placement by figure
coordinates or several grids on the figure -> none; a shape computed at run
time -> none; ``1x1`` -> ``grid``, unless its one cell holds a grid (then the
layout adds nothing: none); one row -> ``row``; one column -> ``stack``; two
rows whose second row is one full-width panel -> ``wide_bottom``; any other
span -> none; ratios on a grid of several rows and columns -> none (``grid``
and ``matrix`` cells are equal); ten cells or more -> ``matrix``; otherwise
``grid``.
"""
from __future__ import annotations

import argparse
import ast
import csv
import re
import statistics
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

GRID_CALLS = {"add_gridspec", "GridSpec", "subgridspec", "add_subfigure", "subfigures"}
CELL_CALLS = {"add_subplot"}
MANUAL_CALLS = {"add_axes", "set_position"}
FINISH_CALLS = {"place_panel_tags", "panel_label", "fit_in_cells", "tight_layout", "subplots_adjust"}
FIGURE = ("fig", "self.fig", "figure")
MATRIX_CELLS = 10                    # a grid of this many cells or more is a wall of small panels
OVERLAY = re.compile(r"legend|banner|card|cbar|colorbar|cb_|title|key", re.I)
BOX = {"x0", "x1", "y0", "y1", "width", "height"}
HELPERS = {"align", "overlay"}       # placements a small helper could take over; the rest stay by hand
# composed_needs may also name "ratios": a grid of unequal rows or columns (grid/matrix take equal cells today)


@dataclass
class Row:
    project: str
    level: str
    grid: str = ""
    ratios: int = 0
    spans: int = 0
    nested: int = 0
    manual: int = 0
    draw_plots: int = 0
    placement: str = ""
    matched_layout: str = ""
    reason: str = ""
    composed_layout: str = ""
    composed_needs: str = ""
    loc_before: int = 0
    loc_after: str = ""


def _name(func: ast.expr) -> str:
    return func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""


def _receiver(func: ast.expr) -> str:
    return ast.unparse(func.value) if isinstance(func, ast.Attribute) else ""


def _int(node) -> int | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, int) else None


def _shape(call: ast.Call) -> tuple[int | None, int | None]:
    kw = {k.arg: k.value for k in call.keywords}
    args = list(call.args) + [None, None]
    rows = kw.get("nrows", args[0])
    cols = kw.get("ncols", args[1])
    return (_int(rows) if rows is not None else 1), (_int(cols) if cols is not None else 1)


def _code_lines(stmt: ast.stmt, source: list[str]) -> int:
    return sum(1 for ln in source[stmt.lineno - 1:stmt.end_lineno]
               if ln.strip() and not ln.strip().startswith("#"))


def _uses_box(node: ast.AST) -> bool:
    """The expression reads another artist's box (``pos.x0``, ``band.width``)."""
    return any(isinstance(n, ast.Attribute) and n.attr in BOX for n in ast.walk(node))


def _target(stmt: ast.stmt) -> str:
    return ast.unparse(stmt.targets[0]) if isinstance(stmt, ast.Assign) else ""


def _placement(stmt: ast.stmt, call: ast.Call, name: str, made_in: dict) -> str:
    """What one ``add_axes`` / ``set_position`` does (see ``placement`` in the module docstring).
    ``made_in`` maps an axes variable to the receiver that created it."""
    if name == "add_axes" and _receiver(call.func) not in FIGURE:
        return "in_cell"
    if name == "set_position" and made_in.get(_receiver(call.func), "fig") not in FIGURE:
        return "in_cell"                                    # lined up with another axes of the same cell
    text = _target(stmt) + " " + ast.unparse(call)
    if name == "add_axes" and call.args and isinstance(call.args[0], ast.List) and \
            [getattr(e, "value", None) for e in call.args[0].elts] == [0, 0, 1, 1]:
        return "canvas"
    if OVERLAY.search(text):
        return "overlay"
    if name == "set_position" and _uses_box(call):
        return "align"
    return "coordinates"


def _is_full_span(sub: ast.Subscript, rows: int | None) -> bool:
    """``gs[k, :]`` with k the last row: one panel across every column."""
    idx = sub.slice
    if not (isinstance(idx, ast.Tuple) and len(idx.elts) == 2):
        return False
    row, col = idx.elts
    full = isinstance(col, ast.Slice) and col.lower is None and col.upper is None and col.step is None
    last = rows is not None and _int(row) in (rows - 1, -1)
    return full and last


def measure(path: Path, level: str) -> Row:
    text = path.read_text(encoding="utf-8")
    source = text.splitlines()
    tree = ast.parse(text)
    row = Row(project=path.name.removesuffix("_analysis.py").removesuffix(".py"), level=level)

    figure_grids, cells = [], 0                             # (statement, call) of each grid on the figure
    layout_stmts, inner_stmts, kinds = set(), set(), set()
    made_in = {_target(st): _receiver(st.value.func) for st in ast.walk(tree)
               if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call)
               and _name(st.value.func) in ("add_subplot", "add_axes")}
    for stmt in ast.walk(tree):
        if not isinstance(stmt, ast.stmt) or isinstance(stmt, (ast.FunctionDef, ast.ClassDef, ast.If, ast.For,
                                                                ast.While, ast.With, ast.Try, ast.Module)):
            continue
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            name = _name(node.func)
            if name == "draw_plots":
                row.draw_plots = 1
            if name in GRID_CALLS | CELL_CALLS | MANUAL_CALLS | FINISH_CALLS:
                layout_stmts.add(stmt)
            if name in CELL_CALLS or name == "add_subfigure":
                cells += 1
            if name in MANUAL_CALLS:
                kinds.add(_placement(stmt, node, name, made_in))
            if name in ("add_gridspec", "GridSpec"):
                if {k.arg for k in node.keywords} & {"height_ratios", "width_ratios"}:
                    row.ratios = 1
                if _receiver(node.func) in FIGURE or name == "GridSpec":
                    figure_grids.append((stmt, node))
                elif _shape(node) != (1, 1):
                    row.nested = 1                          # a grid of several cells inside a cell
                    inner_stmts.add(stmt)
            if name in ("subgridspec", "subfigures") and _shape(node) != (1, 1):
                row.nested = 1
                inner_stmts.add(stmt)

    figure_grids.sort(key=lambda g: g[0].lineno)            # the first grid in the source is the outer one
    for stmt, call in figure_grids[1:]:                     # a later grid on the figure is laid over the first
        edges = [k.value for k in call.keywords if k.arg in ("left", "right", "top", "bottom")]
        kinds.add("overlay" if OVERLAY.search(_target(stmt)) else
                  "band" if any(_uses_box(e) for e in edges) else "coordinates")
    by_hand = kinds - {"in_cell"}
    several = len(figure_grids) > 1
    row.manual = int(bool(by_hand - {"band"}))
    row.nested = int(row.nested or several)
    row.placement = ";".join(sorted(by_hand))

    shape = _shape(figure_grids[0][1]) if figure_grids else None
    if shape:
        row.grid = "x".join("?" if n is None else str(n) for n in shape)
    var = _target(figure_grids[0][0]) if figure_grids else None
    spans, full_last, row_only, col_only = 0, 0, True, True
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == var:
            idx = node.slice
            if isinstance(idx, ast.Tuple) and any(isinstance(e, ast.Slice) for e in idx.elts):
                spans += 1
                full_last += _is_full_span(node, shape[0] if shape else None)
                row_only &= not isinstance(idx.elts[0], ast.Slice)
                col_only &= len(idx.elts) == 2 and not isinstance(idx.elts[1], ast.Slice)
            elif isinstance(idx, ast.Slice):
                spans += 1
                row_only = col_only = False
    row.spans = int(spans > 0)
    row.loc_before = sum(_code_lines(s, source) for s in layout_stmts)

    row.matched_layout, row.reason = _match(row, shape, spans, full_last, several, bool(by_hand))
    if row.matched_layout:
        row.loc_after = str(2 + cells + sum(_code_lines(s, source) for s in inner_stmts))
    row.composed_layout, row.composed_needs = _compose(row, shape, spans, full_last, row_only, col_only, by_hand)
    return row


def _match(row: Row, shape, spans: int, full_last: int, several: bool, by_hand: bool) -> tuple[str, str]:
    if row.draw_plots and not shape:
        return "grid", ""
    if not shape:
        return "", "no grid in the script (a helper or the canvas draws it)"
    if several:
        return "", "several grids placed on the canvas"
    if by_hand:
        return "", "manual placement"
    rows, cols = shape
    if rows is None or cols is None:
        return "", "shape computed at run time"
    if rows == 1 and cols == 1:
        return ("", "one cell holding its own grid") if row.nested else ("grid", "")
    if rows == 1:
        return ("row", "") if not spans else ("", "spans")
    if cols == 1:
        return ("stack", "") if not spans else ("", "spans")
    if spans:
        if rows == 2 and spans == full_last == 1:
            return "wide_bottom", ""
        return "", "spans"
    if row.ratios:
        return "", "unequal cells in a grid"
    return ("matrix", "") if rows * cols >= MATRIX_CELLS else ("grid", "")


def _compose(row: Row, shape, spans: int, full_last: int, row_only: bool, col_only: bool,
             by_hand: set) -> tuple[str, str]:
    """The outer layout if a layout could sit in a cell of another, and what is still needed."""
    if row.matched_layout:
        return row.matched_layout, ""
    if not shape or by_hand & {"coordinates", "canvas"}:
        return "", ""
    needs = ";".join(sorted(by_hand & HELPERS))
    rows, cols = shape
    if rows == 1 and cols == 1:
        return "", ""                                       # the whole figure is one cell: nothing to compose
    if rows == 1 and not spans:
        return "row", needs
    if cols == 1 and not spans:
        return "stack", needs
    if rows == 2 and spans == full_last == 1:
        return "wide_bottom", needs
    if row_only and (spans or cols is None):
        return "stack", needs                               # each row its own band of panels: a stack of rows
    if col_only and spans and rows is not None:
        return "row", needs                                 # each column its own band: a row of columns
    if not spans:                                           # a count computed at run time is fine: letters are too
        name = "matrix" if rows and cols and rows * cols >= MATRIX_CELLS else "grid"
        return name, ";".join(sorted({*filter(None, needs.split(";")), *(["ratios"] if row.ratios else [])}))
    return "", ""


def scripts(repo: Path, levels: list[str]) -> list[tuple[Path, str]]:
    return [(p, level) for level in levels for p in sorted(repo.glob(f"analysis/*/{level}/*_analysis.py"))]


def _count(rows, key) -> list[str]:
    values = sorted({key(r) for r in rows if key(r)}, key=lambda v: (-sum(key(r) == v for r in rows), v))
    return [f"| {v} | {sum(key(r) == v for r in rows)} |" for v in values]


def summary(rows: list[Row], levels: list[str]) -> str:
    out = ["| level | scripts | grid | ratios | spans | nested | manual | draw_plots | matched |",
           "|---|---|---|---|---|---|---|---|---|"]
    for level in levels:
        rs = [r for r in rows if r.level == level]
        out.append(f"| {level} | {len(rs)} | {sum(bool(r.grid) for r in rs)} | {sum(r.ratios for r in rs)} "
                   f"| {sum(r.spans for r in rs)} | {sum(r.nested for r in rs)} | {sum(r.manual for r in rs)} "
                   f"| {sum(r.draw_plots for r in rs)} | {sum(bool(r.matched_layout) for r in rs)} |")
    out += ["", "| matched layout | scripts |", "|---|---|"] + _count(rows, lambda r: r.matched_layout)
    out += ["", "| not matched because | scripts |", "|---|---|"] + _count(rows, lambda r: r.reason)
    matched = [r for r in rows if r.matched_layout]
    if matched:
        before = statistics.median(r.loc_before for r in matched)
        after = statistics.median(int(r.loc_after) for r in matched)
        out += ["", f"Layout code of the matched scripts, median lines: {before:g} before, {after:g} with the layout."]
    composed = [r for r in rows if r.composed_layout and not r.composed_needs]
    helped = [r for r in rows if r.composed_layout and r.composed_needs]
    out += ["", "| scripts covered | today | + composition | + composition, ratios and helpers |", "|---|---|---|---|",
            f"| of {len(rows)} | {len(matched)} | {len(composed)} | {len(composed) + len(helped)} |"]
    out += ["", "| composed: outer layout | scripts |", "|---|---|"] + \
        _count([r for r in rows if r.composed_layout and not r.matched_layout], lambda r: r.composed_layout)
    out += ["", "| still needed | scripts |", "|---|---|"] + _count(helped, lambda r: r.composed_needs)
    out += ["", "| placement by coordinates does | scripts |", "|---|---|"]
    for kind in ("align", "overlay", "band", "canvas", "coordinates"):
        out.append(f"| {kind} | {sum(kind in r.placement.split(';') for r in rows)} |")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, required=True, help="project repository (holds analysis/)")
    ap.add_argument("--levels", default="exploratory,paper", help="comma-separated levels to read")
    ap.add_argument("--csv", type=Path, help="write one row per script here")
    args = ap.parse_args(argv)
    levels = [s.strip() for s in args.levels.split(",") if s.strip()]
    found = scripts(args.repo, levels)
    if not found:
        print(f"no analysis scripts under {args.repo}/analysis/*/{{{','.join(levels)}}}/", file=sys.stderr)
        return 1
    rows = [measure(p, level) for p, level in found]
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=[f.name for f in fields(Row)])
            w.writeheader()
            w.writerows(asdict(r) for r in rows)
    print(summary(rows, levels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
