"""Colour checks of preflight (Phase 3.3): CVD-distinguishability, colormaps,
text contrast. Each defect must be reported; its clean twin must not be."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.preflight import preflight  # noqa: E402

OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]


@pytest.fixture(autouse=True)
def _clean():
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams["font.size"] = 7
        yield
    plt.close("all")


def checks(fig):
    return {f.check for f in preflight(fig, saved_bbox_in="tight")}


def _lines(colors):
    fig, ax = plt.subplots(figsize=(3, 2))
    for i, c in enumerate(colors):
        ax.plot([0, 1], [i, i + 1], color=c, label=f"group {i}")
    ax.legend()
    return fig


def test_red_green_legend_reported():
    assert "cvd_indistinct" in checks(_lines(["#d62728", "#2ca02c"]))      # tab10 red / green


def test_okabe_ito_legend_is_clean():
    assert "cvd_indistinct" not in checks(_lines(OKABE_ITO))


def test_scatter_groups_without_legend_reported():
    fig, ax = plt.subplots(figsize=(3, 2))
    rng = np.random.default_rng(0)
    for c in ("#ff7f0e", "#2ca02c"):                                    # orange / green
        ax.scatter(rng.random(20), rng.random(20), color=c)
    assert "cvd_indistinct" in checks(fig)


def test_same_colour_entries_are_not_flagged():
    # Two entries deliberately share a colour (told apart by line style).
    assert "cvd_indistinct" not in checks(_lines(["#0072B2", "#0072B2"]))


def _image(cmap):
    fig, ax = plt.subplots(figsize=(2.5, 2))
    im = ax.imshow(np.random.default_rng(0).random((8, 8)), cmap=cmap)
    fig.colorbar(im, ax=ax)
    return fig


@pytest.mark.parametrize("cmap,expected", [("jet", "cmap_rainbow"), ("rainbow_r", "cmap_rainbow"),
                                           ("RdYlGn", "cmap_red_green"), ("gist_earth", "cmap_nonuniform")])
def test_problem_colormaps_reported(cmap, expected):
    assert expected in checks(_image(cmap))


@pytest.mark.parametrize("cmap", ["viridis", "RdBu_r", "Greys", "magma"])
def test_good_colormaps_are_clean(cmap):
    assert not {"cmap_rainbow", "cmap_red_green", "cmap_nonuniform"} & checks(_image(cmap))


def _cell_text(text_color, cell_color):
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.imshow([[0]], cmap=matplotlib.colors.ListedColormap([cell_color]), extent=(0, 1, 0, 1))
    ax.text(0.5, 0.5, "+4.2", color=text_color, ha="center", va="center", fontsize=8)
    ax.set_axis_off()
    return fig


def test_low_contrast_text_reported():
    assert "low_text_contrast" in checks(_cell_text("white", "#fde68a"))    # white on pale yellow


def test_muted_grey_on_white_is_info_not_warning():
    # Grey "-" placeholders in a heatmap: deliberate de-emphasis.
    fig, ax = plt.subplots(figsize=(2, 2))
    for i in range(5):
        ax.text(0.1 + 0.15 * i, 0.5, "-", color="#94a3b8", fontsize=7)
    ax.set_axis_off()
    found = [f for f in preflight(fig, saved_bbox_in="tight") if f.check == "low_text_contrast"]
    assert [f.severity for f in found] == ["info"]            # five texts, one grouped finding


def test_white_on_mid_grey_is_a_warning():
    assert "low_text_contrast" in checks(_cell_text("white", "#94a3b8"))


def test_readable_text_is_clean():
    assert "low_text_contrast" not in checks(_cell_text("#111827", "#fde68a"))
    assert "low_text_contrast" not in checks(_cell_text("white", "#1d4ed8"))


def _label_on_green(box):
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.imshow(np.full((10, 10, 3), [0.18, 0.29, 0.31]))               # dark teal, like a green-tinted cell field
    ax.text(0.1, 0.9, "DNA", transform=ax.transAxes, color="#d946ef", fontsize=7, va="top",
            bbox=dict(boxstyle="square", fc="black", ec="none", alpha=0.85) if box else None)
    return fig


def test_text_is_read_against_its_own_box():
    """A label on its own dark box is judged against the box, not the image under it."""
    assert "low_text_contrast" in checks(_label_on_green(box=False))
    assert "low_text_contrast" not in checks(_label_on_green(box=True))


def test_cvd_finding_points_at_the_legend():
    """A colour-vision finding carries the legend's box, so overlays and
    allow-lists can place it (it once had no location)."""
    import matplotlib.pyplot as plt
    from fig_atlas.preflight import MM_PER_INCH, preflight
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1], color="#D62728", label="up")
    ax.plot([0, 1], [1, 0], color="#2CA02C", label="down")
    leg = ax.legend()
    found = [f for f in preflight(fig) if f.check == "cvd_indistinct"]
    assert found
    fig.canvas.draw()
    b = leg.get_window_extent(fig.canvas.get_renderer())
    k = MM_PER_INCH / fig.dpi
    x0, y0, x1, y1 = found[0].bbox_mm
    assert abs(x0 - b.x0 * k) < 0.5 and abs(y1 - b.y1 * k) < 0.5 and x1 > x0
    plt.close(fig)


def test_colormap_finding_points_at_its_axes():
    import matplotlib.pyplot as plt
    import numpy as np
    from fig_atlas.preflight import preflight
    fig, (a, b) = plt.subplots(1, 2, figsize=(4, 2))
    a.imshow(np.arange(9).reshape(3, 3), cmap="jet")
    b.imshow(np.arange(9).reshape(3, 3), cmap="viridis")
    found = [f for f in preflight(fig) if f.check == "cmap_rainbow"]
    assert len(found) == 1 and found[0].bbox_mm != [0.0, 0.0, 0.0, 0.0]
    fig.canvas.draw()
    x_mid = (found[0].bbox_mm[0] + found[0].bbox_mm[2]) / 2
    assert x_mid < 2 * 25.4                       # on the left axes, the one using jet
    plt.close(fig)
