"""MkDocs hook (mkdocs.yml `hooks:`).

- Links from a page to repository files outside docs/ -- AGENTS.md, examples/,
  configs/, fig_atlas_omics/... -- point to the file on GitHub, so they work on
  the site as they do on GitHub. Links inside docs/ are left to MkDocs (its
  strict build checks them).
- Search per language: the i18n plugin writes one search index for both
  languages, so a search on the English site also returns Korean pages. After
  the build, the index is split -- English at search/, Korean at ko/search/ --
  and the Korean pages search from ko/ (docs/decisions/0006).
"""
from __future__ import annotations

import json
import os
import posixpath
import re
from pathlib import Path

try:
    from mkdocs.plugins import event_priority
except ImportError:                       # imported by the tests where MkDocs is not installed
    def event_priority(_priority):
        return lambda f: f

ALT_LANGS = ("ko",)                 # the site's other languages, served under /<lang>/
BASE = re.compile(r'("base":\s*")([^"]*)(")')

LINK = re.compile(r"(\]\()([^)\s#]+)(#[^)\s]*)?(\))")


def rewrite(markdown: str, page_dir: str, repo_url: str, branch: str = "main", on_site=lambda path: True) -> str:
    """``page_dir``: the page's folder relative to the repository root (e.g.
    docs/howto). ``on_site(path)`` says whether a docs/ path is a page of the
    site; one that is not (a research record kept off the site) goes to GitHub too."""
    def fix(m):
        target = m.group(2)
        if re.match(r"^[a-z]+:", target) or target.startswith("/"):
            return m.group(0)                                   # URL or site-absolute
        resolved = posixpath.normpath(posixpath.join(page_dir, target))
        if resolved.startswith(".."):
            return m.group(0)
        if (resolved == "docs" or resolved.startswith("docs/")) and on_site(resolved[len("docs/"):]):
            return m.group(0)
        kind = "tree" if target.endswith("/") else "blob"
        return f"{m.group(1)}{repo_url.rstrip('/')}/{kind}/{branch}/{resolved}{m.group(3) or ''}{m.group(4)}"
    return LINK.sub(fix, markdown)


def on_page_markdown(markdown, page, config, files):
    page_dir = posixpath.dirname(posixpath.join("docs", page.file.src_uri))

    def on_site(path: str) -> bool:
        if not path or path.endswith("/"):
            return True                                         # a folder: MkDocs decides
        f = files.get_file_from_path(path)
        return f is not None and not f.inclusion.is_excluded()
    return rewrite(markdown, page_dir, config.get("repo_url") or "", on_site=on_site)


def split_index(index: dict, lang: str) -> tuple[dict, dict]:
    """(the index without ``lang``'s pages, ``lang``'s own index): its entries
    with their ``<lang>/`` prefix removed, as its pages search from ``<lang>/``,
    plus the default language's entries of pages it has no version of (the
    generated reference pages): the plugin shows them under ``<lang>/`` too."""
    prefix = f"{lang}/"
    own = [dict(e, location=e["location"][len(prefix):]) for e in index["docs"] if e["location"].startswith(prefix)]
    rest = [e for e in index["docs"] if not e["location"].startswith(prefix)]
    # A page the language has no version of appears in its build only as an
    # empty title entry (the plugin drops the rest as duplicates): take the
    # default language's full entries for it.
    translated = {e["location"].split("#")[0] for e in own if e.get("text", "").strip()}
    own = [e for e in own if e["location"].split("#")[0] in translated]
    own += [e for e in rest if e["location"].split("#")[0] not in translated]
    return dict(index, docs=rest), dict(index, docs=own)


def rebase(html: str, page_dir: Path, site_dir: Path, lang_dir: Path) -> str:
    """Point a page's Material config ``base`` (the site root, where search
    reads its index) at its language's root instead. A page already pointing
    there is left as it is, so running twice changes nothing."""
    to_site = Path(os.path.relpath(site_dir, page_dir)).as_posix()
    to_lang = Path(os.path.relpath(lang_dir, page_dir)).as_posix()

    def fix(m):
        return f"{m.group(1)}{to_lang}{m.group(3)}" if m.group(2) == to_site else m.group(0)
    return BASE.sub(fix, html, count=1)


@event_priority(-200)        # after the i18n plugin (-100) has written the combined index
def on_post_build(config):
    site = Path(config["site_dir"])
    path = site / "search" / "search_index.json"
    if not path.is_file():
        return
    index = json.loads(path.read_text(encoding="utf-8"))
    for lang in ALT_LANGS:
        lang_dir = site / lang
        if not lang_dir.is_dir() or not any(e["location"].startswith(f"{lang}/") for e in index["docs"]):
            continue
        index, own = split_index(index, lang)
        (lang_dir / "search").mkdir(exist_ok=True)
        (lang_dir / "search" / "search_index.json").write_text(json.dumps(own, ensure_ascii=False), encoding="utf-8")
        for page in lang_dir.rglob("*.html"):
            html = page.read_text(encoding="utf-8")
            new = rebase(html, page.parent, site, lang_dir)
            if new != html:
                page.write_text(new, encoding="utf-8")
    path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
