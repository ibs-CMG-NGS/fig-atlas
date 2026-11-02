"""``layouts.row``: one row of panels."""
from __future__ import annotations

import pytest

from fig_atlas import layouts


def test_cells_and_tag_groups(fig):
    lay = layouts.row(fig, {}, "abcd")
    assert sorted(lay.cells) == ["a", "b", "c", "d"]
    assert lay.shape == "1x4 row"
    assert lay.columns == [["a"], ["b"], ["c"], ["d"]]
    assert lay.rows == [["a", "b", "c", "d"]]


def test_cells_sit_side_by_side(fig, kit):
    lay = layouts.row(fig, {}, "abc")
    a, b, c = (lay.cells[l] for l in "abc")
    assert a.bbox.y0 == pytest.approx(b.bbox.y0, abs=1e-9)
    assert a.bbox.height == pytest.approx(b.bbox.height, abs=1e-9)
    assert a.bbox.x1 <= b.bbox.x0 + 1e-9 and b.bbox.x1 <= c.bbox.x0 + 1e-9
    for i, first in enumerate(lay.cells.values()):
        for second in list(lay.cells.values())[i + 1:]:
            assert kit.overlap(first, second) == 0.0


def test_width_ratios_from_config(fig):
    lay = layouts.row(fig, {"row": {"width_ratios": [1.0, 2.0]}}, "ab")
    a, b = lay.cells["a"], lay.cells["b"]
    assert b.bbox.width == pytest.approx(2 * a.bbox.width, rel=1e-6)


def test_wspace_separates_panels(fig):
    lay = layouts.row(fig, {"wspace": 0.2}, "ab")
    a, b = lay.cells["a"], lay.cells["b"]
    assert b.bbox.x0 - a.bbox.x1 == pytest.approx(0.2 * a.bbox.width, rel=1e-6)


def test_width_ratios_argument_wins(fig):
    lay = layouts.row(fig, {"row": {"width_ratios": [1.0, 1.0]}}, "ab", width_ratios=[3.0, 1.0])
    a, b = lay.cells["a"], lay.cells["b"]
    assert a.bbox.width == pytest.approx(3 * b.bbox.width, rel=1e-6)


def test_width_ratios_count_is_checked(fig):
    with pytest.raises(ValueError, match="width ratio"):
        layouts.row(fig, {"row": {"width_ratios": [1.0]}}, "ab")


def test_finish_places_every_tag(fig, kit):
    lay = layouts.row(fig, {}, "abc")
    kit.draw(lay)
    assert layouts.finish(fig, lay, {})
    assert kit.tags(fig) == ["a", "b", "c"]
