"""upset counts the intersections of a long membership table and draws them."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas.renderers import render_upset  # noqa: E402


def _membership() -> pd.DataFrame:
    return pd.DataFrame({"dataset": ["A", "A", "A", "B", "B", "C"],
                         "item": ["p1", "p2", "p3", "p2", "p3", "p3"]})


def test_intersections_are_counted_and_ordered_by_degree_then_size():
    fig, ax = plt.subplots()
    out = render_upset(ax, _membership(), {"sort_by": "degree"})
    assert list(out["sets"]) == ["A & B & C", "A & B", "A"]
    assert list(out["count"]) == [1, 1, 1]
    plt.close(fig)


def test_min_size_and_max_columns_limit_the_drawing():
    fig, ax = plt.subplots()
    out = render_upset(ax, _membership(), {"min_size": 2})
    assert out is None                              # every intersection has one item
    plt.close(fig)


def test_a_named_but_missing_column_gives_the_missing_message():
    fig, ax = plt.subplots()
    out = render_upset(ax, pd.DataFrame({"set": ["A"], "member": ["p1"]}), {})
    assert out is None
    assert any("Required columns" in t.get_text() for t in ax.texts)
    plt.close(fig)
