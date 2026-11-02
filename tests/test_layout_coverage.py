"""scripts/layout_coverage.py reads a project repository's analysis scripts
and names the layout that draws each one's arrangement (plans/PLAN_LAYOUT_CATALOG.md,
card L-10). Each case below is a small script of the kind found in a project
repository, with the layout (or the reason for none) it must be given."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_coverage  # noqa: E402

CASES = {
    "uses-draw-plots": ("fig = draw_plots(cfg)\n", "grid", ""),
    "one-row": ("gs = fig.add_gridspec(1, 3, width_ratios=[1, 2, 1])\n"
                "for i in range(3):\n    ax = fig.add_subplot(gs[0, i])\n", "row", ""),
    "one-column": ("gs = fig.add_gridspec(nrows=3, ncols=1, height_ratios=r)\n"
                   "a = fig.add_subplot(gs[0])\nb = fig.add_subplot(gs[1])\nc = fig.add_subplot(gs[2])\n",
                   "stack", ""),
    "wide-bottom": ("gs = fig.add_gridspec(2, 2, height_ratios=r)\n"
                    "a = fig.add_subfigure(gs[0, 0])\nb = fig.add_subfigure(gs[0, 1])\n"
                    "c = fig.add_subfigure(gs[1, :])\n", "wide_bottom", ""),
    "equal-grid": ("gs = fig.add_gridspec(2, 3)\nax = fig.add_subplot(gs[0, 0])\n", "grid", ""),
    "wall": ("gs = fig.add_gridspec(3, 5)\nax = fig.add_subplot(gs[0, 0])\n", "matrix", ""),
    "nested-cell": ("gs = fig.add_gridspec(2, 1)\nsub = fig.add_subfigure(gs[0])\n"
                    "inner = sub.add_gridspec(1, 3)\n", "stack", ""),
    "partial-span": ("gs = fig.add_gridspec(2, 4)\na = fig.add_subplot(gs[0, 0:2])\n", "", "spans"),
    "unequal-grid": ("gs = fig.add_gridspec(2, 2, width_ratios=[1, 2])\n", "", "unequal cells in a grid"),
    "computed-shape": ("gs = fig.add_gridspec(4, ncols)\n", "", "shape computed at run time"),
    "by-hand": ("gs = fig.add_gridspec(1, 2)\nax = fig.add_axes([0.1, 0.1, 0.3, 0.3])\n", "", "manual placement"),
    "two-grids": ("outer = fig.add_gridspec(3, 1)\nover = fig.add_gridspec(1, 1, left=0.1, right=0.5)\n",
                  "", "several grids placed on the canvas"),
    "one-cell-grid": ("gs = fig.add_gridspec(1, 1)\nsub = fig.add_subfigure(gs[0, 0])\n"
                      "inner = sub.add_gridspec(2, 2)\n", "", "one cell holding its own grid"),
    "no-grid": ("ax = fig.add_subplot(1, 1, 1)\n", "", "no grid in the script (a helper or the canvas draws it)"),
}


@pytest.fixture
def repo(tmp_path):
    for name, (body, _, _) in CASES.items():
        level = "paper" if name.startswith("w") else "exploratory"
        path = tmp_path / "analysis" / "lab" / level / f"{name}_analysis.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def main():\n" + "".join(f"    {ln}\n" for ln in body.splitlines()), encoding="utf-8")
    (tmp_path / "analysis" / "lab" / "paper" / "shared_helpers.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def test_each_arrangement_gets_its_layout_or_a_reason(repo):
    rows = {r.project: r for r in (layout_coverage.measure(p, lvl)
                                   for p, lvl in layout_coverage.scripts(repo, ["exploratory", "paper"]))}
    assert set(rows) == set(CASES), "helper modules are not projects"
    for name, (_, layout, reason) in CASES.items():
        assert (rows[name].matched_layout, rows[name].reason) == (layout, reason), name


def test_flags_and_lines(repo):
    path = repo / "analysis" / "lab" / "exploratory" / "nested-cell_analysis.py"
    row = layout_coverage.measure(path, "exploratory")
    assert (row.grid, row.nested, row.spans, row.manual) == ("2x1", 1, 0, 0)
    assert row.loc_before == 3                      # grid, cell, inner grid
    assert row.loc_after == str(2 + 1 + 1)          # layout call + finish, one cell, the inner grid kept


def test_command_writes_the_table(repo, tmp_path, capsys):
    out = tmp_path / "coverage.csv"
    assert layout_coverage.main(["--repo", str(repo), "--csv", str(out)]) == 0
    with out.open(encoding="utf-8") as fh:
        table = list(csv.DictReader(fh))
    assert len(table) == len(CASES)
    assert list(table[0])[:2] == ["project", "level"] and "matched_layout" in table[0] and "loc_after" in table[0]
    printed = capsys.readouterr().out
    assert "| wide_bottom | 1 |" in printed and "median lines" in printed
