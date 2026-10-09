"""Statistics layer (roadmap Phase 4a): tests, multiple-testing correction,
significance stars, and test tables that travel with the figure.

Testing and drawing are separate. A renderer (or analysis script) runs the
tests here, gets a DataFrame with one row per comparison, draws stars from
its adjusted P column, and registers the table::

    from fig_atlas import stats
    table = stats.compare_to_control(groups, control="Control", test="welch")
    table["p_adj"] = stats.adjust(table["p"], "bh")
    table["stars"] = [stats.stars(p, thresholds) for p in table["p_adj"]]
    stats.record(table, name="tf_expression", title="Each condition vs control")
    fig.savefig(...)

Tables registered since the previous ``savefig`` belong to the figure saved
next. ``fa build`` writes them as CSV beside that figure
(``<stem>.statistics/<name>.csv``) and lists them in the provenance record;
publish copies them to ``figure_NN_statistics/`` and names them in the
README's statistics tables. Outside ``fa build`` registering is a no-op.

Tests are scipy's; corrections are implemented here (no extra dependency).
"""
from __future__ import annotations

import hashlib
import math
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

TESTS = ("welch", "student", "mannwhitney")
CORRECTIONS = ("none", "bonferroni", "holm", "bh")
DEFAULT_THRESHOLDS = [[0.001, "***"], [0.01, "**"], [0.05, "*"]]

PENDING: list[dict] = []


# ------------------------------------------------------------------- tests --
def _clean(values) -> np.ndarray:
    a = np.asarray(values, dtype=float).ravel()
    return a[~np.isnan(a)]


def two_group(a, b, test: str = "welch") -> tuple[float, float, str]:
    """Test ``b`` against ``a``; returns (statistic, p, note). The statistic
    is b relative to a: positive when b is higher (for Mann-Whitney, U of b).

    When both groups are constant there is nothing to test: p = 1 with note
    'both groups constant'. A test that raises gives p = 1 with note
    'test failed'. A t-test with a single value in a group gives NaN."""
    if test not in TESTS:
        raise ValueError(f"unknown test {test!r}; use one of {TESTS}")
    a, b = _clean(a), _clean(b)
    if not (np.var(a) > 0 or np.var(b) > 0):
        return math.nan, 1.0, "both groups constant"
    from scipy import stats as st
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)   # n = 1: NaN, reported in the table
            # b first: a positive statistic means b is higher than a (two-sided p is the same).
            if test == "mannwhitney":
                r = st.mannwhitneyu(b, a, alternative="two-sided")
            else:
                r = st.ttest_ind(b, a, equal_var=(test == "student"))
        return float(r.statistic), float(r.pvalue), ""
    except Exception:
        return math.nan, 1.0, "test failed"


def compare_to_control(groups: dict, control: str, test: str = "welch", min_control_n: int = 2) -> pd.DataFrame:
    """Each group against ``control``, in the order of ``groups``.

    Columns: group, control, test, n, n_control, mean, mean_control,
    statistic, p, note. A group with no values gets a row with p NaN; with
    fewer than ``min_control_n`` control values every p is NaN."""
    ctrl = _clean(groups[control])
    rows = []
    for name, values in groups.items():
        if name == control:
            continue
        v = _clean(values)
        row = {"group": name, "control": control, "test": test, "n": int(v.size), "n_control": int(ctrl.size),
               "mean": float(v.mean()) if v.size else math.nan,
               "mean_control": float(ctrl.mean()) if ctrl.size else math.nan}
        if v.size == 0:
            row.update(statistic=math.nan, p=math.nan, note="no values")
        elif ctrl.size < min_control_n:
            row.update(statistic=math.nan, p=math.nan, note=f"control has fewer than {min_control_n} values")
        else:
            s, p, note = two_group(ctrl, v, test)
            row.update(statistic=s, p=p, note=note)
        rows.append(row)
    return pd.DataFrame(rows, columns=["group", "control", "test", "n", "n_control", "mean", "mean_control",
                                       "statistic", "p", "note"])


def anova(groups) -> tuple[float, float]:
    """One-way ANOVA over the non-empty groups; (F, p), NaN when it cannot
    be computed (fewer than two groups, or every group constant)."""
    valid = [g for g in (_clean(x) for x in groups) if g.size > 0]
    if len(valid) < 2 or not any(np.var(g) > 1e-12 for g in valid):
        return math.nan, math.nan
    from scipy import stats as st
    try:
        f, p = st.f_oneway(*valid)
        return float(f), float(p)
    except Exception:
        return math.nan, math.nan


# -------------------------------------------------------------- correction --
def adjust(p, method: str = "none") -> np.ndarray:
    """Multiple-testing correction over one family of P values. NaNs are
    left out of the family and stay NaN. Methods: none, bonferroni, holm,
    bh (Benjamini-Hochberg false discovery rate)."""
    if method not in CORRECTIONS:
        raise ValueError(f"unknown correction {method!r}; use one of {CORRECTIONS}")
    p = np.asarray(p, dtype=float)
    out = p.copy()
    ok = ~np.isnan(p)
    m = int(ok.sum())
    if method == "none" or m == 0:
        return out
    q = p[ok]
    if method == "bonferroni":
        adj = np.minimum(q * m, 1.0)
    else:
        order = np.argsort(q, kind="mergesort")
        ranked = q[order]
        if method == "holm":
            stepped = np.maximum.accumulate((m - np.arange(m)) * ranked)
        else:  # bh
            # p * m / rank, in this order: same rounding as the earlier chip_support code
            stepped = np.minimum.accumulate(ranked[::-1] * m / np.arange(m, 0, -1))[::-1]
        adj = np.empty(m)
        adj[order] = np.minimum(stepped, 1.0)
    out[ok] = adj
    return out


def stars(p, thresholds=None, ns: str = "") -> str:
    """Symbol for P value ``p``: the first [threshold, symbol] pair (ascending
    thresholds) with p < threshold; ``ns`` otherwise or when p is NaN."""
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ns
    for thr, sym in (thresholds if thresholds is not None else DEFAULT_THRESHOLDS):
        if p < float(thr):
            return str(sym)
    return ns


TEST_NAMES = {"welch": "Welch's t-test", "student": "Student's t-test", "mannwhitney": "Mann-Whitney U test"}
CORRECTION_NAMES = {"bonferroni": "Bonferroni", "holm": "Holm", "bh": "Benjamini-Hochberg"}


def describe(test: str, correction: str = "none", thresholds=None, against: str = "control",
             family: str = "") -> str:
    """Legend phrase for the stars, from the same settings that drew them:
    "Welch's t-test versus control (*P < 0.05, **P < 0.01, ***P < 0.001)";
    with a correction, "..., Benjamini-Hochberg-adjusted <family> (*adjusted P < 0.05, ...)"."""
    text = f"{TEST_NAMES[test]} versus {against}"
    p = "P"
    if correction != "none":
        text += f", {CORRECTION_NAMES[correction]}-adjusted" + (f" {family}" if family else "")
        p = "adjusted P"
    pairs = sorted((thresholds if thresholds is not None else DEFAULT_THRESHOLDS), key=lambda t: -float(t[0]))
    return text + " (" + ", ".join(f"{sym}{p} < {float(thr):g}" for thr, sym in pairs) + ")"


# ------------------------------------------------------------------ record --
def record(df: pd.DataFrame, name: str, title: str = "", note: str = "") -> pd.DataFrame:
    """Register a test table for the figure saved next; returns ``df``.
    A name used twice before one save gets a numbered suffix (``_2``, ...)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError(f"name must be letters, digits, '_' or '-': {name!r}")
    taken = {t["name"] for t in PENDING}
    final, k = name, 2
    while final in taken:
        final, k = f"{name}_{k}", k + 1
    PENDING.append({"name": final, "title": title, "note": note, "df": df.copy()})
    return df


def take() -> list[dict]:
    """Tables registered since the last call (the recorder takes them on savefig)."""
    out = PENDING[:]
    PENDING.clear()
    return out


def write(tables: list[dict], out_dir: Path, rel) -> list[dict]:
    """Write tables as CSV into ``out_dir``; return their record entries."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.csv"):
        old.unlink()                               # a rebuild replaces the set
    entries = []
    for t in tables:
        path = out_dir / f"{t['name']}.csv"
        t["df"].to_csv(path, index=False, lineterminator="\n")
        entries.append({"name": t["name"], "title": t["title"], "note": t["note"], "path": rel(path),
                        "rows": int(len(t["df"])), "columns": [str(c) for c in t["df"].columns],
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return entries
