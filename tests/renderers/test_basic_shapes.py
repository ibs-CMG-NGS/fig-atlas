"""The basic shapes: violin, histogram, dose_response, survival, stacked_bar."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import (  # noqa: E402
    render_dose_response,
    render_histogram,
    render_stacked_bar,
    render_survival,
    render_violin,
)
from fig_atlas.renderers.survival import kaplan_meier  # noqa: E402


def test_kaplan_meier_matches_the_product_limit_by_hand():
    # times 1, 2 (censored), 3, 3; events at 1 and both at 3
    km = kaplan_meier(np.array([1.0, 2.0, 3.0, 3.0]), np.array([True, False, True, True]))
    assert list(km["survival"].round(4)) == [1.0, 0.75, 0.75, 0.0]     # 1 * 3/4, unchanged, 0.75 * 0/2
    fig, ax = plt.subplots()
    df = pd.DataFrame({"time": [1, 2, 3, 3], "event": [1, 0, 1, 1]})
    drawn = render_survival(ax, df, {"percent": False})
    assert drawn["survival"].iloc[-1] == 0.0 and ax.lines
    plt.close(fig)


def test_dose_response_recovers_the_ec50():
    doses = np.logspace(-2, 2, 9)
    y = 5 + 95 / (1 + (doses / 0.5) ** 1.2)
    df = pd.DataFrame({"dose": np.repeat(doses, 3), "response": np.repeat(y, 3)})
    fig, ax = plt.subplots()
    fit = render_dose_response(ax, df, {})
    assert fit["fit_ok"].iloc[0] and fit["ec50"].iloc[0] == pytest.approx(0.5, rel=1e-3)
    assert ax.get_xscale() == "log"
    plt.close(fig)


def test_histogram_counts_and_density():
    df = pd.DataFrame({"value": [0.1, 0.2, 0.6, 0.9], "g": ["a", "a", "b", "b"]})
    fig, ax = plt.subplots()
    counts = render_histogram(ax, df, {"bins": 2, "bin_min": 0.0, "bin_max": 1.0})
    assert list(counts["count"]) == [2, 2]
    dens = render_histogram(ax, df, {"bins": 2, "bin_min": 0.0, "bin_max": 1.0, "group_col": "g", "density": True})
    assert (dens.groupby("group")["density"].sum() * 0.5).round(6).tolist() == [1.0, 1.0]   # area 1 per group
    plt.close(fig)


def test_stacked_bar_shares_add_up_and_order_holds():
    df = pd.DataFrame({"category": ["s1", "s1", "s2", "s2"], "part": ["x", "y", "x", "y"], "count": [1, 3, 2, 2]})
    fig, ax = plt.subplots()
    t = render_stacked_bar(ax, df, {"stack_order": ["y", "x"]})
    assert t.groupby("category")["share"].sum().round(6).tolist() == [100.0, 100.0]
    assert [x.get_text() for x in ax.get_xticklabels()] == ["s1", "s2"]
    assert ax.get_legend() is not None
    plt.close(fig)


def test_violin_summary_and_order():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"group": ["b"] * 20 + ["a"] * 20, "value": np.r_[rng.normal(2, 1, 20), rng.normal(0, 1, 20)]})
    fig, ax = plt.subplots()
    s = render_violin(ax, df, {"x_order": ["a", "b"], "show_points": True})
    assert list(s["category"]) == ["a", "b"] and list(s["n"]) == [20, 20]
    assert [x.get_text() for x in ax.get_xticklabels()] == ["a", "b"]
    plt.close(fig)
