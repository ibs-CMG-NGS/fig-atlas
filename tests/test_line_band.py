"""Line + error band renderer (roadmap 6a.3)."""
from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_line_band  # noqa: E402
from fig_atlas.renderers.line_band import summarise  # noqa: E402

REPS = pd.DataFrame({"t": [0, 0, 0, 1, 1, 1], "v": [1.0, 2.0, 3.0, 4.0, 6.0, 8.0], "g": ["a"] * 6})


def test_summary_by_hand():
    # x=0: values 1, 2, 3 -> mean 2, sd 1, sem 1/sqrt(3); t(0.975, 2) = 4.302652...
    s = summarise(REPS, "t", "v", "g", "mean", "sem").set_index("x")
    assert s.loc[0, "n"] == 3 and s.loc[0, "centre"] == 2.0
    assert s.loc[0, "upper"] == pytest.approx(2 + 1 / math.sqrt(3))
    sd = summarise(REPS, "t", "v", "g", "mean", "sd").set_index("x")
    assert sd.loc[1, "lower"] == pytest.approx(6 - 2)                  # x=1: 4, 6, 8 -> sd 2
    ci = summarise(REPS, "t", "v", None, "mean", "ci95").set_index("x")
    assert ci.loc[0, "upper"] == pytest.approx(2 + 4.302652729911275 / math.sqrt(3))
    med = summarise(pd.DataFrame({"t": [0, 0, 0], "v": [1, 2, 10]}), "t", "v", None, "median", "none")
    assert med.loc[0, "centre"] == 2.0 and med.loc[0, "lower"] == 2.0


def test_single_replicate_has_no_band():
    s = summarise(pd.DataFrame({"t": [0], "v": [5.0]}), "t", "v", None, "mean", "sem")
    assert s.loc[0, "centre"] == 5.0 and math.isnan(s.loc[0, "lower"])


def _draw(df, params):
    fig, ax = plt.subplots()
    out = render_line_band(ax, df, params)
    return fig, ax, out


def test_lines_bands_and_points_are_drawn():
    df = pd.concat([REPS, REPS.assign(g="b", v=REPS["v"] * 2)])
    fig, ax, out = _draw(df, {"x_col": "t", "y_col": "v", "group_col": "g", "show_points": True,
                              "group_colors": {"a": "#ff0000", "b": "#0000ff"}})
    try:
        assert len(ax.lines) == 2 and len(ax.collections) == 4         # 2 bands + 2 point clouds
        assert [t.get_text() for t in ax.get_legend().get_texts()] == ["a", "b"]
        assert list(out["group"]) == ["a", "a", "b", "b"]
    finally:
        plt.close(fig)


def test_categorical_x_and_log_x():
    df = pd.DataFrame({"cond": ["ctrl", "low", "high"] * 2, "v": [1, 2, 3, 1.5, 2.5, 3.5]})
    fig, ax, _ = _draw(df, {"x_col": "cond", "y_col": "v", "x_order": ["ctrl", "low", "high"], "error": "ci95"})
    try:
        assert [t.get_text() for t in ax.get_xticklabels()] == ["ctrl", "low", "high"]
        assert list(ax.lines[0].get_xdata()) == [0.0, 1.0, 2.0]
    finally:
        plt.close(fig)
    dose = pd.DataFrame({"dose": [0.1, 1, 10, 100], "v": [1, 2, 3, 4]})
    fig, ax, _ = _draw(dose, {"x_col": "dose", "y_col": "v", "x_log": True, "error": "none"})
    try:
        assert ax.get_xscale() == "log" and len(ax.collections) == 0  # error none: no band
    finally:
        plt.close(fig)


def test_presummarised_rows():
    pre = pd.DataFrame({"x": [0, 1, 2], "m": [1.0, 2.0, 1.5], "lo": [0.8, 1.7, 1.1], "hi": [1.2, 2.3, 1.9]})
    fig, ax, out = _draw(pre, {"y_col": "m", "aggregate": "none", "lower_col": "lo", "upper_col": "hi"})
    try:
        assert list(out["upper"]) == [1.2, 2.3, 1.9] and len(ax.collections) == 1
    finally:
        plt.close(fig)
