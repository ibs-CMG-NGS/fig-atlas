"""The researcher guide (docs/guide/) stays maintainable and portable.

- every chapter is in the site navigation (no orphan pages) and carries its
  front matter (title, audience, last reviewed date);
- only plain Markdown: no MkDocs- or wiki-only syntax, so the pages read the
  same on GitHub and move to another documentation tool unchanged;
- the `fa` commands and repository paths it names exist;
- the pictures it shows are the ones scripts/make_guide_images.py makes.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest
import yaml

from fig_atlas.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guide"
# English chapters (in the navigation); PAGES adds their Korean versions, page.ko.md (docs/decisions/0006)
CHAPTERS = sorted(p for p in GUIDE.glob("*.md") if not p.name.startswith("_") and not p.name.endswith(".ko.md"))
PAGES = sorted(p for p in GUIDE.glob("*.md") if not p.name.startswith("_"))
TOP = ("configs", "analysis", "figure_specs", "fig_atlas", "scripts", "docs", "styles", "examples", ".vscode")


def _front_matter(page: Path) -> dict:
    text = page.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{page.name}: no front matter"
    return yaml.safe_load(text.split("---\n", 2)[1]) or {}


def _body(page: Path) -> str:
    return page.read_text(encoding="utf-8").split("---\n", 2)[2]


def _nav_pages() -> set[str]:
    class Loader(yaml.SafeLoader):
        pass
    Loader.add_multi_constructor("tag:yaml.org,2002:python/", lambda *a: None)    # mkdocs.yml python tags
    nav = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=Loader)["nav"]
    found = set()

    def walk(x):
        if isinstance(x, str):
            found.add(x)
        elif isinstance(x, list):
            for i in x:
                walk(i)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
    walk(nav)
    return found


def test_chapters_are_numbered_and_in_the_navigation():
    assert CHAPTERS, "no guide chapters"
    nav = _nav_pages()
    missing = [p.name for p in CHAPTERS if f"guide/{p.name}" not in nav]
    assert not missing, f"guide pages not in mkdocs.yml nav: {missing}"
    assert all(re.match(r"^\d\d-[a-z0-9-]+\.md$", p.name) for p in CHAPTERS)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_front_matter(page):
    meta = _front_matter(page)
    assert meta.get("title") and meta.get("audience"), page.name
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(meta.get("reviewed"))), f"{page.name}: reviewed date"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_plain_markdown_only(page):
    body = re.sub(r"```.*?```", "", _body(page), flags=re.S)
    tool_only = [ln for ln in body.splitlines()
                 if re.match(r"^\s*(!!!|\?\?\?)", ln) or "[[" in ln or re.search(r"\{:\s*[.#]", ln)]
    assert not tool_only, f"{page.name}: tool-specific syntax {tool_only[:3]}"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_named_commands_and_paths_exist(page):
    body = _body(page)
    sub = next(a for a in build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    bad = [c for c in re.findall(r"`fa ([a-z][a-z-]*)", body) if c not in sub.choices]
    for p in re.findall(r"`((?:%s)/[^`\s]*)`" % "|".join(TOP), body):
        layout = p.startswith(("docs/storylines", "docs/data_contracts", ".vscode/"))   # project-repository places
        if p.isascii() and not layout and not any(ch in p for ch in "<>*{}") and not (ROOT / p).exists():
            bad.append(p)
    assert not bad, f"{page.name}: names that do not exist: {bad}"


def test_pictures_come_from_the_image_script():
    script = (ROOT / "scripts" / "make_guide_images.py").read_text(encoding="utf-8")
    shown = {m for p in PAGES for m in re.findall(r"\]\(img/([^)]+)\)", _body(p))}
    assert shown, "the guide shows no pictures"
    for name in shown:
        assert (GUIDE / "img" / name).is_file(), name
        assert f'"{name}"' in script, f"img/{name} is not made by scripts/make_guide_images.py"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_no_editor_is_required(page):
    """The package works without any particular editor: the guide's steps are
    the AI or `fa` commands, and VS Code appears only as an optional tip."""
    body = _body(page)
    assert "🖱" not in body, f"{page.name}: an editor-button step (use 💬 / ⌨, and 💡 for editor tips)"
    optional = ("💡", "VS Code를 쓴다면", "VS Code를 쓸 때", "필요하지 않습니다", "그리고 VS Code",
                "if you use VS Code", "(With VS Code)", "is needed", "and the VS Code")
    for para in re.split(r"\n\s*\n", body):
        if ("VS Code" in para or "Ctrl+Shift" in para) and not any(o in para for o in optional):
            pytest.fail(f"{page.name}: VS Code presented as required: {para.strip()[:120]}")


def test_entry_paths_are_named_the_same_everywhere():
    """Case A / B / C mean the same thing in the guide, the rules, the ingest
    skill and the user guide; the old 'track' names are gone."""
    sources = {"guide": GUIDE / "05-entry-paths.md", "rules": ROOT / "AGENTS.md",
               "skill": ROOT / ".agents" / "skills" / "ingest_plot" / "SKILL.md",
               "user guide": ROOT / "docs" / "USER_GUIDE.md"}
    for name, path in sources.items():
        if name == "user guide" and not path.is_file():
            continue                                  # only in repositories that keep the older user guide
        text = path.read_text(encoding="utf-8")
        assert all(f"Case {c}" in text or f"Case A·B·C" in text for c in "ABC"), f"{name}: Case A/B/C missing"
        assert not re.search(r"트랙 [A-D]", text), f"{name}: old 'track' naming"
    guide = sources["guide"].read_text(encoding="utf-8")
    guide_ko = (GUIDE / "05-entry-paths.ko.md").read_text(encoding="utf-8")
    rules = sources["rules"].read_text(encoding="utf-8")
    # A = own code + data, B = compliant bundle, C = data + visual intent -- in the rules and both languages
    assert re.search(r"Case A \(Unstructured custom script", rules)
    assert re.search(r"Case B \(Pre-packaged compliant bundle", rules)
    assert re.search(r"Case C \(Data \+ visual intent", rules)
    assert "Case A: port code" in guide and "Case A: 코드 이식" in guide_ko
    assert "Case B: bring in a bundle" in guide and "Case B: 번들 반입" in guide_ko
    assert "Case C: draw from intent" in guide and "Case C: 의도로 합성" in guide_ko
