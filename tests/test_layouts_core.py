"""The layout core: letters, cells, tags, and parity with ``draw_plots``.

``layouts.grid`` must build the same cells ``fig_atlas.bundle_figure.draw_plots``
builds from the same panel count and ``figures.columns`` -- that parity is what
lets a script move from ``draw_plots`` to an explicit layout without the figure
changing (plans/PLAN_LAYOUT_CATALOG.md, card L-05).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from fig_atlas import bundle_figure, layouts  # noqa: E402
from fig_atlas.renderers.panels import PANEL_TAG_GID  # noqa: E402


def _bounds(sf) -> list:
    return [sf.bbox.x0, sf.bbox.y0, sf.bbox.width, sf.bbox.height]


def _draw(cell, title: str = "") -> None:
    ax = cell.add_subplot(1, 1, 1)
    ax.plot([0, 1], [1, 0])
    if title:
        ax.set_title(title)


def _tags(fig) -> list:
    return [t.get_text() for t in fig.texts if t.get_gid() == PANEL_TAG_GID]


@pytest.mark.parametrize("letters", ["", ("a", "a"), ("a", "A"), ("aa",), ("1",), (1,)])
def test_letters_are_validated(letters):
    fig = plt.figure()
    with pytest.raises(ValueError):
        layouts.grid(fig, {}, letters)
    plt.close(fig)


@pytest.mark.parametrize("name", ["grid", "stack", "matrix", "row"])
def test_shape_and_cells(name):
    fig = plt.figure(figsize=(6, 4))
    lay = getattr(layouts, name)(fig, {}, "abcd")
    assert sorted(lay.cells) == ["a", "b", "c", "d"]
    assert isinstance(lay.shape, str) and lay.shape
    assert sorted(l for group in lay.columns for l in group) == ["a", "b", "c", "d"]
    plt.close(fig)


def test_grid_columns_default_and_argument():
    fig = plt.figure(figsize=(6, 4))
    lay = layouts.grid(fig, {}, "abcdefgh")
    assert lay.shape == "3x3 equal grid"            # default: 3 columns
    lay = layouts.grid(fig, {"columns": 4}, "abcdefgh")
    assert lay.shape == "2x4 equal grid"            # the config sets it
    lay = layouts.grid(fig, {"columns": 4}, "abcdefgh", columns=2)
    assert lay.shape == "4x2 equal grid"            # the argument wins
    plt.close(fig)


def test_grid_one_panel():
    """A single panel is grid(columns=1), not a layout of its own (G1)."""
    fig = plt.figure(figsize=(3, 3))
    lay = layouts.grid(fig, {}, "a", columns=1)
    assert lay.shape == "1x1 equal grid"
    assert lay.columns == [["a"]] and lay.rows == [["a"]]
    plt.close(fig)


def test_finish_places_tags():
    fig = plt.figure(figsize=(6, 4))
    lay = layouts.grid(fig, {}, "ab")
    for cell in lay.cells.values():
        _draw(cell, title="panel")
    tags = layouts.finish(fig, lay, {})
    assert sorted(_tags(fig)) == ["a", "b"]
    assert len(tags) == 2
    plt.close(fig)


def test_finish_honours_tag_config():
    fig = plt.figure(figsize=(6, 4))
    fcfg = {"tags": {"show": False}}
    lay = layouts.grid(fig, fcfg, "ab")
    for cell in lay.cells.values():
        _draw(cell)
    assert layouts.finish(fig, lay, fcfg) == []
    assert _tags(fig) == []
    plt.close(fig)


def test_finish_moves_axes_inside_the_cell():
    """fit_in_cells runs: every drawn axes stays inside its subfigure's cell."""
    fig = plt.figure(figsize=(6, 4))
    lay = layouts.grid(fig, {}, "ab")
    for cell in lay.cells.values():
        ax = cell.add_subplot(1, 1, 1)
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("a long axis title that needs the outer bounding box")
    layouts.finish(fig, lay, {})
    for letter, cell in lay.cells.items():
        for ax in cell.axes:
            box = ax.get_window_extent()                 # display pixels, like cell.bbox
            assert cell.bbox.x0 - 1e-6 <= box.x0 and box.x1 <= cell.bbox.x1 + 1e-6, letter
            assert cell.bbox.y0 - 1e-6 <= box.y0 and box.y1 <= cell.bbox.y1 + 1e-6, letter
    plt.close(fig)


def test_grid_matches_draw_plots(monkeypatch):
    """Same cells, same tag groups as draw_plots (the migration path)."""

    def painter(ax, df, params):                     # shape ("ax", "df"): drawable
        ax.plot([0, 1], [1, 0])

    monkeypatch.setattr(bundle_figure, "resolve", lambda target: painter)
    fcfg = {"columns": 3}
    plots = {f"p{i}": {"renderer": "stub:painter"} for i in range(7)}

    fig_a = plt.figure(figsize=(6, 4))
    columns = bundle_figure.draw_plots(fig_a, plots, Path("."), fcfg,
                                       load=lambda name, block: None)
    fig_b = plt.figure(figsize=(6, 4))
    lay = layouts.grid(fig_b, fcfg, "abcdefg")

    assert len(fig_a.subfigs) == len(fig_b.subfigs) == 7
    for sf_a, sf_b in zip(fig_a.subfigs, fig_b.subfigs):
        assert _bounds(sf_a) == pytest.approx(_bounds(sf_b), abs=1e-9)
    assert [[letter for letter, axes in column] for column in columns] == lay.columns
    plt.close(fig_a)
    plt.close(fig_b)


def test_grid_parity_with_four_columns(monkeypatch):
    def painter(ax, df, params):
        ax.plot([0, 1], [0, 1])

    monkeypatch.setattr(bundle_figure, "resolve", lambda target: painter)
    fcfg = {"columns": 4}
    plots = {f"p{i}": {"renderer": "stub:x"} for i in range(5)}

    fig_a = plt.figure(figsize=(6, 4))
    bundle_figure.draw_plots(fig_a, plots, Path("."), fcfg, load=lambda name, block: None)
    fig_b = plt.figure(figsize=(6, 4))
    lay = layouts.grid(fig_b, fcfg, "abcde")
    for sf_a, sf_b in zip(fig_a.subfigs, fig_b.subfigs):
        assert _bounds(sf_a) == pytest.approx(_bounds(sf_b), abs=1e-9)
    plt.close(fig_a)
    plt.close(fig_b)


def test_gaps_are_real_and_follow_the_gridspec_convention():
    """matplotlib ignores wspace on a SubFigure, so layouts make the gap a
    separator row/column of ``wspace * mean(cell)`` (as add_subplot would)."""
    fig = plt.figure(figsize=(6, 4))
    plain = layouts.grid(fig, {}, "ab", columns=2)
    gap = plain.cells["b"].bbox.x0 - plain.cells["a"].bbox.x1
    assert gap == pytest.approx(0.0, abs=1e-9)          # default: draw_plots' cells

    fig2 = plt.figure(figsize=(6, 4))
    spaced = layouts.grid(fig2, {"wspace": 0.25}, "ab", columns=2)
    a, b = spaced.cells["a"], spaced.cells["b"]
    gap = b.bbox.x0 - a.bbox.x1
    assert gap == pytest.approx(0.25 * a.bbox.width, rel=1e-6)
    plt.close(fig)
    plt.close(fig2)


def test_grid_ratios_from_argument_and_config():
    """Rows and columns of different sizes (L-13); unset, the cells stay equal."""
    fig = plt.figure(figsize=(6, 4))
    lay = layouts.grid(fig, {}, "abcd", columns=2, width_ratios=[2, 1], height_ratios=[1, 3])
    a, b, c = lay.cells["a"], lay.cells["b"], lay.cells["c"]
    assert a.bbox.width == pytest.approx(2 * b.bbox.width, rel=1e-6)
    assert c.bbox.height == pytest.approx(3 * a.bbox.height, rel=1e-6)
    assert lay.shape == "2x2 grid"
    from_config = layouts.grid(fig, {"grid": {"width_ratios": [2, 1]}}, "abcd", columns=2)
    assert from_config.cells["a"].bbox.width == pytest.approx(2 * from_config.cells["b"].bbox.width, rel=1e-6)
    argument_wins = layouts.grid(fig, {"grid": {"width_ratios": [2, 1]}}, "abcd", columns=2, width_ratios=[1, 1])
    assert argument_wins.cells["a"].bbox.width == pytest.approx(argument_wins.cells["b"].bbox.width, rel=1e-6)
    plt.close(fig)


@pytest.mark.parametrize("name", ["grid", "matrix"])
def test_ratios_need_one_number_per_row_or_column(name):
    fig = plt.figure(figsize=(6, 4))
    with pytest.raises(ValueError, match=r"one number per column \(2\)"):
        getattr(layouts, name)(fig, {}, "abcd", columns=2, width_ratios=[1, 1, 1])
    with pytest.raises(ValueError, match=r"one number per row \(2\)"):
        getattr(layouts, name)(fig, {name: {"height_ratios": [1]}}, "abcd", columns=2)
    plt.close(fig)


def test_draw_plot_draws_one_block_into_a_layout_cell():
    """draw_plot (what draw_plots does per panel) into a layout's cell: the data
    from load() when the block has no bundle, the axes inside the cell."""
    import pandas as pd
    fig = plt.figure(figsize=(6, 3))
    lay = layouts.row(fig, {}, "ab")
    block = {"renderer": "fig_atlas.renderers:render_line_band", "x_col": "x", "y_col": "y"}
    loaded = []

    def load(name, blk):
        loaded.append(name)
        return pd.DataFrame({"x": [0, 1, 2, 0, 1, 2], "y": [1.0, 2.0, 3.0, 1.2, 2.1, 2.9]})

    axes = bundle_figure.draw_plot(lay.cells["b"], "curve", block, Path("."), load=load)
    assert loaded == ["curve"] and axes and all(ax.figure is lay.cells["b"] for ax in axes)
    assert not list(lay.cells["a"].axes)
    with pytest.raises(ValueError, match="names no renderer"):
        bundle_figure.draw_plot(lay.cells["a"], "x", {}, Path("."))
    plt.close(fig)


def test_fixed_size_keeps_the_printed_size_and_the_cell_corner():
    """figures.cells.<letter>.size_mm: the panel's axes keep that size (mm) and its
    outer box starts at the cell's top-left corner; the other panels are fitted."""
    from matplotlib.transforms import Bbox
    fig = plt.figure(figsize=(160 / 25.4, 70 / 25.4), dpi=100)
    fcfg = {"wspace": 0.1, "panel_pad_mm": 1.0, "cells": {"b": {"size_mm": [40, 30]}},
            "tags": {"size": 9.0, "pad_pt": 2.0}}
    lay = layouts.row(fig, fcfg, "abc")
    for letter in "abc":
        _draw(lay.cells[letter], title=letter)
    layouts.finish(fig, lay, fcfg)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    mm = 25.4 / fig.dpi
    (b,) = lay.cells["b"].axes
    box = b.get_window_extent(r)
    assert box.width * mm == pytest.approx(40, abs=0.05) and box.height * mm == pytest.approx(30, abs=0.05)
    cell, outer = lay.cells["b"].bbox, Bbox.union([b.get_tightbbox(r)])
    assert (outer.x0 - cell.x0) * mm == pytest.approx(1.0, abs=0.05)
    assert (cell.y1 - outer.y1) * mm == pytest.approx(1.0 + 11.0 * 25.4 / 72, abs=0.05)   # pad + tag reserve
    (a,) = lay.cells["a"].axes
    assert (lay.cells["a"].bbox.x1 - a.get_tightbbox(r).x1) * mm == pytest.approx(1.0, abs=0.05)   # a still fitted
    assert "b" in _tags(fig)
    plt.close(fig)


def test_mm_axes_keep_the_drawn_size_and_move_to_the_cell_corner():
    """layouts.mm_axes: axes set out in mm inside a cell keep their sizes and their
    arrangement; finish moves the panel to the cell's top-left corner, no size_mm needed."""
    from matplotlib.transforms import Bbox
    fig = plt.figure(figsize=(160 / 25.4, 70 / 25.4), dpi=100)
    fcfg = {"panel_pad_mm": 1.0, "tags": {"size": 9.0, "pad_pt": 2.0}}
    lay = layouts.row(fig, fcfg, "ab")
    left = layouts.mm_axes(lay.cells["a"], 10, 12, 30, 20)
    right = layouts.mm_axes(lay.cells["a"], 45, 12, 15, 20)
    _draw(lay.cells["b"])
    layouts.finish(fig, lay, fcfg)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    mm = 25.4 / fig.dpi
    lb, rb = left.get_window_extent(r), right.get_window_extent(r)
    assert lb.width * mm == pytest.approx(30, abs=0.05) and lb.height * mm == pytest.approx(20, abs=0.05)
    assert rb.width * mm == pytest.approx(15, abs=0.05)
    assert (rb.x0 - lb.x1) * mm == pytest.approx(5, abs=0.05)                  # the gap drawn stays
    cell, outer = lay.cells["a"].bbox, Bbox.union([a.get_tightbbox(r) for a in (left, right)])
    assert (outer.x0 - cell.x0) * mm == pytest.approx(1.0, abs=0.05)
    assert (cell.y1 - outer.y1) * mm == pytest.approx(1.0 + 11.0 * 25.4 / 72, abs=0.05)
    assert "a" in _tags(fig)
    plt.close(fig)


def test_mm_axes_and_size_mm_on_one_cell_is_an_error():
    fig = plt.figure(figsize=(6, 3))
    fcfg = {"cells": {"a": {"size_mm": [30, 20]}}}
    lay = layouts.row(fig, fcfg, "ab")
    layouts.mm_axes(lay.cells["a"], 0, 0, 30, 20)
    with pytest.raises(ValueError, match="drawn with mm_axes"):
        layouts.finish(fig, lay, fcfg)
    with pytest.raises(ValueError, match="positive"):
        layouts.mm_axes(lay.cells["b"], 0, 0, 0, 20)
    plt.close(fig)


@pytest.mark.parametrize("size", [[40], "40x30", [40, 0], [-1, 30]])
def test_fixed_size_must_be_a_positive_width_and_height(size):
    fig = plt.figure(figsize=(6, 3))
    fcfg = {"cells": {"a": {"size_mm": size}}}
    lay = layouts.row(fig, fcfg, "ab")
    _draw(lay.cells["a"])
    with pytest.raises(ValueError, match=r"figures\.cells\.a\.size_mm"):
        layouts.finish(fig, lay, fcfg)
    plt.close(fig)
