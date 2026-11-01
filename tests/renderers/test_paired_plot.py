"""render_paired_plot: one line per subject across conditions, groups side by
side, a bracket from a P value column (never a test of its own)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_paired_plot  # noqa: E402

PAIRS = pd.DataFrame({"subject": ["s1", "s1", "s2", "s2", "s3", "s3"],
                      "condition": ["before", "after"] * 3,
                      "value": [1.0, 2.0, 2.0, 3.5, 3.0, 2.5]})


def _draw(df, params):
    fig, ax = plt.subplots()
    return fig, ax, render_paired_plot(ax, df, params)


def test_one_line_per_subject_and_the_rows_drawn():
    fig, ax, out = _draw(PAIRS, {})
    try:
        assert len(ax.lines) == 3                                   # s1, s2, s3
        assert list(out.columns) == ["subject", "group", "condition", "x", "value"]
        assert set(out.loc[out["condition"] == "after", "x"]) == {1.0}
        assert [t.get_text() for t in ax.get_xticklabels()] == ["before", "after"]
    finally:
        plt.close(fig)


def test_renamed_columns_and_condition_order():
    df = PAIRS.rename(columns={"subject": "mouse", "condition": "day", "value": "weight"})
    fig, ax, out = _draw(df, {"subject_col": "mouse", "condition_col": "day", "value_col": "weight",
                              "condition_order": ["after", "before"], "condition_labels": {"after": "Day 7"}})
    try:
        assert [t.get_text() for t in ax.get_xticklabels()] == ["Day 7", "before"]
        assert set(out.loc[out["condition"] == "after", "x"]) == {0.0}
        assert ax.get_ylabel() == "weight"
    finally:
        plt.close(fig)


def test_missing_values_and_a_subject_with_one_condition():
    df = pd.concat([PAIRS, pd.DataFrame({"subject": ["s4", "s5"], "condition": ["before", "after"],
                                         "value": [None, 4.0]})])
    fig, ax, out = _draw(df, {})
    try:
        assert "s4" not in set(out["subject"])                      # its only value is missing
        assert len(ax.lines) == 4                                   # s5 is one point, still drawn
    finally:
        plt.close(fig)


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(PAIRS.iloc[0:0], {})
    try:
        assert out.empty and not ax.lines
    finally:
        plt.close(fig)


def test_bracket_comes_from_the_pvalue_column():
    df = PAIRS.assign(p=0.004)
    fig, ax, _ = _draw(df, {"pvalue_col": "p"})
    try:
        assert [t.get_text() for t in ax.texts] == ["**"]
        assert len(ax.lines) == 4                                   # three subjects + the bracket
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(PAIRS.assign(p=0.3), {"pvalue_col": "p", "sig_ns_display": ""})
    try:
        assert not ax.texts                                         # ns hidden
    finally:
        plt.close(fig)


def test_groups_sit_side_by_side_with_their_own_brackets_and_labels():
    df = pd.concat([PAIRS.assign(arm="vehicle", p=0.5), PAIRS.assign(arm="drug", subject=PAIRS["subject"] + "d",
                                                                     p=0.01)])
    fig, ax, out = _draw(df, {"group_col": "arm", "pvalue_col": "p", "group_order": ["vehicle", "drug"],
                              "summary": "mean", "line_color_by": "direction"})
    try:
        xs = out.groupby("group")["x"].agg(["min", "max"])
        assert xs.loc["drug", "min"] > xs.loc["vehicle", "max"]     # drug block right of vehicle
        texts = [t.get_text() for t in ax.texts]
        assert "*" in texts and "ns" in texts                       # one bracket per group
        assert {"vehicle", "drug"} <= set(texts)                   # group labels under the ticks
        assert len(ax.get_xticklabels()) == 4
    finally:
        plt.close(fig)


@pytest.mark.parametrize("how", ["mean", "median"])
def test_summary_line(how):
    fig, ax, _ = _draw(PAIRS, {"summary": how})
    try:
        assert len(ax.lines) == 4                                   # three subjects + the summary
    finally:
        plt.close(fig)


def test_summary_bars_start_at_zero_with_error_bars():
    fig, ax, _ = _draw(PAIRS, {"summary": "mean", "summary_style": "bar", "summary_error": "sem"})
    try:
        bars = [p for p in ax.patches if p.get_height() > 0]
        assert len(bars) == 2                                       # one bar per condition
        assert bars[0].get_height() == pytest.approx(2.0)           # mean of 1, 2, 3 at "before"
        assert ax.get_ylim()[0] == 0.0
        assert ax.containers                                        # the error bars
        assert len(ax.lines) == 3 + 2                               # subjects + the error bars' two lines
    finally:
        plt.close(fig)


def test_bracket_clears_the_error_bars():
    df = PAIRS.assign(p=0.01)
    fig, ax, _ = _draw(df, {"summary": "mean", "summary_style": "bar", "summary_error": "sd", "pvalue_col": "p"})
    try:
        fig.canvas.draw()
        star = next(t for t in ax.texts if t.get_text() == "*")
        assert star.get_position()[1] > 3.5                          # above the highest subject value
    finally:
        plt.close(fig)
