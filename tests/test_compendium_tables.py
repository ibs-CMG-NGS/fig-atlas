"""Table pages of the compendium (plan T-05): one page per table; a table longer
than a page shows the rows that fit, in a stated order, and names the rest."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.tools import compile_storyline_pdf as c  # noqa: E402

PAGE = {"w": 595.0, "h": 842.0, "margin": 36.0, "content_w": 523.0, "content_h": 770.0}


def _entry(**render):
    return {"role": "Table 1", "file": "t.csv", "description": "A table", "render": render}


def _texts_of(pdf_path):
    from pypdf import PdfReader
    return PdfReader(pdf_path).pages[0].extract_text()


def test_wide_tables_turn_and_orientation_overrides():
    narrow = pd.DataFrame({f"c{i}": [1] for i in range(3)})
    wide = pd.DataFrame({f"c{i}": [1] for i in range(c.TABLE_PAGE["landscape_min_columns"])})
    assert c.table_layout(_entry(), narrow) == "portrait"
    assert c.table_layout(_entry(), wide) == "landscape"
    assert c.table_layout(_entry(orientation="portrait"), wide) == "portrait"
    assert c.table_layout(_entry(columns=["c0", "c1"]), wide) == "portrait", "only the printed columns count"


def test_auto_formats_drop_float_noise_but_keep_whole_numbers_whole():
    df = pd.DataFrame({"pos": [90534207.0, None], "share": [0.4871234, 0.5], "name": ["a", "b"], "n": [1, 2],
                       "base_mean": [40.29, 32623.41]})
    assert c._auto_formats(df) == {"pos": ".0f", "share": ".4g", "base_mean": ",.1f"}, \
        "text and integer columns print as they are; a column into the thousands avoids e-notation"


def test_auto_formats_group_the_digits_of_large_integers():
    """A genomic coordinate stored as an integer printed as 7301884 while the same
    table wrote its text coordinates as chr1:24,905,310. Counts stay plain."""
    df = pd.DataFrame({"breakpoint": [7301884, 24905310], "size_bp": [41280, 60310],
                       "split_reads": [11, 7], "year": [2026, 2026]})
    assert c._auto_formats(df) == {"breakpoint": ",d", "size_bp": ",d"}, \
        "five figures and up are grouped; small counts (and four-figure values) are left alone"


def test_transpose_turns_the_first_column_into_headings():
    df = pd.DataFrame({"line": ["A", "B"], "copies": [2, 6]})
    t = c._table_data(_entry(transpose=True), df)
    assert list(t.columns) == ["line", "A", "B"] and list(t.iloc[0]) == ["copies", 2, 6]


def test_sort_by_decides_which_rows_come_first():
    df = pd.DataFrame({"gene": ["a", "b", "c"], "p": [0.5, 0.001, None]})
    assert list(c._table_data(_entry(sort_by="p"), df)["gene"]) == ["b", "a", "c"], "missing values last"
    assert list(c._table_data(_entry(sort_by="p", sort_ascending=False), df)["gene"]) == ["a", "b", "c"]
    with pytest.raises(ValueError, match="not a column"):
        c._table_data(_entry(sort_by="nope"), df)


def test_a_table_that_fits_shows_every_row(tmp_path):
    df = pd.DataFrame({"name": ["a", "b"], "n": [1, 2]})
    assert c.rows_that_fit(_entry(), df, "portrait", PAGE, tmp_path / "probe.pdf") == 2


def test_measuring_a_very_long_table_never_draws_it_whole(tmp_path, monkeypatch):
    """A 26,000-row table must cost a handful of page-sized drawings, not one of 26,000 rows."""
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(26000)], "p": [0.5] * 26000})
    asked = []
    real = c.generate_table_page

    def spy(*args, shown=None, **kw):
        asked.append(shown)
        return real(*args, shown=shown, **kw)

    monkeypatch.setattr(c, "generate_table_page", spy)
    shown = c.rows_that_fit(_entry(), df, "portrait", PAGE, tmp_path / "probe.pdf")
    assert 1 < shown <= c.TABLE_PAGE["probe_rows_max"]
    assert max(asked) <= c.TABLE_PAGE["probe_rows_max"] and len(asked) <= 10


def test_a_long_table_shows_the_rows_that_fit_and_names_the_rest(tmp_path):
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(5000)], "p": [i / 5000 for i in range(5000)][::-1]})
    entry = _entry(sort_by="p")
    shown = c.rows_that_fit(entry, df, "portrait", PAGE, tmp_path / "probe.pdf")
    assert 1 < shown < len(df)
    used = c.generate_table_page(entry, df, "portrait", PAGE, tmp_path / "page.pdf", 3, 9, shown=shown)
    assert used <= PAGE["content_h"], "what is shown fits the page"
    assert c.generate_table_page(entry, df, "portrait", PAGE, tmp_path / "over.pdf", 3, 9,
                                 shown=shown + 1) > PAGE["content_h"], "and one more row would not"
    text = _texts_of(tmp_path / "page.pdf")
    assert f"first {shown:,} of 5,000 rows" in text and "sorted by p (ascending)" in text
    assert f"other {5000 - shown:,} are in the CSV file" in text
    assert "g4999" in text, "sorted by p: the smallest p is shown first"
