"""render_correlation_scatter: points, a fitted line and band from fit rows, and
r and P per group from columns the analysis writes."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_correlation_scatter  # noqa: E402

POINTS = pd.DataFrame({"x": [0.0, 1.0, 2.0, 3.0, 0.0, 1.0, 2.0, 3.0],
                       "y": [1.0, 3.0, 2.0, 4.0, 4.0, 3.0, 1.0, 0.5],
                       "g": ["a"] * 4 + ["b"] * 4,
                       "r": [0.8] * 4 + [-0.97] * 4,
                       "p": [0.2] * 4 + [0.00002] * 4})
GRID = np.linspace(0, 3, 4)
FITS = pd.DataFrame({"g": ["a"] * 4 + ["b"] * 4, "fx": np.r_[GRID, GRID],
                     "fy": np.r_[1 + GRID, 4 - GRID], "lo": np.r_[GRID, 3 - GRID], "hi": np.r_[2 + GRID, 5 - GRID]})
DATA = pd.concat([POINTS, FITS], ignore_index=True)
FIT = {"fit_x_col": "fx", "fit_y_col": "fy", "band_lower_col": "lo", "band_upper_col": "hi"}


def _draw(df, params):
    fig, ax = plt.subplots()
    return fig, ax, render_correlation_scatter(ax, df, params)


def test_points_only_by_default():
    fig, ax, out = _draw(POINTS, {})
    try:
        assert len(out) == 8 and list(out.columns) == ["group", "x", "y"]
        assert not ax.lines and not ax.texts
        assert ax.get_xlabel() == "x" and ax.get_ylabel() == "y"
    finally:
        plt.close(fig)


def test_fit_rows_draw_a_line_and_band_per_group_in_its_colour():
    colors = {"a": "#ff0000", "b": "#0000ff"}
    fig, ax, out = _draw(DATA, {"group_col": "g", "group_colors": colors, **FIT})
    try:
        assert len(out) == 8                                          # fit rows are not points
        assert [matplotlib.colors.to_hex(ln.get_color()) for ln in ax.lines] == ["#ff0000", "#0000ff"]
        assert list(ax.lines[1].get_ydata()) == pytest.approx(4 - GRID)
        bands = [c for c in ax.collections if c.get_alpha() == pytest.approx(0.18)]
        assert len(bands) == 2
        assert ax.get_legend() is not None
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(DATA, {"group_col": "g", **FIT, "show_band": False})
    try:
        assert len(ax.lines) == 2 and len(ax.collections) == 2      # two point sets, no bands
    finally:
        plt.close(fig)


def test_a_fit_row_without_a_group_is_one_line_over_all_points():
    pooled = pd.concat([POINTS, FITS.iloc[:4].assign(g=None)], ignore_index=True)
    fig, ax, _ = _draw(pooled, {"group_col": "g", **FIT, "color": "#222222"})
    try:
        assert len(ax.lines) == 1 and matplotlib.colors.to_hex(ax.lines[0].get_color()) == "#222222"
    finally:
        plt.close(fig)


def test_r_and_p_per_group_from_columns():
    fig, ax, _ = _draw(DATA, {"group_col": "g", "r_col": "r", "p_col": "p",
                              "stats_format": "{group}: r = {r:.2f}, {p_text}, n = {n}"})
    try:
        assert [t.get_text() for t in ax.texts] == ["a: r = 0.80, P = 0.2, n = 4",
                                                    "b: r = -0.97, P < 0.0001, n = 4"]
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(POINTS.assign(r=0.5, p=0.0123), {"r_col": "r", "p_col": "p", "stats_format": "R² = {r2:.2f}, {p_text}"})
    try:
        assert [t.get_text() for t in ax.texts] == ["R² = 0.25, P = 0.012"]
    finally:
        plt.close(fig)
    with pytest.raises(ValueError, match="analysis script"):
        _draw(POINTS, {"r_col": "rho", "p_col": "p"})


def test_lower_corner_keeps_the_first_group_on_top():
    fig, ax, _ = _draw(DATA, {"group_col": "g", "r_col": "r", "p_col": "p", "stats_loc": "lower right"})
    try:
        fig.canvas.draw()
        y = {t.get_text()[:8]: t.get_window_extent().y0 for t in ax.texts}
        assert y["r = 0.80"] > y["r = -0.9"]
    finally:
        plt.close(fig)


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(POINTS.iloc[0:0], {})
    try:
        assert out.empty and not ax.collections
    finally:
        plt.close(fig)
