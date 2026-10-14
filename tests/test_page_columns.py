"""Named column widths: a figure states how many journal columns it spans
(figures.page_columns) and the journal preset gives the width; the dumbbell's
4x1 layout fits one column."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402
import yaml  # noqa: E402

from fig_atlas.page import PageSpec  # noqa: E402
from fig_atlas.renderers import render_paired_dumbbell  # noqa: E402


def _write_preset(root, name, data):
    d = root / "styles"
    d.mkdir(exist_ok=True)
    (d / f"{name}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_page_names_its_column_widths():
    page = PageSpec.from_dict({"name": "j", "content_width_mm": 183, "content_height_mm": 247,
                               "columns_mm": {"1": 89, 1.5: 120, "2": 183}})
    assert page.column_width_mm(1) == 89
    assert page.column_width_mm("1.5") == 120
    assert page.column_width_mm(2.0) == 183
    one = page.spanning(1)
    assert one.content_width_mm == 89 and one.content_height_mm == 247
    assert one.figure_size_in(height_mm=50)[0] == pytest.approx(89 / 25.4)


def test_unnamed_span_is_refused():
    page = PageSpec.from_dict({"name": "a4", "paper_mm": [210, 297], "margin_mm": 12.7})
    with pytest.raises(ValueError, match="names no 1-column width"):
        page.column_width_mm(1)


@pytest.mark.parametrize("journal, width", [("journal_nature", 89), ("journal_science", 89),
                                            ("journal_generic", 85)])
def test_one_column_follows_the_journal(make_config, journal, width):
    _write_preset(make_config.root, "one_column", {"figures": {"page_columns": 1}})
    config = make_config(project={"style": [journal, "one_column"]})
    assert config.page.content_width_mm == width


def test_no_span_keeps_the_full_width(make_config):
    config = make_config(project={"style": ["journal_nature"]})
    assert config.page.content_width_mm == 183


@pytest.mark.parametrize("layout, n_axes_columns", [("2x2", 2), ("4x1", 1)])
def test_dumbbell_facet_layout(layout, n_axes_columns):
    conds = ["A", "B"]
    counts = {s: {c: (10, 20) for c in conds} for s in ("human_rna", "mouse_rna", "human_atac", "mouse_atac")}
    fig = plt.figure(figsize=(3.5, 5))
    out = render_paired_dumbbell(fig=fig, gs_target=fig.add_gridspec(1, 1)[0, 0], counts=counts, conditions=conds,
                                 params={"facet_layout": layout})
    lefts = {round(ax.get_position().x0, 3) for ax in out["axes"].values()}
    assert len(out["axes"]) == 4 and len(lefts) == n_axes_columns
    if layout == "4x1":                          # assay by assay, UP above DOWN
        tops = [out["axes"][k].get_position().y0 for k in [(0, 0), (1, 0), (0, 1), (1, 1)]]
        assert tops == sorted(tops, reverse=True)
    plt.close(fig)
