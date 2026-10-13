"""The documentation site in two languages (docs/decisions/0006): English is
the source, page.md; the Korean version is page.ko.md beside it. These tests
keep the two in step -- a change to one that the other lacks fails here --
and keep docs/i18n_pending.txt, the pages not yet in English, exact.

What is compared is structure, not wording: the order of heading levels, the
code blocks, the tutorial step markers, images, tables and link targets.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PENDING = DOCS / "i18n_pending.txt"
HANGUL = re.compile(r"[가-힣]")
FENCE = re.compile(r"^```(?P<lang>[\w-]*)[^\n]*\n(?P<body>.*?)^```", re.S | re.M)
MARKER = re.compile(r"<!-- (?:run|replace: .+?|file: \S+) -->")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)")
# Comments in these blocks are prose and are translated; the rest must match.
COMMENTED = {"bash": "#", "sh": "#", "powershell": "#", "python": "#", "yaml": "#", "toml": "#"}


def _prose(text: str) -> str:
    return FENCE.sub("", text)


def is_korean(text: str) -> bool:
    return len(HANGUL.findall(_prose(text))) > 40


def pending() -> list[str]:
    return [ln.strip() for ln in PENDING.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def _uncomment(lang: str, body: str) -> str:
    mark = COMMENTED.get(lang)
    if not mark:
        return body
    out = []
    for line in body.splitlines():
        if line.lstrip().startswith(mark):
            continue
        out.append(re.sub(r"\s+" + re.escape(mark) + r"(?![^\"']*[\"']\s*$).*$", "", line).rstrip())
    return "\n".join(out)


def structure(text: str) -> dict:
    blocks = [(m.group("lang"), m.group("body")) for m in FENCE.finditer(text)]
    prose = _prose(text)
    return {
        "headings": [len(m.group(1)) for m in re.finditer(r"^(#{1,6}) ", prose, re.M)],
        "code": [(lang, "(diagram)" if lang == "mermaid" else _uncomment(lang, body)) for lang, body in blocks],
        "markers": MARKER.findall(text),
        "images": IMAGE.findall(prose),
        "tables": len(re.findall(r"^\|[-:| ]+\|\s*$", prose, re.M)),
        "links": [t.split("#")[0] for t in LINK.findall(prose) if t.split("#")[0]],
    }


def pages() -> list[Path]:
    return sorted(p for p in DOCS.rglob("*.md") if not p.name.endswith(".ko.md"))


def test_pending_list_is_exact():
    """Every page still in Korean is listed, and only those."""
    listed = pending()
    assert len(listed) == len(set(listed)), "a page is listed twice"
    missing = [rel for rel in listed if not (DOCS / rel).is_file()]
    assert not missing, f"listed but no such page: {missing}"
    korean = {p.relative_to(DOCS).as_posix() for p in pages() if is_korean(p.read_text(encoding="utf-8"))}
    assert not korean - set(listed), (f"pages in Korean that are not in {PENDING.name} -- write the English "
                                      f"page.md and keep the Korean as page.ko.md: {sorted(korean - set(listed))}")
    assert not set(listed) - korean, f"pages now in English: remove them from {PENDING.name}: {sorted(set(listed) - korean)}"


@pytest.mark.parametrize("ko", sorted(DOCS.rglob("*.ko.md")), ids=lambda p: p.relative_to(DOCS).as_posix())
def test_korean_page_matches_its_english_page(ko):
    en = ko.with_name(ko.name[:-len(".ko.md")] + ".md")
    rel = en.relative_to(DOCS).as_posix()
    assert en.is_file(), f"{ko.name} has no English page {en.name}"
    assert rel not in pending(), f"{rel} has a Korean version, so it is translated: remove it from {PENDING.name}"
    a, b = structure(en.read_text(encoding="utf-8")), structure(ko.read_text(encoding="utf-8"))
    for key in a:
        assert a[key] == b[key], f"{rel}: {key} differ between the English and the Korean page"


def test_structure_reads_what_it_should():
    text = ("# T\n\n## S\n\n<!-- run -->\n```bash\nfa build x  # 빌드\n```\n\n![a](img/x.png)\n\n"
            "| a |\n|---|\n| 1 |\n\n[g](guide/01.md#왜)\n\n```mermaid\nflowchart TD\n  A[\"가\"]\n```\n")
    s = structure(text)
    assert s["headings"] == [1, 2] and s["markers"] == ["<!-- run -->"] and s["images"] == ["img/x.png"]
    assert s["tables"] == 1 and s["links"] == ["guide/01.md"]
    assert s["code"] == [("bash", "fa build x"), ("mermaid", "(diagram)")]
