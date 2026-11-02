"""Composition: a layout called on a cell of another (plans/PLAN_LAYOUT_CATALOG.md,
section 16, card L-15). The inner layout starts with the cell's letter,
registers itself on the cell, and ``finish`` -- called once, on the outer
layout -- fits its panels and joins their letters to the outer plumb lines
and rows."""
from __future__ import annotations

import pytest

from fig_atlas import layouts
from fig_atlas.renderers.panels import PANEL_TAG_GID

FCFG = {"wspace": 0.1, "hspace": 0.12}


def _draw(cells, letters):
    for letter in letters:
        ax = cells[letter].add_subplot(1, 1, 1)
        ax.plot([0, 1], [1, 0])
        ax.set_title("panel")


def _tag_boxes(fig):
    fig.canvas.draw()
    return {t.get_text(): t.get_window_extent() for t in fig.texts if t.get_gid() == PANEL_TAG_GID}


def _inside(inner, outer, tol=1e-6):
    a, b = inner.bbox, outer.bbox
    return b.x0 - tol <= a.x0 and a.x1 <= b.x1 + tol and b.y0 - tol <= a.y0 and a.y1 <= b.y1 + tol


def test_stack_of_rows(fig, kit):
    """A stack whose middle cell is split into a row: the figure reads a-e."""
    outer = layouts.stack(fig, FCFG, letters=("a", "b", "e"))
    inner = layouts.row(outer.cells["b"], FCFG, letters=("b", "c", "d"))
    _draw(outer.cells, "ae")
    _draw(inner.cells, "bcd")
    layouts.finish(fig, outer, FCFG)

    assert all(_inside(inner.cells[l], outer.cells["b"]) for l in "bcd")
    assert kit.overlap(inner.cells["b"], inner.cells["c"]) == 0.0
    assert not list(outer.cells["b"].axes)                 # the split cell draws nothing itself
    boxes = _tag_boxes(fig)
    assert sorted(boxes) == list("abcde")
    assert boxes["a"].x0 == pytest.approx(boxes["b"].x0) == pytest.approx(boxes["e"].x0)   # one plumb line
    assert boxes["b"].y0 == pytest.approx(boxes["c"].y0) == pytest.approx(boxes["d"].y0)   # one row


def test_row_with_a_stack(fig):
    """The mirror: a tall left panel beside a stack (the gs[:, 0] shape)."""
    outer = layouts.row(fig, FCFG, letters=("a", "b"))
    right = layouts.stack(outer.cells["b"], FCFG, letters=("b", "c"))
    _draw(outer.cells, "a")
    _draw(right.cells, "bc")
    layouts.finish(fig, outer, FCFG)
    boxes = _tag_boxes(fig)
    assert sorted(boxes) == list("abc")
    assert boxes["b"].x0 == pytest.approx(boxes["c"].x0)    # the stack's plumb line
    assert boxes["a"].y0 == pytest.approx(boxes["b"].y0)    # a and b head the same row


def test_values_under_the_cell_letter(fig):
    """Two cells split the same way keep their own numbers; nothing leaks between levels."""
    fcfg = {"cells": {"a": {"row": {"width_ratios": [2, 1]}},
                      "c": {"row": {"width_ratios": [1, 3]}, "wspace": 0.2}}}
    outer = layouts.stack(fig, fcfg, letters=("a", "c"))
    top = layouts.row(outer.cells["a"], fcfg, letters=("a", "b"))
    bottom = layouts.row(outer.cells["c"], fcfg, letters=("c", "d"))
    assert top.cells["a"].bbox.width == pytest.approx(2 * top.cells["b"].bbox.width, rel=1e-6)
    assert bottom.cells["d"].bbox.width == pytest.approx(3 * bottom.cells["c"].bbox.width, rel=1e-6)
    assert bottom.cells["d"].bbox.x0 - bottom.cells["c"].bbox.x1 > 0          # cell c's own wspace
    assert top.cells["b"].bbox.x0 - top.cells["a"].bbox.x1 == pytest.approx(0.0, abs=1e-9)
    assert outer.cells["c"].bbox.y1 == pytest.approx(outer.cells["a"].bbox.y0)  # the outer stack: no gap


def test_inner_layout_starts_with_the_cell_letter(fig):
    outer = layouts.stack(fig, {}, letters=("a", "b"))
    with pytest.raises(ValueError, match="starts with 'b'"):
        layouts.row(outer.cells["b"], {}, letters=("c", "d"))


def test_a_cell_holds_one_layout(fig):
    outer = layouts.stack(fig, {}, letters=("a", "b"))
    layouts.row(outer.cells["b"], {}, letters=("b", "c"))
    with pytest.raises(ValueError, match="already holds a layout"):
        layouts.row(outer.cells["b"], {}, letters=("b", "d"))


def test_two_levels_at_most(fig):
    outer = layouts.stack(fig, {}, letters=("a", "b"))
    inner = layouts.row(outer.cells["b"], {}, letters=("b", "c"))
    with pytest.raises(ValueError, match="2 levels at most"):
        layouts.stack(inner.cells["c"], {}, letters=("c", "d"))


def test_a_letter_used_twice_across_levels_fails_at_finish(fig):
    outer = layouts.stack(fig, {}, letters=("a", "b", "c"))
    inner = layouts.row(outer.cells["b"], {}, letters=("b", "c"))
    _draw(outer.cells, "ac")
    _draw(inner.cells, "bc")
    with pytest.raises(ValueError, match="'c' is used twice"):
        layouts.finish(fig, outer, {})


def test_finish_without_composition_is_unchanged(fig, kit):
    lay = layouts.grid(fig, {}, "abcd", columns=2)
    kit.draw(lay)
    layouts.finish(fig, lay, {})
    assert kit.tags(fig) == list("abcd")
