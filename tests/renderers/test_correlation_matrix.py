"""render_correlation_matrix: a triangle of cells from a long table of pairs
(r and P from the analysis), squares or circles, values with stars, blank
cells above a P cut-off."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_correlation_matrix  # noqa: E402

PAIRS = pd.DataFrame({"var1": ["a", "a", "b"], "var2": ["b", "c", "c"],
                      "r": [0.8, -0.3, 0.05], "p": [0.0005, 0.04, 0.7]})


def _draw(df, params):
    fig, ax = plt.subplots()
    return fig, ax, render_correlation_matrix(ax, df, params)


def test_lower_triangle_without_diagonal_by_default():
    fig, ax, out = _draw(PAIRS, {"p_col": "p"})
    try:
        assert sorted(zip(out["row"], out["col"])) == [("b", "a"), ("c", "a"), ("c", "b")]
        assert [t.get_text() for t in ax.get_yticklabels()] == ["b", "c"]
        assert [t.get_text() for t in ax.get_xticklabels()] == ["a", "b"]
        assert sorted(t.get_text() for t in ax.texts) == ["0.05", "0.80\n***", "−0.30\n*"]
        assert len(fig.axes) == 2                                        # colourbar
    finally:
        plt.close(fig)


def test_upper_full_and_diagonal():
    fig, ax, out = _draw(PAIRS, {"triangle": "upper", "show_diagonal": True, "show_colorbar": False})
    try:
        assert len(out) == 6 and out[out["row"] == out["col"]]["r"].tolist() == [1.0, 1.0, 1.0]
        assert len(ax.texts) == 3                                         # implied 1s carry no text
        assert len(fig.axes) == 1
    finally:
        plt.close(fig)
    fig, ax, out = _draw(PAIRS, {"triangle": "full", "variable_order": ["c", "b", "a"],
                                 "variable_labels": {"a": "Alpha"}})
    try:
        assert len(out) == 6
        assert [t.get_text() for t in ax.get_yticklabels()] == ["c", "b", "Alpha"]
    finally:
        plt.close(fig)


def test_circles_scale_with_r_and_blank_cells_above_the_cutoff():
    fig, ax, _ = _draw(PAIRS, {"mark": "circle", "p_col": "p", "hide_above_p": 0.05, "show_values": False})
    try:
        frame, discs = ax.collections                                    # cell outlines, then the circles
        assert len(frame.get_paths()) == 3                               # every cell keeps its outline
        radii = sorted(np.ptp(p.vertices[:, 0]) / 2 for p in discs.get_paths())   # p = 0.7 is left blank
        assert radii == pytest.approx(sorted([0.5 * 0.95 * np.sqrt(0.8), 0.5 * 0.95 * np.sqrt(0.3)]), abs=1e-3)
        assert not ax.texts
    finally:
        plt.close(fig)


def test_a_named_column_must_exist():
    with pytest.raises(ValueError, match="analysis script"):
        _draw(PAIRS, {"p_col": "padj"})


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(PAIRS.iloc[0:0], {})
    try:
        assert out.empty and not ax.collections
    finally:
        plt.close(fig)
