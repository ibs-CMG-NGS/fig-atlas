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


def test_crowded_texts_and_uneven_titles_are_reported_as_info():
    import matplotlib.pyplot as plt
    from fig_atlas.preflight import preflight
    fig = plt.figure(figsize=(4.0, 2.0))
    a = fig.add_axes([0.1, 0.2, 0.35, 0.55])
    b = fig.add_axes([0.6, 0.2, 0.35, 0.45])            # lower top edge: its title sits lower
    a.set_title("Left panel", fontsize=7)
    b.set_title("Right panel", fontsize=7)
    # two labels 0.2 mm apart, one above the other (in inches from the figure corner)
    fig.text(0.5, 0.15, "upper label", va="bottom", fontsize=6, transform=fig.dpi_scale_trans)
    fig.text(0.5, 0.15 - 0.2 / 25.4, "lower label", va="top", fontsize=6, transform=fig.dpi_scale_trans)
    found = {f.check: f for f in preflight(fig, saved_bbox_in="tight")}
    assert found["title_misaligned"].severity == "info"
    assert found["text_crowded"].severity == "info"
    plt.close(fig)

    fig = plt.figure(figsize=(4.0, 2.0))
    for x in (0.1, 0.6):
        ax = fig.add_axes([x, 0.2, 0.35, 0.55])
        ax.set_title("Panel", fontsize=7)
    found = {f.check for f in preflight(fig, saved_bbox_in="tight")}
    assert "title_misaligned" not in found and "text_crowded" not in found
    plt.close(fig)


def test_title_starts_at_the_tick_labels():
    import matplotlib.pyplot as plt
    from fig_atlas.renderers import align_title_to_labels
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.barh([0, 1], [3, 5])
    ax.set_yticks([0, 1], ["a long category name", "short"])
    title = ax.set_title("Title", loc="left")
    align_title_to_labels(ax)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    labels = min(t.get_window_extent(r).x0 for t in ax.get_yticklabels())
    assert abs(title.get_window_extent(r).x0 - labels) < 1.0
    plt.close(fig)


def test_panel_reaching_into_its_neighbour_is_reported():
    """A title moved left over the neighbour's whitespace: no text lies on the
    neighbour's plot area, yet the two panels' regions interleave."""
    import matplotlib.pyplot as plt
    from fig_atlas.preflight import preflight
    fig = plt.figure(figsize=(6.0, 2.5))
    a = fig.add_axes([0.08, 0.15, 0.4, 0.6])
    b = fig.add_axes([0.62, 0.15, 0.3, 0.6])
    a.set_title("Left", loc="left")
    b.set_title("A long title that starts far left", loc="left").set_x(-0.6)
    found = {f.check: f for f in preflight(fig, saved_bbox_in="tight")}
    assert found["panel_regions_overlap"].severity == "warn"
    assert "panel_intrusion" not in found
    plt.close(fig)

    fig = plt.figure(figsize=(6.0, 2.5))
    for x in (0.08, 0.62):
        fig.add_axes([x, 0.15, 0.3, 0.6]).set_title("Panel", loc="left")
    assert "panel_regions_overlap" not in {f.check for f in preflight(fig, saved_bbox_in="tight")}
    plt.close(fig)


def test_journal_text_cap_and_column_widths():
    import matplotlib.pyplot as plt
    from fig_atlas.preflight import preflight
    fig = plt.figure(figsize=(150 / 25.4, 60 / 25.4))
    ax = fig.add_axes([0.15, 0.2, 0.7, 0.6])
    ax.set_title("Eight-point title", fontsize=8)
    ax.tick_params(labelsize=6)
    fig.text(0.01, 0.95, "a", fontsize=8, fontweight="bold", va="top")      # a tag: not capped
    params = {"max_font_pt": 7, "allowed_widths_mm": [89, 183]}
    found = {f.check: f for f in preflight(fig, saved_bbox_in=None, params=params)}
    assert found["print_font_too_large"].measured == 8.0
    assert "1 text(s)" in found["print_font_too_large"].message          # the title, not the tag
    assert found["width_not_journal_column"].measured == 150.0
    plt.close(fig)

    fig = plt.figure(figsize=(183 / 25.4, 60 / 25.4))
    fig.add_axes([0.15, 0.2, 0.7, 0.6]).set_title("Seven", fontsize=7)
    checks = {f.check for f in preflight(fig, saved_bbox_in=None, params=params)}
    assert not {"print_font_too_large", "width_not_journal_column"} & checks
    plt.close(fig)
