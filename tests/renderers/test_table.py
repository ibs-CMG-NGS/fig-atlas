"""render_table draws a classic summary table.

The checks here are about what makes a table readable rather than about pixels:
per-column formatting and alignment, widths that respond to the content,
wrapping, the three rules, and the row limit. The snapshot case in
tests/renderers/cases.py catches unintended visual changes.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

from fig_atlas.renderers import render_table  # noqa: E402

DATA = pd.DataFrame({
    "assay": ["J1", "J2", "WT allele"],
    "size_bp": [412, 1037, 268],
    "share": [0.4871234, 0.0049, None],
})


def _texts(ax):
    return [t.get_text() for t in ax.texts]


def _draw(df, params):
    """Draw on a figure with a real extent, so the point-based geometry resolves."""
    fig, ax = plt.subplots(figsize=(6, 3), dpi=100)
    fig.canvas.draw()
    drawn = render_table(ax, df, params)
    return fig, ax, drawn


def test_draws_every_row_and_the_three_rules():
    fig, ax, drawn = _draw(DATA, {})
    assert len(drawn) == len(DATA)
    assert len(ax.lines) == 3, "top, header and bottom rule"
    assert "J1" in _texts(ax) and "assay" in _texts(ax)
    plt.close(fig)


def test_column_format_is_applied_per_column():
    fig, ax, drawn = _draw(DATA, {"column_format": {"share": ".3f", "size_bp": ",.0f"}})
    assert list(drawn["share"])[:2] == ["0.487", "0.005"]
    assert list(drawn["size_bp"])[1] == "1,037"
    plt.close(fig)


def test_missing_value_prints_na_text():
    fig, ax, drawn = _draw(DATA, {"column_format": {"share": ".3f"}, "na_text": "n/a"})
    assert list(drawn["share"])[2] == "n/a"
    plt.close(fig)


def test_numeric_columns_align_right_by_default_and_align_overrides():
    fig, ax, _ = _draw(DATA, {})
    by_text = {t.get_text(): t for t in ax.texts}
    assert by_text["412"].get_ha() == "right"
    assert by_text["J1"].get_ha() == "left"
    plt.close(fig)

    fig, ax, _ = _draw(DATA, {"column_align": {"size_bp": "center"}})
    assert {t.get_text(): t for t in ax.texts}["412"].get_ha() == "center"
    plt.close(fig)


def test_columns_selects_and_orders_and_labels_rename():
    fig, ax, drawn = _draw(DATA, {"columns": ["size_bp", "assay"],
                                  "column_labels": {"size_bp": "Amplicon (bp)"}})
    assert list(drawn.columns) == ["size_bp", "assay"]
    assert "Amplicon (bp)" in _texts(ax) and "share" not in _texts(ax)
    plt.close(fig)


def test_unknown_column_is_an_error():
    fig, ax = plt.subplots()
    with pytest.raises(ValueError, match="columns not in the data"):
        render_table(ax, DATA, {"columns": ["assay", "nope"]})
    plt.close(fig)


def test_column_width_responds_to_the_content():
    """A long cell must widen its column: the next column starts further right."""
    narrow = pd.DataFrame({"a": ["x"], "b": ["y"]})
    wide = pd.DataFrame({"a": ["x" * 40], "b": ["y"]})
    fig, ax, _ = _draw(narrow, {"wrap": False})
    x_narrow = {t.get_text(): t.get_position()[0] for t in ax.texts}["y"]
    plt.close(fig)
    fig, ax, _ = _draw(wide, {"wrap": False})
    x_wide = {t.get_text(): t.get_position()[0] for t in ax.texts}["y"]
    plt.close(fig)
    assert x_wide > x_narrow


def test_a_short_column_keeps_its_longest_word_beside_a_long_text_column():
    """A long notes column must not squeeze a short column below its longest
    word: a word cannot wrap, so it would run into the next column."""
    df = pd.DataFrame({"line": ["Condition-A-long-name"], "id": ["X-1"],
                       "note": [" ".join(["lorem ipsum dolor sit amet"] * 30)]})
    fig, ax, _ = _draw(df, {"max_lines": 20})
    texts = {t.get_text(): t for t in ax.texts}
    fig.canvas.draw()
    name, nxt = texts["Condition-A-long-name"], texts["X-1"]
    r = fig.canvas.get_renderer()
    assert name.get_window_extent(r).x1 <= nxt.get_window_extent(r).x0, "the name runs into the next column"
    plt.close(fig)


def test_a_word_wider_than_its_column_is_broken_not_overrun():
    df = pd.DataFrame({"a": ["collateral_rearrangement_of_the_host"], "b": ["next"]})
    fig, ax, _ = _draw(df, {"column_width": {"a": 0.08, "b": 0.5}, "max_lines": 10})
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    parts = [t for t in ax.texts if t.get_text() and "collateral_rearrangement_of_the_host".startswith(t.get_text())]
    nxt = next(t for t in ax.texts if t.get_text() == "next")
    assert parts, "the long word is drawn"
    assert max(t.get_window_extent(r).x1 for t in ax.texts if t.get_text() not in ("next", "b", "a")
               and t.get_position()[0] < nxt.get_position()[0]) <= nxt.get_window_extent(r).x0
    plt.close(fig)


def test_wrap_breaks_a_long_cell_into_lines():
    long = pd.DataFrame({"note": ["one two three four five six seven eight nine ten"], "n": [1]})
    fig, ax, _ = _draw(long, {"wrap": True, "max_lines": 3, "column_width": {"note": 0.3, "n": 0.1}})
    wrapped = [t.get_text() for t in ax.texts if t.get_text().startswith("one")]
    assert wrapped and wrapped[0] != "one two three four five six seven eight nine ten"
    plt.close(fig)


def test_a_cell_cut_at_max_lines_says_so():
    long = pd.DataFrame({"note": [" ".join(f"word{i}" for i in range(60))], "n": [1]})
    fig, ax, _ = _draw(long, {"max_lines": 2, "column_width": {"note": 0.3, "n": 0.1}})
    lines = [t.get_text() for t in ax.texts if t.get_text().startswith("word")]
    assert len(lines) == 2 and lines[-1].endswith("…")
    plt.close(fig)
    fig, ax, _ = _draw(pd.DataFrame({"note": ["short text"], "n": [1]}), {"max_lines": 2})
    assert not any(t.get_text().endswith("…") for t in ax.texts), "an uncut cell carries no mark"
    plt.close(fig)


def test_max_rows_truncates_and_notes_how_many():
    many = pd.DataFrame({"i": range(10)})
    fig, ax, drawn = _draw(many, {"max_rows": 4})
    assert len(drawn) == 4
    assert any("6 more rows" in t for t in _texts(ax))
    plt.close(fig)


def test_rules_can_be_switched_off():
    fig, ax, _ = _draw(DATA, {"rule_top_width": 0, "rule_header_width": 0, "rule_bottom_width": 0})
    assert len(ax.lines) == 0
    plt.close(fig)


def test_title_and_footnotes_are_drawn():
    fig, ax, _ = _draw(DATA, {"title": "Table 1", "footnotes": ["a, designed in silico", "b, not run"]})
    texts = _texts(ax)
    assert "Table 1" in texts and "a, designed in silico" in texts and "b, not run" in texts
    plt.close(fig)


def test_a_column_a_hair_narrower_than_its_longest_word_still_keeps_it_whole():
    """A column that asks for nothing beyond its longest word is given exactly that
    word's measured width, and the widths are then scaled if their sum overshoots the
    table by one bit of floating point. Judged strictly, that one bit broke the word
    between characters -- and every row below it moved, so the same table rendered
    differently on another machine. A fit is judged with a hair of slack instead."""
    from fig_atlas.renderers.table import _FIT_TOLERANCE_PT, _text_width_pt, _wrap

    fig, ax = plt.subplots(figsize=(6, 3), dpi=100)
    fig.canvas.draw()
    font = FontProperties(size=5.5)
    word = "Condition-A-long-name"
    exact = _text_width_pt(word, font, fig)
    for shave in (0.0, 1e-13, 1e-9, _FIT_TOLERANCE_PT / 2):
        assert _wrap(word, exact - shave, font, fig, 20) == [word], f"broken after shaving {shave}"
    assert _wrap(word, exact - 2 * _FIT_TOLERANCE_PT, font, fig, 20) != [word], \
        "a column genuinely narrower than the word must still break it"
    plt.close(fig)


def test_a_long_title_wraps_to_the_table_width_instead_of_running_off_the_page():
    """An unwrapped title overran the page in the compendium. It must break like a
    cell does -- over several lines, each inside the table -- and never be cut: it
    is the author's own text, so every word of it is still there."""
    long_title = ("Supplementary Table S9 | Assay Coordinates, Supporting Read Counts, Phased Allele "
                  "Orientations and Marker Positions across Every Condition in the Study")
    fig, ax, _ = _draw(DATA, {"title": long_title})
    lines = [t for t in ax.texts if t.get_fontproperties().get_weight() == "bold"
             and t.get_text() in long_title]
    assert len(lines) > 1, "the title should have broken over several lines"
    assert " ".join(t.get_text() for t in lines) == long_title, "no word of the title may be lost"
    fig.canvas.draw()
    right = max(t.get_window_extent(fig.canvas.get_renderer()).x1 for t in lines)
    assert right <= ax.get_window_extent().x1 + 1, "no title line may run past the table"
    plt.close(fig)


def test_column_groups_draw_a_spanning_label_under_the_top_rule():
    """Convention order: top rule, then the spanning row, then its partial rule."""
    fig, ax, _ = _draw(DATA, {"column_groups": [{"label": "Design", "columns": ["size_bp", "share"]}]})
    assert "Design" in _texts(ax)
    assert len(ax.lines) == 4, "three table rules plus the group rule"
    top_rule, group_rule = ax.lines[0], ax.lines[1]
    assert top_rule.get_xdata()[0] == 0, "the top rule spans the table"
    assert group_rule.get_xdata()[0] > 0, "the group rule spans its own columns, not the table"
    assert group_rule.get_ydata()[0] < top_rule.get_ydata()[0], "the spanning row sits under the top rule"
    plt.close(fig)


def test_style_preset_supplies_the_look_and_a_config_key_still_wins():
    """T-03: the look comes from the `table:` block of a style preset, and the
    renderer falls back to the same values when no preset defines it."""
    from fig_atlas.renderers.table import SCHEMA

    assert SCHEMA.default("cell_size", None) == SCHEMA.default("cell_size", {}), "no preset: its own fallback"
    assert SCHEMA.default("cell_size", {"table": {"cell_size": 7.0}}) == 7.0
    assert SCHEMA.default("row_stripe", {"table": {"row_stripe": True}}) is True

    fig, ax, _ = _draw(DATA, {"_style": {"table": {"header_weight": "normal", "cell_size": 7.0}}})
    cells = [t for t in ax.texts if t.get_text() == "J1"]
    assert cells and cells[0].get_fontsize() == 7.0
    plt.close(fig)

    fig, ax, _ = _draw(DATA, {"cell_size": 9.0, "_style": {"table": {"cell_size": 7.0}}})
    cells = [t for t in ax.texts if t.get_text() == "J1"]
    assert cells and cells[0].get_fontsize() == 9.0, "the figure's own config beats the preset"
    plt.close(fig)


def test_shipped_classic_preset_matches_the_schema_fallbacks():
    """Adding table_classic must not change a table that was drawn without it."""
    from pathlib import Path

    import yaml

    from fig_atlas.config import style_path
    from fig_atlas.renderers.table import SCHEMA

    preset = yaml.safe_load(style_path(Path(__file__).resolve().parents[2], "table_classic").read_text(encoding="utf-8"))
    for key, value in preset["table"].items():
        assert SCHEMA.default(key, None) == value, f"table_classic.{key} disagrees with the schema fallback"


def test_drawn_height_is_reported_for_page_layout():
    few, many = pd.DataFrame({"i": range(3)}), pd.DataFrame({"i": range(20)})
    fig, ax, small = _draw(few, {})
    plt.close(fig)
    fig, ax, big = _draw(many, {})
    plt.close(fig)
    assert big.attrs["height_pt"] > small.attrs["height_pt"] > 0


def test_row_stripe_is_off_by_default_and_can_be_turned_on():
    fig, ax, _ = _draw(DATA, {})
    assert not ax.patches
    plt.close(fig)
    fig, ax, _ = _draw(DATA, {"row_stripe": True})
    assert ax.patches, "striped rows draw a span"
    plt.close(fig)
