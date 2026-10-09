"""Statistics layer (roadmap 4a): tests, corrections, stars, recorded tables,
and the tf_expression_bars migration (same stars as the old in-renderer test)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats as st

from fig_atlas import stats
from fig_atlas_omics.renderers import tf_expression_bars as tfb


# ------------------------------------------------------------ corrections --
P = [0.01, 0.04, 0.03, 0.005, 0.2, float("nan"), 0.04]


@pytest.mark.parametrize("method,sm", [("bonferroni", "bonferroni"), ("holm", "holm"), ("bh", "fdr_bh")])
def test_adjust_matches_statsmodels(method, sm):
    multipletests = pytest.importorskip("statsmodels.stats.multitest").multipletests
    p = np.array(P)
    ok = ~np.isnan(p)
    expected = multipletests(p[ok], method=sm)[1]
    got = stats.adjust(p, method)
    assert np.allclose(got[ok], expected)
    assert math.isnan(got[~ok][0])            # NaN stays out of the family


def test_adjust_none_is_identity_and_bad_method_fails():
    assert np.array_equal(stats.adjust(P, "none"), np.array(P), equal_nan=True)
    with pytest.raises(ValueError):
        stats.adjust(P, "fdr")


def test_bh_hand_example():
    # m = 4: sorted p 0.01, 0.02, 0.03, 0.04 -> 0.04 each (min over ranks above)
    assert np.allclose(stats.adjust([0.04, 0.01, 0.03, 0.02], "bh"), [0.04, 0.04, 0.04, 0.04])


def test_hand_worked_corrections():
    """Worked by hand, so CI checks them without statsmodels.
    p = 0.01, 0.04, 0.03, 0.005 (m = 4); sorted 0.005, 0.01, 0.03, 0.04.
    Holm: 4x0.005=0.02, 3x0.01=0.03, 2x0.03=0.06, 1x0.04 -> running max 0.06.
    BH: 0.005x4/1=0.02, 0.01x4/2=0.02, 0.03x4/3=0.04, 0.04x4/4=0.04 (running min from the top)."""
    p = [0.01, 0.04, 0.03, 0.005]
    assert np.allclose(stats.adjust(p, "bonferroni"), [0.04, 0.16, 0.12, 0.02])
    assert np.allclose(stats.adjust(p, "holm"), [0.03, 0.06, 0.06, 0.02])
    assert np.allclose(stats.adjust(p, "bh"), [0.02, 0.04, 0.04, 0.02])


def test_describe_matches_the_legend_text():
    assert stats.describe("welch") == "Welch's t-test versus control (*P < 0.05, **P < 0.01, ***P < 0.001)"
    assert stats.describe("mannwhitney", "holm", family="within each gene").startswith(
        "Mann-Whitney U test versus control, Holm-adjusted within each gene (*adjusted P < 0.05")


# ------------------------------------------------------------------ stars --
def test_stars_strict_threshold_and_nan():
    t = [[0.001, "***"], [0.01, "**"], [0.05, "*"]]
    assert stats.stars(0.0009, t) == "***"
    assert stats.stars(0.001, t) == "**"       # strictly below
    assert stats.stars(0.05, t) == ""
    assert stats.stars(float("nan"), t, ns="ns") == "ns"


# ------------------------------------------------------------------ tests --
def test_two_group_matches_scipy_and_edge_cases():
    a, b = [1.0, 2.0, 3.0, 4.0], [3.0, 5.0, 6.0, 8.0]
    assert stats.two_group(a, b, "welch")[1] == pytest.approx(st.ttest_ind(a, b, equal_var=False).pvalue)
    assert stats.two_group(a, b, "student")[1] == pytest.approx(st.ttest_ind(a, b).pvalue)
    assert stats.two_group(a, b, "mannwhitney")[1] == pytest.approx(
        st.mannwhitneyu(a, b, alternative="two-sided").pvalue)
    assert stats.two_group([2, 2, 2], [2, 2, 2]) == (pytest.approx(math.nan, nan_ok=True), 1.0, "both groups constant")
    assert stats.two_group(a, b, "welch")[0] > 0          # b is higher than a
    with pytest.raises(ValueError):
        stats.two_group(a, b, "ttest")


def test_compare_to_control_rows():
    t = stats.compare_to_control({"C": [1, 2, 3], "A": [4, 5, 6], "B": []}, control="C")
    assert list(t["group"]) == ["A", "B"]
    assert t.loc[1, "note"] == "no values" and math.isnan(t.loc[1, "p"])
    one = stats.compare_to_control({"C": [1.0], "A": [4, 5, 6]}, control="C")
    assert math.isnan(one.loc[0, "p"])        # control needs two values


# ----------------------------------------------------------------- record --
def test_record_names_and_write(tmp_path):
    stats.take()
    df = pd.DataFrame({"p": [0.1]})
    stats.record(df, "t")
    stats.record(df, "t")
    names = [t["name"] for t in stats.take()]
    assert names == ["t", "t_2"]
    stats.record(df, "t", title="x")
    entries = stats.write(stats.take(), tmp_path / "s", lambda p: p.name)
    assert entries[0]["path"] == "t.csv" and entries[0]["rows"] == 1
    assert (tmp_path / "s" / "t.csv").read_text().splitlines() == ["p", "0.1"]
    with pytest.raises(ValueError):
        stats.record(df, "bad name")


# ------------------------------------------------- tf_expression migration --
def _old_stars(replicate_groups):
    """The renderer's pre-4a logic, verbatim: Welch t vs the first group."""
    c_ctrl = np.array(replicate_groups[0])[~np.isnan(replicate_groups[0])]
    out = {}
    if len(c_ctrl) <= 1:
        return out
    for gi in range(1, len(replicate_groups)):
        grp = np.array(replicate_groups[gi])[~np.isnan(replicate_groups[gi])]
        if len(grp) < 1:
            continue
        try:
            if np.var(c_ctrl) > 0 or np.var(grp) > 0:
                _, pval = st.ttest_ind(c_ctrl, grp, equal_var=False)
            else:
                pval = 1.0
        except Exception:
            pval = 1.0
        out[gi] = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
    return out


def test_default_stars_equal_the_old_in_renderer_test():
    rng = np.random.default_rng(0)
    conds = ["Control", "D1", "D3", "24h", "48h"]
    for trial in range(300):
        groups = [list(rng.normal(10 + (k * rng.uniform(0, 3) if k else 0), rng.uniform(0.2, 2), size=3))
                  for k in range(5)]
        if trial % 25 == 0:
            groups[2] = [5.0, 5.0, 5.0]
            groups[0] = [5.0, 5.0, 5.0] if trial % 50 == 0 else groups[0]
        if trial % 30 == 0:
            groups[3] = [float("nan"), 4.0]
        t = tfb._correct(tfb.gene_tests("G", conds, groups, {}), {})
        new = dict(zip(t["group"], t["stars"]))
        old = _old_stars(groups)
        for gi, star in old.items():
            assert new[conds[gi]] == star, (trial, gi, groups)


def test_figure_scope_correction_differs_from_gene_scope():
    rng = np.random.default_rng(1)
    conds = ["C", "A", "B"]
    genes = [{"symbol": f"G{i}", "replicates": [list(rng.normal(0, 1, 3)), list(rng.normal(1.5, 1, 3)),
                                                list(rng.normal(0, 1, 3))]} for i in range(4)]
    per_gene = [tfb.gene_tests(g["symbol"], conds, g["replicates"], {}) for g in genes]
    params = {"stat_correction": "bonferroni"}
    by_gene = pd.concat([tfb._correct(t, params) for t in per_gene], ignore_index=True)
    by_fig = tfb._correct(pd.concat(per_gene, ignore_index=True), params)
    assert np.allclose(by_fig["p_adj"], np.minimum(by_fig["p"] * 8, 1))
    assert np.allclose(by_gene["p_adj"], np.minimum(by_gene["p"] * 2, 1))


def test_grid_records_the_table():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    stats.take()
    fig = plt.figure()
    genes = [{"symbol": "JUN", "replicates": [[1, 2, 3], [4, 5, 6], [1, 2, 2]]},
             {"symbol": "FOS", "replicates": [[1, 1, 2], [9, 8, 7], [2, 2, 1]]}]
    tfb.render_tf_expression_scatter_grid(fig, genes, ["Ctrl", "A", "B"], params={"stat_correction": "bh"})
    plt.close(fig)
    (t,) = stats.take()
    assert t["name"] == "tf_expression_tests"
    df = t["df"]
    assert list(df["gene"]) == ["JUN", "JUN", "FOS", "FOS"]
    assert {"p", "p_adj", "stars", "anova_p", "correction", "test"} <= set(df.columns)
    assert (df["correction"] == "bh").all()
