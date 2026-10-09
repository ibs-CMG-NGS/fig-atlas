"""Preflight checks on saved files and while rendering (Phase 3.2: fonts, resolution).

Same pattern as test_preflight.py: each defect must be reported, and its
clean twin must not be.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.preflight import capture_font_issues, check_pdf, check_png, preflight  # noqa: E402


@pytest.fixture(autouse=True)
def _clean():
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams["pdf.fonttype"] = 42   # the repo default (./matplotlibrc)
        yield
    plt.close("all")


def _fig():
    fig, ax = plt.subplots(figsize=(2.4, 1.8))
    ax.plot([0, 1], [0, 1], label="series")
    ax.set_title("Title")
    return fig


def _checks(findings):
    return {(f.check, f.severity) for f in findings}


# ------------------------------------------------------------------ PDF fonts --
def test_type3_font_reported(tmp_path):
    with matplotlib.rc_context({"pdf.fonttype": 3}):
        _fig().savefig(tmp_path / "f.pdf")
    assert ("pdf_type3_font", "error") in _checks(check_pdf(tmp_path / "f.pdf"))


def test_core14_font_not_embedded_reported(tmp_path):
    with matplotlib.rc_context({"pdf.use14corefonts": True}):
        _fig().savefig(tmp_path / "f.pdf")
    assert ("pdf_font_not_embedded", "error") in _checks(check_pdf(tmp_path / "f.pdf"))


def test_truetype_embedded_pdf_is_clean(tmp_path):
    _fig().savefig(tmp_path / "f.pdf")
    assert check_pdf(tmp_path / "f.pdf") == []


def test_allowed_fonts(tmp_path):
    _fig().savefig(tmp_path / "f.pdf")    # DejaVu Sans
    assert ("pdf_font_not_allowed", "warn") in _checks(check_pdf(tmp_path / "f.pdf", {"allowed_fonts": ["Arial"]}))
    assert check_pdf(tmp_path / "f.pdf", {"allowed_fonts": ["DejaVuSans"]}) == []


# ------------------------------------------------------------- render-time fonts --
def test_missing_font_family_reported():
    with capture_font_issues() as found:
        with matplotlib.rc_context({"font.family": "NoSuchFontFamilyXYZ"}):
            _fig().canvas.draw()
    assert ("font_fallback", "error") in _checks(found)


def test_missing_glyph_reported():
    with capture_font_issues() as found:
        fig = _fig()
        fig.axes[0].set_xlabel("中")          # not in DejaVu Sans
        fig.canvas.draw()
    assert ("missing_glyph", "warn") in _checks(found)


def test_available_font_is_clean():
    with capture_font_issues() as found:
        _fig().canvas.draw()
    assert found == []


# -------------------------------------------------------------------- resolution --
def test_low_dpi_png_reported(tmp_path):
    _fig().savefig(tmp_path / "f.png", dpi=72)
    assert ("png_dpi_low", "error") in _checks(check_png(tmp_path / "f.png"))


def test_print_dpi_png_is_clean(tmp_path):
    _fig().savefig(tmp_path / "f.png", dpi=300)
    assert check_png(tmp_path / "f.png") == []


def test_png_scaled_to_page_width_uses_printed_width(tmp_path):
    # 2.4 in wide at 300 dpi = 720 px; printed at 4.8 in that is only 150 ppi.
    _fig().savefig(tmp_path / "f.png", dpi=300)
    assert ("png_dpi_low", "error") in _checks(check_png(tmp_path / "f.png", printed_width_in=4.8))


def test_rasterized_content_at_low_dpi_reported():
    fig = _fig()
    fig.axes[0].scatter(np.arange(50), np.arange(50), rasterized=True)
    assert ("raster_dpi_low", "error") in _checks(preflight(fig, "tight", save_dpi=72))
    assert ("raster_dpi_low", "error") not in _checks(preflight(fig, "tight", save_dpi=300))


def test_vector_only_figure_ignores_save_dpi():
    assert ("raster_dpi_low", "error") not in _checks(preflight(_fig(), "tight", save_dpi=72))


# ---------------------------------------------------------------- print size --
from fig_atlas.page import PageSpec  # noqa: E402
from fig_atlas.preflight import check_print_size  # noqa: E402

A4 = PageSpec("a4_test", 184.6, 271.6)


def test_wide_figure_scaled_below_min_font_reported():
    fig, ax = plt.subplots(figsize=(14, 4))          # 356 mm wide -> printed at ~52 %
    ax.plot([0, 1], [0, 1]); ax.set_title("Title", fontsize=7)
    checks = _checks(check_print_size(fig, A4, 5.0, 0.25))
    assert ("print_font_too_small", "error") in checks


def test_tall_figure_needs_more_than_one_page():
    fig, ax = plt.subplots(figsize=(7, 14))           # 356 mm tall at page width
    matplotlib.rcParams["font.size"] = 7
    ax.plot([0, 1], [0, 1])
    assert ("print_exceeds_page", "warn") in _checks(check_print_size(fig, A4, 5.0, 0.25))


def test_final_size_figure_is_clean():
    with matplotlib.rc_context({"font.size": 7, "axes.linewidth": 0.6, "lines.linewidth": 1.0,
                                "xtick.major.width": 0.6, "ytick.major.width": 0.6}):
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        ax.plot([0, 1], [0, 1])
        assert check_print_size(fig, A4, 5.0, 0.25) == []
