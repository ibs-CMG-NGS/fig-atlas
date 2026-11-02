"""render_roc_curve: curves from fpr/tpr columns, the chance line, AUC and its
interval in the legend, and an operating point marked by a column."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_roc_curve  # noqa: E402

CURVES = pd.DataFrame({
    "marker": ["A"] * 4 + ["B"] * 4,
    "fpr": [0.0, 0.1, 0.4, 1.0, 0.0, 0.3, 0.6, 1.0],
    "tpr": [0.0, 0.6, 0.9, 1.0, 0.0, 0.4, 0.7, 1.0],
    "auc": [0.85] * 4 + [0.62] * 4,
    "lo": [0.78] * 4 + [0.51] * 4,
    "hi": [0.91] * 4 + [0.72] * 4,
    "youden": [False, True, False, False, False, False, True, False],
})


def _draw(df, params):
    fig, ax = plt.subplots()
    return fig, ax, render_roc_curve(ax, df, params)


def test_one_curve_and_the_chance_line_by_default():
    fig, ax, out = _draw(CURVES[CURVES["marker"] == "A"], {})
    try:
        assert len(out) == 4 and list(out.columns) == ["group", "fpr", "tpr"]
        assert len(ax.lines) == 2                                        # chance line + curve
        assert list(ax.lines[0].get_xdata()) == [0, 1]
        assert ax.get_legend() is None
        assert ax.get_xlabel() == "1 − specificity" and ax.get_ylabel() == "Sensitivity"
        assert ax.get_xlim() == pytest.approx((-0.02, 1.02))
    finally:
        plt.close(fig)


def test_auc_and_interval_per_marker_in_the_legend():
    fig, ax, _ = _draw(CURVES, {"group_col": "marker", "auc_col": "auc", "auc_low_col": "lo", "auc_high_col": "hi",
                                "group_colors": {"A": "#ff0000"}})
    try:
        assert [t.get_text() for t in ax.get_legend().get_texts()] == ["A (AUC 0.85, 0.78–0.91)",
                                                                       "B (AUC 0.62, 0.51–0.72)"]
        assert matplotlib.colors.to_hex(ax.lines[1].get_color()) == "#ff0000"
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(CURVES[CURVES["marker"] == "A"], {"auc_col": "auc"})
    try:
        assert [t.get_text() for t in ax.get_legend().get_texts()] == ["(AUC 0.85)"]
    finally:
        plt.close(fig)


def test_operating_point_and_percent_axes():
    fig, ax, _ = _draw(CURVES, {"group_col": "marker", "operating_point_col": "youden", "as_percent": True})
    try:
        pts = [tuple(c.get_offsets()[0]) for c in ax.collections]
        assert pts == [pytest.approx((10, 60)), pytest.approx((60, 70))]
        assert ax.get_xlim()[1] == pytest.approx(102) and ax.get_ylabel() == "Sensitivity (%)"
    finally:
        plt.close(fig)


def test_a_named_column_must_exist():
    with pytest.raises(ValueError, match="analysis script"):
        _draw(CURVES, {"auc_col": "AUC"})


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(CURVES.iloc[0:0], {})
    try:
        assert out.empty and not ax.lines
    finally:
        plt.close(fig)
