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
  panel, not nesting), or places axes by coordinates
  (``add_axes``, ``set_position``).
- ``draw_plots`` -- 1 when the figure is drawn by ``draw_plots``.
- ``matched_layout`` -- the layout of ``fig_atlas.layouts`` that draws the same
  top-level arrangement, or empty; ``reason`` says why none does. A cell that
  holds its own grid (``nested``) still matches: the layout gives the cells,
  and the inner grid stays the panel's own code.
- ``loc_before`` -- lines of layout code: the statements that build grids,
  take a cell (``add_subplot``), place axes by hand, or fit and tag the panels.
- ``loc_after`` -- for a matched script, the same work with the layout: the
  layout call, ``layouts.finish``, one line per cell taken, and the inner grids
  unchanged. An estimate of what the layout replaces, not a measured rewrite.

Matching, in order: ``draw_plots`` -> ``grid``; manual placement or several
grids on the figure -> none; a shape computed at run time -> none; ``1x1`` ->
``grid``, unless its one cell holds a grid (then the layout adds nothing:
none); one row -> ``row``;
one column -> ``stack``; two rows whose second row is one full-width panel ->
``wide_bottom``; any other span -> none; ratios on a grid of several rows and
columns -> none (``grid`` and ``matrix`` cells are equal); ten cells or more ->
``matrix``; otherwise ``grid``.
"""
from __future__ import annotations

import argparse
import ast
import csv
import statistics
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

GRID_CALLS = {"add_gridspec", "GridSpec", "subgridspec", "add_subfigure", "subfigures"}
CELL_CALLS = {"add_subplot"}
MANUAL_CALLS = {"add_axes", "set_position"}
FINISH_CALLS = {"place_panel_tags", "panel_label", "fit_in_cells", "tight_layout", "subplots_adjust"}
MATRIX_CELLS = 10                    # a grid of this many cells or more is a wall of small panels


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
    matched_layout: str = ""
    reason: str = ""
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

    figure_grids, grid_vars, cells = [], {}, 0
    layout_stmts, inner_stmts = set(), set()
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
                row.manual = 1
            if name in ("add_gridspec", "GridSpec"):
                if {k.arg for k in node.keywords} & {"height_ratios", "width_ratios"}:
                    row.ratios = 1
                if _receiver(node.func) in ("fig", "self.fig", "figure") or name == "GridSpec":
                    figure_grids.append(node)
                    if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name):
                        grid_vars[stmt.targets[0].id] = node
                elif _shape(node) != (1, 1):
                    row.nested = 1                          # a grid of several cells inside a cell
                    inner_stmts.add(stmt)
            if name in ("subgridspec", "subfigures") and _shape(node) != (1, 1):
                row.nested = 1
                inner_stmts.add(stmt)

    several = len(figure_grids) > 1                         # grids placed side by side on the canvas by hand
    shape = _shape(figure_grids[0]) if figure_grids else None
    if shape:
        row.grid = "x".join("?" if n is None else str(n) for n in shape)
    var = next(iter(grid_vars), None)
    spans, full_last = 0, 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == var:
            if isinstance(node.slice, ast.Tuple) and any(isinstance(e, ast.Slice) for e in node.slice.elts):
                spans += 1
                full_last += _is_full_span(node, shape[0] if shape else None)
            elif isinstance(node.slice, ast.Slice):
                spans += 1
    row.spans = int(spans > 0)
    row.loc_before = sum(_code_lines(s, source) for s in layout_stmts)

    row.matched_layout, row.reason = _match(row, shape, spans, full_last, several)
    if row.matched_layout:
        row.loc_after = str(2 + cells + sum(_code_lines(s, source) for s in inner_stmts))
    return row


def _match(row: Row, shape, spans: int, full_last: int, several: bool) -> tuple[str, str]:
    if row.draw_plots and not shape:
        return "grid", ""
    if not shape:
        return "", "no grid in the script (a helper or the canvas draws it)"
    if several:
        return "", "several grids placed on the canvas"
    if row.manual:
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


def scripts(repo: Path, levels: list[str]) -> list[tuple[Path, str]]:
    return [(p, level) for level in levels for p in sorted(repo.glob(f"analysis/*/{level}/*_analysis.py"))]


def summary(rows: list[Row], levels: list[str]) -> str:
    out = ["| level | scripts | grid | ratios | spans | nested | manual | draw_plots | matched |",
           "|---|---|---|---|---|---|---|---|---|"]
    for level in levels:
        rs = [r for r in rows if r.level == level]
        out.append(f"| {level} | {len(rs)} | {sum(bool(r.grid) for r in rs)} | {sum(r.ratios for r in rs)} "
                   f"| {sum(r.spans for r in rs)} | {sum(r.nested for r in rs)} | {sum(r.manual for r in rs)} "
                   f"| {sum(r.draw_plots for r in rs)} | {sum(bool(r.matched_layout) for r in rs)} |")
    out += ["", "| matched layout | scripts |", "|---|---|"]
    for name in sorted({r.matched_layout for r in rows if r.matched_layout}):
        out.append(f"| {name} | {sum(r.matched_layout == name for r in rows)} |")
    out += ["", "| not matched because | scripts |", "|---|---|"]
    reasons = sorted({r.reason for r in rows if r.reason})
    for reason in sorted(reasons, key=lambda x: -sum(r.reason == x for r in rows)):
        out.append(f"| {reason} | {sum(r.reason == reason for r in rows)} |")
    matched = [r for r in rows if r.matched_layout]
    if matched:
        before = statistics.median(r.loc_before for r in matched)
        after = statistics.median(int(r.loc_after) for r in matched)
        out += ["", f"Layout code of the matched scripts, median lines: {before:g} before, {after:g} with the layout."]
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
