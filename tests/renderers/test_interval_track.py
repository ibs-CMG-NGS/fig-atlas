"""render_interval_track draws boxes, brackets and points, coloured by kind."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas_omics.renderers import render_interval_track  # noqa: E402

IV = pd.DataFrame({"start": [100, 150, 5000], "end": [900, 400, 5000],
                   "kind": ["del", "sv", "junction"], "label": ["Δ800 bp", "", "J1"]})


def test_overlaps_go_to_separate_rows_and_points_are_markers():
    fig, ax = plt.subplots()
    out = render_interval_track(ax, IV, {"x_min": 0, "x_max": 10000, "bracket_kinds": ["del"]})
    rows = out.set_index("kind")["row"]
    assert rows["del"] != rows["sv"]
    assert len(ax.patches) == 1                       # sv box; del is a bracket, junction a triangle
    assert ax.get_legend() is not None
    plt.close(fig)


def test_legend_kinds_lists_kinds_not_drawn_here():
    fig, ax = plt.subplots()
    render_interval_track(ax, IV, {"x_min": 0, "x_max": 10000, "legend_kinds": ["junction", "lost"],
                                   "kind_order": ["del", "lost", "junction"]})
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["lost", "junction"]
    plt.close(fig)


def test_open_intervals_extend_past_both_ends():
    df = pd.DataFrame({"start": [4000], "end": [6000], "kind": ["seg"], "label": [""]})
    fig, ax = plt.subplots()
    render_interval_track(ax, df, {"x_min": 0, "x_max": 10000, "bracket_kinds": ["seg"], "open_kinds": ["seg"],
                                   "open_extend_frac": 0.1, "show_legend": False})
    dotted = [ln for ln in ax.lines if ln.get_linestyle() == ":"]
    spans = sorted(tuple(ln.get_xdata()) for ln in dotted)
    assert spans == [(2999.0, 3999.0), (6000.0, 7000.0)]
    plt.close(fig)
