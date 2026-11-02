"""render_column_scatter: points per category (swarm, jitter or aligned), a mean
or median line with error bars, and brackets against a control from a P value
column."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_column_scatter  # noqa: E402

RNG = np.random.default_rng(3)
DATA = pd.DataFrame({"group": ["ctrl"] * 12 + ["A"] * 12 + ["B"] * 12,
                     "value": np.r_[RNG.normal(5, 1, 12), RNG.normal(8, 1, 12), RNG.normal(6, 1, 12)],
                     "p": [None] * 12 + [0.0002] * 12 + [0.04] * 12})


def _draw(df, params, size=(3, 2.5)):
    fig, ax = plt.subplots(figsize=size)
    return fig, ax, render_column_scatter(ax, df, params)


def _points(ax):
    return [c for c in ax.collections if c.get_offsets().shape[0] == 12]


def test_swarm_points_do_not_overlap_and_keep_their_values():
    fig, ax, out = _draw(DATA, {"point_size": 16})
    try:
        assert out["category"].tolist() == ["ctrl", "A", "B"] and out["n"].tolist() == [12, 12, 12]
        assert out["centre"].iloc[0] == pytest.approx(DATA["value"][:12].mean())
        assert out["upper"].iloc[0] - out["centre"].iloc[0] == pytest.approx(DATA["value"][:12].std(ddof=1))
        pts = _points(ax)[0]
        xy = pts.get_offsets()
        assert sorted(xy[:, 1]) == pytest.approx(sorted(DATA["value"][:12]))     # true values
        px = ax.transData.transform(xy)
        d = np.sqrt(16) * fig.dpi / 72
        dist = np.sqrt(((px[:, None, :] - px[None, :, :]) ** 2).sum(-1)) + np.eye(12) * 1e9
        assert dist.min() >= d * 0.999
        assert np.abs(xy[:, 0]).max() <= 0.4 + 1e-9
    finally:
        plt.close(fig)


def test_aligned_and_jitter_layouts():
    fig, ax, _ = _draw(DATA, {"point_layout": "aligned"})
    try:
        assert (_points(ax)[1].get_offsets()[:, 0] == 1).all()
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(DATA, {"point_layout": "jitter", "point_jitter": 0.1})
    try:
        x = _points(ax)[2].get_offsets()[:, 0]
        assert np.abs(x - 2).max() <= 0.1 and np.abs(x - 2).max() > 0
    finally:
        plt.close(fig)


def test_a_crowded_swarm_is_squeezed_to_max_spread():
    many = pd.DataFrame({"group": "a", "value": np.full(40, 1.0)})
    fig, ax, _ = _draw(many, {"max_spread": 0.6, "point_size": 30})
    try:
        x = [c for c in ax.collections if c.get_offsets().shape[0] == 40][0].get_offsets()[:, 0]
        assert np.abs(x).max() == pytest.approx(0.3)
    finally:
        plt.close(fig)


def test_median_with_iqr_and_no_summary():
    fig, ax, out = _draw(DATA, {"summary": "median", "error": "iqr"})
    try:
        v = DATA["value"][12:24]
        assert out["centre"].iloc[1] == pytest.approx(np.median(v))
        assert (out["lower"].iloc[1], out["upper"].iloc[1]) == pytest.approx(tuple(np.percentile(v, [25, 75])))
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(DATA, {"summary": "none"})
    try:
        assert not ax.lines and len(ax.collections) == 3                      # points only
    finally:
        plt.close(fig)


def test_brackets_against_the_control_stack():
    fig, ax, _ = _draw(DATA, {"pvalue_col": "p", "control_category": "ctrl"})
    try:
        texts = sorted(ax.texts, key=lambda t: t.get_position()[1])
        assert [t.get_text() for t in texts] == ["***", "*"]                 # ctrl-B stacked above ctrl-A
        assert ax.get_ylim()[1] > texts[-1].get_position()[1]
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(DATA, {"pvalue_col": "p"})
    try:
        assert not ax.texts
    finally:
        plt.close(fig)


def test_renamed_columns_order_and_labels():
    df = DATA.rename(columns={"group": "arm", "value": "score"})
    fig, ax, out = _draw(df, {"category_col": "arm", "value_col": "score", "category_order": ["B", "ctrl"],
                              "category_labels": {"ctrl": "Control"}})
    try:
        assert out["category"].tolist() == ["B", "ctrl"]
        assert [t.get_text() for t in ax.get_xticklabels()] == ["B", "Control"]
        assert ax.get_ylabel() == "score"
    finally:
        plt.close(fig)


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(DATA.iloc[0:0], {})
    try:
        assert out.empty and not ax.collections
    finally:
        plt.close(fig)
