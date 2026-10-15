"""render_segment_array lays segments out in order, with arrows, gaps and flanks."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas_omics.renderers import render_segment_array  # noqa: E402

DATA = pd.DataFrame({
    "kind": ["host", "tg", "copy_gap", "tg", "host"],
    "label": ["chr2:100", "TG1", None, "TG2", "chr2:104"],
    "length_bp": [0, 2000, 400, 2000, 0],
    "strand": ["NA", "-", "NA", "+", "NA"],
})


def test_segments_fill_the_row_in_order():
    fig, ax = plt.subplots()
    drawn = render_segment_array(ax, DATA, {"flank_frac": 0.1})
    assert list(drawn["x0"].diff().dropna() > 0) == [True] * 4
    assert abs(drawn["x1"].iloc[-1] - 1.0) < 1e-9
    assert abs((drawn["x1"] - drawn["x0"]).iloc[0] - 0.1) < 1e-9
    assert len(ax.patches) == 4                       # two flanks + two arrows; the gap is a line
    plt.close(fig)


def test_short_segments_keep_a_minimum_width():
    df = pd.DataFrame({"kind": ["tg", "copy_gap", "tg"], "length_bp": [100000, 4, 100000], "strand": ["+"] * 3})
    fig, ax = plt.subplots()
    drawn = render_segment_array(ax, df, {"min_frac": 0.05, "flank_kinds": [], "label_col": None})
    assert (drawn["x1"] - drawn["x0"]).iloc[1] >= 0.05 - 1e-9
    plt.close(fig)


def test_groups_get_one_label():
    df = DATA.assign(copy=[None, "copy 1", None, "copy 2", None])
    fig, ax = plt.subplots()
    render_segment_array(ax, df, {"group_col": "copy", "labels_title": "T"})
    texts = [t.get_text() for t in ax.texts]
    assert "copy 1" in texts and "TG1" not in texts and ax.get_title(loc="left") == "T"
    plt.close(fig)


def test_names_inside_or_under_and_span_arrows():
    df = pd.DataFrame({"kind": ["tg", "tg", "pass"], "length_bp": [3000, 3000, 30],
                       "name": ["promoter", None, "a rather long passenger name"],
                       "copy": ["c1", "c1", None], "coords": ["6,000-1", "6,000-1", None],
                       "strand": ["-", "-", None]})
    fig, ax = plt.subplots(figsize=(6, 1))
    render_segment_array(ax, df, {"flank_kinds": [], "label_col": None, "inner_label_col": "name",
                                  "span_col": "copy", "span_label_col": "coords", "strand_col": None,
                                  "span_strand_col": "strand", "kind_colors": {"tg": "#111111"}})
    texts = {t.get_text(): t for t in ax.texts}
    assert texts["promoter"].get_color() == "#ffffff"            # light text on a dark fill
    assert texts["a rather long passenger name"].get_va() == "top"   # too narrow: moved under the bar
    assert list(texts).count("6,000-1") == 1                        # one span label for the two rows
    plt.close(fig)
