"""render_bland_altman: difference against mean of two methods, with the bias
and the limits of agreement drawn from columns the analysis writes."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_bland_altman  # noqa: E402

DATA = pd.DataFrame({"lab": [10.0, 20.0, 30.0, 40.0], "device": [9.0, 21.0, 28.0, 41.0],
                     "site": ["x", "x", "y", "y"],
                     "bias": 0.25, "lo": -2.5, "hi": 3.0})
NAMES = {"a_col": "lab", "b_col": "device"}


def _draw(df, params):
    fig, ax = plt.subplots()
    return fig, ax, render_bland_altman(ax, df, params)


def test_points_are_difference_against_mean():
    fig, ax, out = _draw(DATA, NAMES)
    try:
        assert out["mean"].tolist() == [9.5, 20.5, 29.0, 40.5]
        assert out["difference"].tolist() == [1.0, -1.0, 2.0, -1.0]
        assert len(ax.lines) == 1 and not ax.texts                      # the zero line only
        assert ax.get_ylabel() == "Difference (lab − device)" and ax.get_xlabel() == "Mean of lab and device"
    finally:
        plt.close(fig)


def test_percent_difference():
    fig, ax, out = _draw(DATA, {**NAMES, "difference": "percent"})
    try:
        assert out["difference"].iloc[0] == pytest.approx(100 / 9.5)
        assert ax.get_ylabel() == "Difference (%)"
    finally:
        plt.close(fig)


def test_bias_and_limits_from_columns_with_labels():
    fig, ax, _ = _draw(DATA, {**NAMES, "bias_col": "bias", "loa_low_col": "lo", "loa_high_col": "hi"})
    try:
        assert sorted(ln.get_ydata()[0] for ln in ax.lines) == [-2.5, 0, 0.25, 3.0]
        assert [t.get_text() for t in ax.texts] == ["Mean 0.25", "+1.96 SD 3.00", "−1.96 SD −2.50"]
        lo, hi = ax.get_ylim()
        assert lo < -2.5 and hi > 3.0
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(DATA, {**NAMES, "bias_col": "bias", "show_line_labels": False, "show_zero": False,
                              "bias_label": "Bias {value:+.1f}"})
    try:
        assert len(ax.lines) == 1 and not ax.texts
    finally:
        plt.close(fig)
    with pytest.raises(ValueError, match="analysis script"):
        _draw(DATA, {**NAMES, "bias_col": "mean_diff"})


def test_groups_colour_the_points():
    fig, ax, out = _draw(DATA, {**NAMES, "group_col": "site", "group_colors": {"x": "#ff0000", "y": "#0000ff"}})
    try:
        assert out["group"].tolist() == ["x", "x", "y", "y"]
        assert ax.get_legend() is not None and len(ax.collections) == 2
    finally:
        plt.close(fig)


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(DATA.iloc[0:0], NAMES)
    try:
        assert out.empty and not ax.collections
    finally:
        plt.close(fig)
