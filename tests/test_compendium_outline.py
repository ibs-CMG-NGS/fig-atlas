"""Bookmarks of the compendium: the cover, each figure and table under its kind, and the
appendix, each pointing at the page it starts on."""
from __future__ import annotations

from pypdf import PdfReader, PdfWriter

from fig_atlas.tools import compile_storyline_pdf as c


def _fig(role, title, page):
    return {"meta": {"role": role, "title": title}, "figure_page_no": page}


def _tab(role, description, page):
    return {"entry": {"role": role, "description": description}, "page_no": page}


def test_groups_are_the_slot_kinds_made_plural():
    assert c._outline_group("Main Figure 1", "Figures") == "Main Figures"
    assert c._outline_group("Supplementary Figure S3", "Figures") == "Supplementary Figures"
    assert c._outline_group("Main Table 2", "Tables") == "Main Tables"
    assert c._outline_group("Overview", "Figures") == "Figures", "a role with no number falls back"


def test_long_titles_are_cut_at_a_word():
    t = c._outline_title("Main Figure 1", "word " * 40)
    assert len(t) <= c.OUTLINE_TITLE_CHARS + 1 and t.endswith("…") and not t.endswith(" …")
    assert c._outline_title("Main Table 1", "") == "Main Table 1"
    assert c._outline_title("Main Figure 2", "A short title.") == "Main Figure 2 — A short title"


def test_entries_point_at_the_page_each_item_starts_on():
    items = [_fig("Main Figure 1", "One", 2), _fig("Main Figure 2", "Two", 4), _fig("Supplementary Figure S1", "S", 5)]
    tables = [_tab("Main Table 1", "T", 6)]
    e = c.outline_entries(items, tables, total_pages=7)
    assert e[0] == (None, "Cover", 0)
    assert [(g, p) for g, _, p in e[1:-1]] == [("Main Figures", 1), ("Main Figures", 3),
                                               ("Supplementary Figures", 4), ("Main Tables", 5)]
    assert e[-1][0] is None and e[-1][2] == 6


def test_written_pdf_carries_nested_bookmarks(tmp_path):
    writer = PdfWriter()
    for _ in range(4):
        writer.add_blank_page(width=100, height=100)
    c.add_outline(writer, c.outline_entries([_fig("Main Figure 1", "One", 2), _fig("Main Figure 2", "Two", 3)],
                                            [], total_pages=4))
    out = tmp_path / "o.pdf"
    with open(out, "wb") as f:
        writer.write(f)

    r = PdfReader(out)
    top = r.outline
    titles = [o.title for o in top if not isinstance(o, list)]
    assert titles == ["Cover", "Main Figures", "Appendix — data, live numbers, source data, data requests"]
    children = next(o for o in top if isinstance(o, list))
    assert [(o.title, r.get_destination_page_number(o)) for o in children] == \
        [("Main Figure 1 — One", 1), ("Main Figure 2 — Two", 2)]
    assert r.trailer["/Root"]["/PageMode"] == "/UseOutlines"
