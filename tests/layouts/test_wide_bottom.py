"""``layouts.wide_bottom``: a top row and one full-width panel beneath it."""
from __future__ import annotations

import pytest

from fig_atlas import layouts


def test_cells_and_tag_groups(fig):
    lay = layouts.wide_bottom(fig, {}, top=("a", "b"), bottom="c")
    assert sorted(lay.cells) == ["a", "b", "c"]
    assert lay.shape == "2 columns + full-width bottom row"
    assert lay.columns == [["a", "c"], ["b"]]      # the wide panel starts in column 0
    assert lay.rows == [["a", "b"], ["c"]]


def test_bottom_spans_the_full_width(fig):
    lay = layouts.wide_bottom(fig, {}, top=("a", "b", "c"), bottom="d")
    a, b, c, d = (lay.cells[l] for l in "abcd")
    total = (a.bbox.width + b.bbox.width + c.bbox.width)
    assert d.bbox.width > total * 0.95            # covers every column
    assert d.bbox.x0 == pytest.approx(a.bbox.x0, abs=1e-9)
    assert d.bbox.x1 == pytest.approx(c.bbox.x1, abs=1e-9)


def test_cells_do_not_overlap_and_bottom_is_below(fig, kit):
    lay = layouts.wide_bottom(fig, {}, top=("a", "b"), bottom="c")
    cells = list(lay.cells.values())
    for i, first in enumerate(cells):
        for second in cells[i + 1:]:
            assert kit.overlap(first, second) == 0.0
    a, b, c = (lay.cells[l] for l in "abc")
    assert c.bbox.y1 <= a.bbox.y0 + 1e-9
    assert c.bbox.y1 <= b.bbox.y0 + 1e-9


def test_height_ratios_from_config(fig):
    lay = layouts.wide_bottom(fig, {"wide_bottom": {"height_ratios": [1.0, 2.0]}},
                              top=("a", "b"), bottom="c")
    a, c = lay.cells["a"], lay.cells["c"]
    assert c.bbox.height == pytest.approx(2 * a.bbox.height, rel=1e-6)


def test_height_ratios_count_is_checked(fig):
    with pytest.raises(ValueError, match="height_ratios"):
        layouts.wide_bottom(fig, {"wide_bottom": {"height_ratios": [1.0, 2.0, 3.0]}},
                            top=("a", "b"), bottom="c")


def test_hspace_separates_rows(fig):
    lay = layouts.wide_bottom(fig, {"hspace": 0.2}, top=("a", "b"), bottom="c")
    a, c = lay.cells["a"], lay.cells["c"]
    assert a.bbox.y0 - c.bbox.y1 == pytest.approx(0.2 * a.bbox.height, rel=1e-6)


def test_one_top_panel_points_to_stack(fig):
    with pytest.raises(ValueError, match="stack"):
        layouts.wide_bottom(fig, {}, top=("a",), bottom="b")


def test_finish_places_every_tag(fig, kit):
    fcfg = {"tags": {"size": 10.0}}
    lay = layouts.wide_bottom(fig, fcfg, top=("a", "b"), bottom="c")
    kit.draw(lay)
    lay_finish = layouts.finish(fig, lay, fcfg)
    assert kit.tags(fig) == ["a", "b", "c"]
    assert len(lay_finish) == 3
