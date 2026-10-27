"""group_scatter: the r/P text is drawn from the analysis's columns, not computed here.

docs/decisions/0007 -- a renderer draws a result, it does not run the test.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_group_scatter  # noqa: E402


def _points() -> pd.DataFrame:
    return pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0], "y": [2.0, 1.0, 4.0, 3.0, 5.0],
                         "group": ["a"] * 5})


def _texts(ax) -> str:
    return " | ".join(t.get_text() for t in ax.texts)


def test_r_text_comes_from_the_columns():
    df = _points().assign(r=0.42, p_value=0.031)
    fig, ax = plt.subplots()
    render_group_scatter(ax, df, {"r_col": "r", "p_col": "p_value"})
    assert "r = +0.42" in _texts(ax) and "P = 0.03" in _texts(ax)
    plt.close(fig)


def test_changing_the_columns_changes_the_text():
    """The printed value follows the analysis, not the points under it."""
    first = _points().assign(r=0.42, p_value=0.031)
    second = _points().assign(r=-0.90, p_value=1e-06)
    labels = []
    for df in (first, second):
        fig, ax = plt.subplots()
        render_group_scatter(ax, df, {"r_col": "r", "p_col": "p_value"})
        labels.append(_texts(ax))
        plt.close(fig)
    assert labels[0] != labels[1]


def test_a_named_but_missing_column_is_an_error():
    df = _points().assign(r=0.42)
    fig, ax = plt.subplots()
    with pytest.raises(ValueError, match="p_value"):
        render_group_scatter(ax, df, {"r_col": "r", "p_col": "p_value"})
    plt.close(fig)


def test_absent_columns_fall_back_with_a_deprecation_warning():
    fig, ax = plt.subplots()
    with pytest.warns(DeprecationWarning, match="r_col"):
        render_group_scatter(ax, _points(), {})
    assert "r = " in _texts(ax)
    plt.close(fig)


def test_annotate_r_off_draws_no_text():
    df = _points().assign(r=0.42, p_value=0.031)
    fig, ax = plt.subplots()
    render_group_scatter(ax, df, {"r_col": "r", "p_col": "p_value", "annotate_r": False})
    assert not _texts(ax)
    plt.close(fig)
