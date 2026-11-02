"""``layouts.matrix``: a dense wall of small panels."""
from __future__ import annotations

import pytest

from fig_atlas import layouts

LETTERS = "abcdefghijklm"          # 13 panels: 3 rows of 5, last row of 3


def test_cells_and_default_wall(fig):
    lay = layouts.matrix(fig, {}, LETTERS)
    assert sorted(lay.cells) == sorted(LETTERS)
    assert lay.shape == "3x5 matrix"
    assert lay.rows[0] == list("abcde")
    assert lay.rows[2] == list("klm")
    assert lay.columns[0] == list("afk")


def test_columns_argument_is_the_wall_width(fig):
    lay = layouts.matrix(fig, {}, "abcdef", columns=3)
    assert lay.shape == "2x3 matrix"


def test_cells_do_not_overlap(fig, kit):
    lay = layouts.matrix(fig, {}, LETTERS)
    cells = list(lay.cells.values())
    for i, first in enumerate(cells):
        for second in cells[i + 1:]:
            assert kit.overlap(first, second) == 0.0


def test_panels_are_separated_by_default(fig):
    """matrix separates its small panels; grid's default cells share an edge."""
    dense = layouts.matrix(fig, {}, "abcd", columns=2)
    gap = dense.cells["b"].bbox.x0 - dense.cells["a"].bbox.x1
    assert gap > 0
    plain = layouts.grid(fig, {}, "ab", columns=2)
    assert plain.cells["b"].bbox.x0 - plain.cells["a"].bbox.x1 == pytest.approx(0.0, abs=1e-9)


def test_gaps_from_config(fig):
    narrow = layouts.matrix(fig, {}, "abcd", columns=2)
    wide = layouts.matrix(fig, {"matrix": {"wspace": 0.4}}, "abcd", columns=2)
    gap_narrow = narrow.cells["b"].bbox.x0 - narrow.cells["a"].bbox.x1
    gap_wide = wide.cells["b"].bbox.x0 - wide.cells["a"].bbox.x1
    assert gap_wide > gap_narrow > 0


def test_finish_places_every_tag(fig, kit):
    lay = layouts.matrix(fig, {}, "abcdef")
    kit.draw(lay)
    assert layouts.finish(fig, lay, {})
    assert kit.tags(fig) == sorted("abcdef")
