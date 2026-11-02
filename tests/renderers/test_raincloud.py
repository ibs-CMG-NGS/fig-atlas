"""render_raincloud: a half violin, a box and the points per category, either
orientation, and brackets against a control from a P value column."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

from fig_atlas.renderers import render_raincloud  # noqa: E402

RNG = np.random.default_rng(1)
DATA = pd.DataFrame({"group": ["ctrl"] * 20 + ["A"] * 20 + ["B"] * 20,
                     "value": np.r_[RNG.normal(0, 1, 20), RNG.normal(2, 1, 20), RNG.normal(1, 1, 20)],
                     "p": [None] * 20 + [0.0004] * 20 + [0.03] * 20})


def _draw(df, params):
    fig, ax = plt.subplots()
    return fig, ax, render_raincloud(ax, df, params)


def test_horizontal_cloud_above_rain_below_first_category_on_top():
    fig, ax, out = _draw(DATA, {})
    try:
        assert out["category"].tolist() == ["ctrl", "A", "B"] and out["n"].tolist() == [20, 20, 20]
        assert out["median"].iloc[1] == pytest.approx(float(np.median(DATA["value"][20:40])))
        assert [t.get_text() for t in ax.get_yticklabels()] == ["ctrl", "A", "B"]
        assert ax.get_ylim()[0] > ax.get_ylim()[1]                     # inverted: first at the top
        cloud = [c for c in ax.collections if isinstance(c, PolyCollection)][0]
        ys = cloud.get_paths()[0].vertices[:, 1]
        assert ys.max() <= 0 - 0.08 + 1e-9                             # all above (smaller y) the box centre
        xs = cloud.get_paths()[0].vertices[:, 0]
        ctrl = DATA["value"][:20]
        assert xs.min() < ctrl.min() and xs.max() > ctrl.max()        # the tails reach past the data
        rain = [c for c in ax.collections if c.get_offsets().shape[0] == 20][0]
        assert (rain.get_offsets()[:, 1] > 0).all()                    # rain below
        assert ax.get_xlabel() == "value" and ax.get_ylabel() == ""
    finally:
        plt.close(fig)


def test_vertical_and_flip_move_the_cloud():
    fig, ax, _ = _draw(DATA, {"orientation": "vertical"})
    try:
        cloud = [c for c in ax.collections if isinstance(c, PolyCollection)][0]
        assert cloud.get_paths()[0].vertices[:, 0].min() >= 0.08 - 1e-9   # right of the box
        assert [t.get_text() for t in ax.get_xticklabels()] == ["ctrl", "A", "B"]
        assert ax.get_ylabel() == "value"
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(DATA, {"orientation": "vertical", "flip": True})
    try:
        cloud = [c for c in ax.collections if isinstance(c, PolyCollection)][0]
        assert cloud.get_paths()[0].vertices[:, 0].max() <= -0.08 + 1e-9  # left of the box
    finally:
        plt.close(fig)


def test_brackets_against_the_control_stack():
    fig, ax, _ = _draw(DATA, {"pvalue_col": "p", "control_category": "ctrl"})
    try:
        assert sorted(t.get_text() for t in ax.texts) == ["*", "***"]
        fig.canvas.draw()
        xs = sorted(t.get_window_extent().x0 for t in ax.texts)
        assert xs[1] > xs[0]                                            # ctrl-B spans ctrl-A: stacked beyond it
        assert ax.get_xlim()[1] > DATA["value"].max()
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(DATA, {"pvalue_col": "p"})                      # no control named: no brackets
    try:
        assert not ax.texts
    finally:
        plt.close(fig)


def test_parts_can_be_turned_off_and_a_single_value_has_no_cloud():
    one = pd.concat([DATA, pd.DataFrame({"group": ["C"], "value": [1.0]})], ignore_index=True)
    fig, ax, out = _draw(one, {"show_box": False, "show_points": False})
    try:
        assert len([c for c in ax.collections if isinstance(c, PolyCollection)]) == 3   # C gets no cloud
        assert not ax.patches and out["n"].tolist() == [20, 20, 20, 1]
    finally:
        plt.close(fig)


def test_renamed_columns_order_and_labels():
    df = DATA.rename(columns={"group": "arm", "value": "score"})
    fig, ax, out = _draw(df, {"category_col": "arm", "value_col": "score", "category_order": ["B", "ctrl"],
                              "category_labels": {"ctrl": "Control"}})
    try:
        assert out["category"].tolist() == ["B", "ctrl"]
        assert [t.get_text() for t in ax.get_yticklabels()] == ["B", "Control"]
    finally:
        plt.close(fig)


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(DATA.iloc[0:0], {})
    try:
        assert out.empty and not ax.collections
    finally:
        plt.close(fig)
