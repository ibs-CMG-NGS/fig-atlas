"""Preflight checks (fig_atlas/preflight.py) on seeded-defect fixtures.

Each case is a pair: the same figure with one deliberate defect, and a clean
twin. The defect must be reported with the expected check at severity
"error" (recall), and the twin must produce no errors (no false alarms).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.preflight import preflight  # noqa: E402

LONG = [f"condition label {i}" for i in range(8)]


def _bars(ax, labels, rotation=0):
    ax.bar(range(len(labels)), np.arange(1, len(labels) + 1))
    ax.set_xticks(range(len(labels)), labels, rotation=rotation, fontsize=7,
                  ha="right" if rotation not in (0, 90) else "center")


# --------------------------------------------------------------- the pairs --
def tick_collision(defect: bool):
    fig, ax = plt.subplots(figsize=(3.0, 2.2), layout="constrained")
    _bars(ax, LONG, rotation=0 if defect else 90)
    return fig, None


def rotated_tick_collision(defect: bool):
    # 45-degree labels: adjacent labels are parallel diagonal strips; they
    # collide only when the tick spacing is below the text height.
    fig, ax = plt.subplots(figsize=(3.0 if defect else 6.0, 2.4))
    _bars(ax, LONG * (5 if defect else 1), rotation=45)
    return fig, "tight"


def cross_panel_overlap(defect: bool):
    # Stacked panels: the upper panel's x-axis title runs into the lower
    # panel's title when the vertical gap is too small.
    fig = plt.figure(figsize=(3.0, 3.2))
    gap = 0.0 if defect else 0.12
    top = fig.add_axes([0.18, 0.56, 0.75, 0.38])
    bottom = fig.add_axes([0.18, 0.12, 0.75, 0.38 - gap])
    top.plot([0, 1], [0, 1])
    top.set_xlabel("Time after treatment (h)")
    bottom.plot([0, 1], [1, 0])
    bottom.set_title("Recovery of the response")
    return fig, "tight"


def cross_subfigure_overlap(defect: bool):
    # The same overlap with each panel in its own subfigure (as
    # bundle_figure.draw_plots lays panels out): both axes sit at the same
    # position *within their subfigure*, which once made them one "panel".
    fig = plt.figure(figsize=(3.0, 3.2))
    upper, lower = fig.subfigures(2, 1, hspace=0.0)
    rect = [0.18, 0.04, 0.75, 0.9] if defect else [0.18, 0.3, 0.75, 0.5]
    top, bottom = upper.add_axes(rect), lower.add_axes(rect)
    top.plot([0, 1], [0, 1])
    top.set_xlabel("Time after treatment (h)")
    bottom.plot([0, 1], [1, 0])
    bottom.set_title("Recovery of the response")
    return fig, "tight"


def legend_over_panel(defect: bool):
    fig = plt.figure(figsize=(4.4, 2.0))
    a = fig.add_axes([0.1, 0.18, 0.36, 0.72])
    b = fig.add_axes([0.6, 0.18, 0.36, 0.72])
    for s in range(3):
        a.plot([0, 1], [s, s + 1], label=f"series {s}")
    b.plot([0, 1], [1, 0])
    if defect:   # anchored to the right of panel a -- straight into panel b
        a.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
    else:
        a.legend(loc="upper left")
    return fig, "tight"


def clipped_title(defect: bool):
    fig, ax = plt.subplots(figsize=(2.6, 2.0))
    fig.subplots_adjust(left=0.2, bottom=0.2, top=0.97 if defect else 0.8)
    ax.plot([0, 1], [0, 1])
    ax.set_title("A title that needs room", fontsize=8)
    return fig, None   # plain savefig: canvas is the saved area


def panel_overlap(defect: bool):
    fig = plt.figure(figsize=(4.0, 2.4))
    a = fig.add_axes([0.1, 0.15, 0.45, 0.75])
    b = fig.add_axes([0.45 if defect else 0.66, 0.15, 0.3, 0.75])
    a.plot([0, 1], [0, 1])
    b.plot([0, 1], [1, 0])
    return fig, None


def tick_labels_into_neighbour(defect: bool):
    # Panel a's right-side tick labels run into panel b's plot area.
    fig = plt.figure(figsize=(4.0, 2.2))
    gap = 0.01 if defect else 0.2
    a = fig.add_axes([0.08, 0.2, 0.33, 0.7])
    b = fig.add_axes([0.41 + gap, 0.2, 0.33, 0.7])
    a.plot([0, 1], [0, 1000000])
    a.yaxis.tick_right()
    b.plot([0, 1], [0, 1])
    return fig, "tight"


CASES = {
    "tick_collision": ("tick_label_collision", tick_collision),
    "rotated_tick_collision": ("tick_label_collision", rotated_tick_collision),
    "cross_panel_overlap": ("cross_panel_text_overlap", cross_panel_overlap),
    "cross_subfigure_overlap": ("panel_intrusion", cross_subfigure_overlap),
    "legend_over_panel": ("legend_overlaps_panel", legend_over_panel),
    "clipped_title": ("clipped_by_saved_area", clipped_title),
    "panel_overlap": ("panel_overlap", panel_overlap),
    "tick_labels_into_neighbour": ("panel_intrusion", tick_labels_into_neighbour),
}


@pytest.fixture(autouse=True)
def _clean():
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams["font.size"] = 7   # print-size text, as in the paper figures
        yield
    plt.close("all")


@pytest.mark.parametrize("name", sorted(CASES))
def test_defect_is_reported(name):
    check, make = CASES[name]
    fig, saved = make(defect=True)
    found = preflight(fig, saved_bbox_in=saved)
    assert any(f.check == check and f.severity == "error" for f in found), \
        f"{name}: expected {check}, got {[(f.check, f.severity, f.message) for f in found]}"


@pytest.mark.parametrize("name", sorted(CASES))
def test_clean_twin_has_no_errors(name):
    _, make = CASES[name]
    fig, saved = make(defect=False)
    errors = [f for f in preflight(fig, saved_bbox_in=saved) if f.severity == "error"]
    assert not errors, f"{name} clean twin: {[(f.check, f.message) for f in errors]}"


def test_colorbar_and_inset_are_part_of_their_panel():
    fig, ax = plt.subplots(figsize=(3.2, 2.4))
    im = ax.imshow(np.random.default_rng(0).random((5, 5)))
    fig.colorbar(im, ax=ax)
    ins = ax.inset_axes([0.55, 0.55, 0.4, 0.4])
    ins.plot([0, 1], [0, 1])
    tw = ax.twinx()
    tw.set_ylabel("twin", fontsize=7)
    errors = [f for f in preflight(fig, saved_bbox_in="tight") if f.severity == "error"]
    assert not errors, [(f.check, f.message) for f in errors]


def test_findings_carry_location_and_hint():
    fig, saved = tick_collision(defect=True)
    f = next(f for f in preflight(fig, saved_bbox_in=saved) if f.check == "tick_label_collision")
    x0, y0, x1, y1 = f.bbox_mm
    assert 0 <= x0 < x1 <= 3.0 * 25.4 and 0 <= y0 < y1 <= 2.2 * 25.4
    assert f.hint and f.measured is not None


def test_recorder_measures_every_text():
    # Rotated tick labels need an extra measurement; a failure there once made
    # them silently skip every check.
    fig, saved = rotated_tick_collision(defect=True)
    found = preflight(fig, saved_bbox_in=saved)
    assert not [f for f in found if f.check == "recorder_error"], [f.message for f in found]


def test_composite_panel_with_wide_title_is_not_flagged():
    # Regression (compendium Figures 3-5, panel e): a heatmap whose wide title
    # passes above a shorter neighbouring axes. The two outer boxes overlap
    # (the title spans the neighbour's whitespace) but nothing collides.
    fig = plt.figure(figsize=(4.4, 2.2))
    heat = fig.add_axes([0.08, 0.15, 0.55, 0.65])
    side = fig.add_axes([0.66, 0.15, 0.2, 0.5])
    heat.imshow(np.random.default_rng(1).random((4, 12)), aspect="auto")
    heat.set_title("A wide title centred over the heatmap and beyond it", fontsize=8)
    side.barh(range(4), [3, 1, 4, 2])
    side.set_yticks([])
    hb = heat.get_tightbbox(fig.canvas.get_renderer())
    sb = side.get_tightbbox(fig.canvas.get_renderer())
    assert hb.x1 > sb.x0 and hb.y1 > sb.y1            # outer boxes do overlap...
    errors = [f for f in preflight(fig, saved_bbox_in="tight") if f.severity == "error"]
    assert not errors, [(f.check, f.message) for f in errors]   # ...but that's no defect


def test_overlay_box_is_drawn_where_the_finding_is(tmp_path):
    """The overlay is saved at its own dpi (150); a box placed in pixels at the
    figure's dpi (300 here) once landed at twice the distance from the corner."""
    from PIL import Image

    from fig_atlas.preflight import Finding, draw_overlay
    fig = plt.figure(figsize=(4.0, 3.0), dpi=300)
    box = [40.0, 30.0, 60.0, 45.0]                       # mm from the bottom-left corner
    draw_overlay(fig, [Finding("text_overlap", "error", "x", box)], tmp_path / "o.png", dpi=150)
    im = np.asarray(Image.open(tmp_path / "o.png").convert("RGB")).astype(int)
    red = (im[..., 0] > 180) & (im[..., 1] < 90) & (im[..., 2] < 90)
    k = 150 / 25.4
    red[:, int(box[2] * k) + 4:] = False                 # leave out the number written past the box
    ys, xs = np.nonzero(red)
    h = im.shape[0]
    assert abs(xs.min() - box[0] * k) < 6 and abs(xs.max() - box[2] * k) < 6
    assert abs(ys.min() - (h - box[3] * k)) < 6 and abs(ys.max() - (h - box[1] * k)) < 6
