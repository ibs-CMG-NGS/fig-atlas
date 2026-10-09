"""MkDocs hook (mkdocs.yml `hooks:`): links from a page to repository files
outside docs/ -- AGENTS.md, examples/, configs/, fig_atlas_omics/... -- point
to the file on GitHub, so they work on the site as they do on GitHub.

Links inside docs/ are left to MkDocs (its strict build checks them).
"""
from __future__ import annotations

import posixpath
import re

LINK = re.compile(r"(\]\()([^)\s#]+)(#[^)\s]*)?(\))")


def rewrite(markdown: str, page_dir: str, repo_url: str, branch: str = "master", on_site=lambda path: True) -> str:
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
