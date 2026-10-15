"""render_dot_matrix places one dot per filled cell, sized by count and coloured by category."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas.renderers import render_dot_matrix  # noqa: E402

DATA = pd.DataFrame({"gene": ["A", "A", "B", "C"], "feature": ["CDS", "CDS", "UTR", "CDS"],
                     "n": [2, 1, 1, 4], "origin": ["x", "y", "y", "x"], "line": ["L1", "L1", "L1", "L2"]})


def test_cells_are_summed_and_take_the_first_category():
    fig, ax = plt.subplots()
    cells = render_dot_matrix(ax, DATA, {"row_col": "gene", "col_col": "feature", "size_col": "n",
                                         "color_col": "origin", "color_order": ["y", "x"],
                                         "row_group_col": "line"})
    a = cells[(cells["gene"] == "A") & (cells["feature"] == "CDS")].iloc[0]
    assert a["n"] == 3 and a["kind"] == "y"
    assert len(cells) == 3
    assert [t.get_text() for t in ax.get_yticklabels()] == ["A", "B", "C"]
    assert ax.get_legend() is not None
    plt.close(fig)


def test_orders_drop_unlisted_cells():
    fig, ax = plt.subplots()
    cells = render_dot_matrix(ax, DATA, {"row_col": "gene", "col_col": "feature", "row_order": ["A", "C"],
                                         "col_order": ["CDS"], "show_legend": False})
    assert set(cells["gene"]) == {"A", "C"}
    plt.close(fig)


def test_split_cells_show_one_dot_per_category():
    fig, ax = plt.subplots()
    cells = render_dot_matrix(ax, DATA, {"row_col": "gene", "col_col": "feature", "size_col": "n",
                                         "color_col": "origin", "multi": "split", "split_offset": 0.3})
    a = cells[(cells["gene"] == "A") & (cells["feature"] == "CDS")].sort_values("x")
    assert list(a["kind"]) == ["x", "y"] and list(a["n"]) == [2, 1]
    assert abs((a["x"].iloc[1] - a["x"].iloc[0]) - 0.3) < 1e-9
    plt.close(fig)
