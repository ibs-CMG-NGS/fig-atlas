"""render_grouped_hbar keeps a zero-based axis unless a bar goes below zero."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas.renderers import render_grouped_hbar  # noqa: E402


def test_axis_starts_at_zero_for_positive_bars():
    df = pd.DataFrame({"category": ["a", "b"], "n": [3, 5]})
    fig, ax = plt.subplots()
    render_grouped_hbar(ax, df, {"series": ["n"], "xlim": [0, 6], "show_legend": False})
    assert ax.get_xlim() == (0.0, 6.0)
    plt.close(fig)


def test_negative_min_extends_the_axis_and_labels_go_left():
    df = pd.DataFrame({"category": ["a", "b"], "s": [-1.5, 2.0]})
    fig, ax = plt.subplots()
    render_grouped_hbar(ax, df, {"series": ["s"], "xlim": [-2, 2.5], "show_legend": False})
    assert ax.get_xlim() == (-2.0, 2.5)
    neg = [t for t in ax.texts if t.get_text() == "-1"]
    assert neg and neg[0].get_ha() == "right" and neg[0].get_position()[0] < -1.5
    plt.close(fig)
