"""Layout-rule and consistency checks of preflight (Phase 3.4): tick labels
that nearly touch, panel tag alignment/style, font-size outliers."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.preflight import MM_PER_INCH, preflight  # noqa: E402
from fig_atlas.renderers import place_panel_tags  # noqa: E402


@pytest.fixture(autouse=True)
def _clean():
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams["font.size"] = 7
        yield
    plt.close("all")


def found(fig):
    return {f.check for f in preflight(fig, saved_bbox_in="tight")}


def touching_ticks(gap_mm: float):
    """Two x tick labels whose ink boxes are ``gap_mm`` apart: place the
    second tick from the first label's measured width."""
    fig, ax = plt.subplots(figsize=(3.0, 1.5))
    ax.set_xlim(0, 10)
    ax.set_xticks([2, 5], ["24h", "48h"])
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    a, b = ax.get_xticklabels()
    w_mm = (a.get_window_extent(r).width + b.get_window_extent(r).width) / 2 / fig.dpi * MM_PER_INCH
    mm_per_unit = ax.get_window_extent(r).width / fig.dpi * MM_PER_INCH / 10
    ax.set_xticks([2, 2 + (w_mm + gap_mm) / mm_per_unit], ["24h", "48h"])
    return fig


def test_touching_tick_labels_reported():
    assert "tick_labels_touching" in found(touching_ticks(0.1))


def test_sliver_overlap_below_collision_threshold_is_touching():
    # Boxes overlapping by a hair: too little for tick_label_collision, but
    # the labels still run together ("24h48h").
    checks = found(touching_ticks(-0.05))
    assert "tick_labels_touching" in checks and "tick_label_collision" not in checks


def test_spaced_tick_labels_are_clean():
    assert "tick_labels_touching" not in found(touching_ticks(2.0))


def _two_stacked(tag_offset_mm: float, styles=None):
    fig = plt.figure(figsize=(3.0, 3.0))
    a = fig.add_axes([0.2, 0.58, 0.7, 0.35])
    b = fig.add_axes([0.2, 0.1, 0.7, 0.35])
    a.plot([0, 1], [0, 1])
    b.plot([0, 1], [1, 0])
    tags = place_panel_tags(fig, [[("a", [a]), ("b", [b])]], 10)
    if tag_offset_mm:
        x, y = tags[1].get_position()
        tags[1].set_x(x + tag_offset_mm / MM_PER_INCH / 3.0)
    for t, style in zip(tags, styles or []):
        t.set(**style)
    return fig


def test_misaligned_tags_reported():
    assert "panel_tag_misaligned" in found(_two_stacked(1.5))


def test_place_panel_tags_alignment_is_clean():
    f = found(_two_stacked(0.0))
    assert not {"panel_tag_misaligned", "panel_tag_inconsistent"} & f


def test_inconsistent_tag_style_reported():
    assert "panel_tag_inconsistent" in found(_two_stacked(0.0, [{}, {"fontweight": "normal"}]))


def test_journal_tag_case_reported():
    fig = _two_stacked(0.0)
    checks = {f.check for f in preflight(fig, "tight", params={"panel_tag_case": "upper"})}
    assert "panel_tag_style" in checks


def _grid(sizes):
    fig, axes = plt.subplots(2, 2, figsize=(3.4, 3.0), layout="constrained")
    for ax, s in zip(axes.flat, sizes):
        ax.plot([0, 1], [0, 1])
        ax.tick_params(labelsize=s)
    return fig


def test_font_size_outlier_reported():
    assert "font_size_outlier" in found(_grid([6, 6, 6, 7]))


def test_uniform_font_sizes_are_clean():
    assert "font_size_outlier" not in found(_grid([6, 6, 6, 6]))


def test_profile_is_returned():
    prof = {}
    preflight(_grid([6, 6, 6, 6]), "tight", profile=prof)
    assert set(prof["tick"]) == {6.0}
