"""``layouts.stack``: one column of panels."""
from __future__ import annotations

import pytest

from fig_atlas import layouts


def test_cells_and_tag_groups(fig):
    lay = layouts.stack(fig, {}, "abc")
    assert sorted(lay.cells) == ["a", "b", "c"]
    assert lay.shape == "3 stacked rows"
    assert lay.columns == [["a", "b", "c"]]        # one plumb line for the cluster
    assert lay.rows == [["a"], ["b"], ["c"]]


def test_one_column_top_to_bottom(fig, kit):
    lay = layouts.stack(fig, {}, "abc")
    a, b, c = (lay.cells[l] for l in "abc")
    assert a.bbox.x0 == pytest.approx(b.bbox.x0, abs=1e-9)
    assert a.bbox.width == pytest.approx(b.bbox.width, abs=1e-9)
    assert a.bbox.y0 >= b.bbox.y1 and b.bbox.y0 >= c.bbox.y1     # default: no gap
    for i, first in enumerate(lay.cells.values()):
        for second in list(lay.cells.values())[i + 1:]:
            assert kit.overlap(first, second) == 0.0


def test_hspace_separates_rows(fig):
    lay = layouts.stack(fig, {"hspace": 0.2}, "ab")
    a, b = lay.cells["a"], lay.cells["b"]
    assert a.bbox.y0 - b.bbox.y1 == pytest.approx(0.2 * b.bbox.height, rel=1e-6)


def test_height_ratios_from_config(fig):
    lay = layouts.stack(fig, {"stack": {"height_ratios": [1.0, 2.0]}}, "ab")
    a, b = lay.cells["a"], lay.cells["b"]
    assert b.bbox.height == pytest.approx(2 * a.bbox.height, rel=1e-6)


def test_height_ratios_argument_wins(fig):
    lay = layouts.stack(fig, {"stack": {"height_ratios": [1.0, 1.0]}}, "ab",
                        height_ratios=[3.0, 1.0])
    a, b = lay.cells["a"], lay.cells["b"]
    assert a.bbox.height == pytest.approx(3 * b.bbox.height, rel=1e-6)


def test_height_ratios_count_is_checked(fig):
    with pytest.raises(ValueError, match="height ratio"):
        layouts.stack(fig, {"stack": {"height_ratios": [1.0]}}, "ab")


def test_finish_places_every_tag(fig, kit):
    lay = layouts.stack(fig, {}, "abc")
    kit.draw(lay)
    assert layouts.finish(fig, lay, {})
    assert kit.tags(fig) == ["a", "b", "c"]
