"""render_grouped_bar: two factors as clustered or blocked bars with the replicates
on top, and brackets against a control group from a P value column."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.renderers import render_grouped_bar  # noqa: E402

REPS = pd.DataFrame({
    "category": ["WT"] * 6 + ["KO"] * 6,
    "group": (["vehicle"] * 3 + ["drug"] * 3) * 2,
    "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 2.0, 2.0, 2.0, 1.0, 1.5, 2.0],
})


def _draw(df, params):
    fig, ax = plt.subplots()
    return fig, ax, render_grouped_bar(ax, df, params)


def _bars(ax):
    return [p for p in ax.patches if p.get_width() > 0 and p.get_height() > 0]


def test_interleaved_bars_summary_and_points():
    fig, ax, out = _draw(REPS, {})
    try:
        assert len(_bars(ax)) == 4                                   # 2 categories x 2 groups
        wt_vehicle = out[(out["category"] == "WT") & (out["group"] == "vehicle")].iloc[0]
        assert wt_vehicle["centre"] == pytest.approx(2.0) and wt_vehicle["n"] == 3
        assert wt_vehicle["upper"] == pytest.approx(2.0 + 1 / 3 ** 0.5)  # SEM of 1, 2, 3
        assert [t.get_text() for t in ax.get_xticklabels()] == ["WT", "KO"]
        assert ax.get_legend() is not None
        assert ax.get_ylim()[0] == 0.0
        x = out.set_index(["category", "group"])["x"]
        assert x[("WT", "vehicle")] < x[("WT", "drug")] < x[("KO", "vehicle")]
    finally:
        plt.close(fig)


def test_separated_blocks_and_their_labels():
    fig, ax, out = _draw(REPS, {"arrangement": "separated", "group_order": ["drug", "vehicle"]})
    try:
        x = out.set_index(["category", "group"])["x"]
        assert max(x[("WT", "drug")], x[("KO", "drug")]) < min(x[("WT", "vehicle")], x[("KO", "vehicle")])
        assert {"drug", "vehicle"} <= {t.get_text() for t in ax.texts}  # block labels
        assert ax.get_legend() is None
        assert len(ax.get_xticklabels()) == 4
    finally:
        plt.close(fig)


def test_brackets_against_the_control_from_the_p_column():
    df = REPS.assign(p=[None] * 3 + [0.004] * 3 + [None] * 3 + [0.4] * 3)
    fig, ax, _ = _draw(df, {"pvalue_col": "p", "control_group": "vehicle"})
    try:
        assert sorted(t.get_text() for t in ax.texts) == ["**", "ns"]
    finally:
        plt.close(fig)
    fig, ax, _ = _draw(df, {"pvalue_col": "p"})                     # no control named: no brackets
    try:
        assert not ax.texts
    finally:
        plt.close(fig)


def test_brackets_stack_when_they_overlap():
    three = pd.concat([REPS, REPS[REPS["group"] == "drug"].assign(group="drug2")])
    df = three.assign(p=[0.5 if g == "vehicle" else 0.01 for g in three["group"]])
    fig, ax, _ = _draw(df, {"pvalue_col": "p", "control_group": "vehicle", "category_order": ["WT"]})
    try:
        fig.canvas.draw()
        ys = sorted(t.get_position()[1] for t in ax.texts)
        assert len(ys) == 2 and ys[1] > ys[0]                         # second bracket above the first
    finally:
        plt.close(fig)


def test_renamed_columns_missing_values_and_one_group():
    df = REPS.rename(columns={"category": "genotype", "group": "arm", "value": "weight"})
    df.loc[0, "weight"] = None
    fig, ax, out = _draw(df[df["arm"] == "vehicle"], {"category_col": "genotype", "group_col": "arm",
                                                      "value_col": "weight", "error": "sd"})
    try:
        assert len(_bars(ax)) == 2 and out["n"].tolist() == [2, 3]
        assert ax.get_legend() is None                                # one group: nothing to tell apart
        assert ax.get_ylabel() == "weight"
    finally:
        plt.close(fig)


def test_empty_table_draws_nothing():
    fig, ax, out = _draw(REPS.iloc[0:0], {})
    try:
        assert out.empty and not ax.patches
    finally:
        plt.close(fig)
