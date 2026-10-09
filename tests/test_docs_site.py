"""The documentation site (mkdocs.yml, roadmap 8.2): links resolve, and the
site builds in strict mode where MkDocs is installed (`pip install -e .[docs]`)."""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OFF_SITE = ("storylines", "storyline", "data_contracts", "baselines", "usability", "paper")     # mkdocs.yml exclude_docs
LINK = re.compile(r"\]\(([^)\s]+)\)")


def _hooks():
    spec = importlib.util.spec_from_file_location("mkdocs_hooks", ROOT / "scripts" / "mkdocs_hooks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pages() -> list[Path]:
    site = [p for p in (ROOT / "docs").rglob("*.md") if p.relative_to(ROOT / "docs").parts[0] not in OFF_SITE]
    return sorted(site) + [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "examples" / "README.md"]


@pytest.mark.parametrize("page", _pages(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_relative_links_resolve(page):
    text = re.sub(r"```.*?```", "", page.read_text(encoding="utf-8"), flags=re.S)    # not code samples
    text = re.sub(r"`[^`\n]*`", "", text)                                          # nor inline code
    broken = []
    for target in LINK.findall(text):
        target = target.split("#", 1)[0]
        if not target or re.match(r"^[a-z]+:", target) or target.startswith("/"):
            continue
        if not (page.parent / target).exists():
            broken.append(target)
    assert not broken, f"{page.relative_to(ROOT)}: links to missing files {broken}"


def test_hook_sends_repository_files_to_github():
    rewrite = _hooks().rewrite
    url = "https://github.com/o/r"
    md = "[a](../AGENTS.md) [b](contracts/README.md) [c](../examples/) [d](https://x.org) [e](#top) [f](storylines/p.md)"
    out = rewrite(md, "docs", url, on_site=lambda p: not p.startswith("storylines/"))
    assert "[a](https://github.com/o/r/blob/master/AGENTS.md)" in out
    assert "[b](contracts/README.md)" in out                            # a page of the site
    assert "[c](https://github.com/o/r/tree/master/examples)" in out
    assert "[d](https://x.org)" in out and "[e](#top)" in out
    assert "[f](https://github.com/o/r/blob/master/docs/storylines/p.md)" in out   # kept off the site


@pytest.mark.skipif(shutil.which("mkdocs") is None and importlib.util.find_spec("mkdocs") is None,
                    reason="MkDocs not installed (pip install -e .[docs])")
def test_site_builds_strict(tmp_path):
    res = subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict", "-q", "-d", str(tmp_path / "site")],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, res.stderr[-3000:]
    assert (tmp_path / "site" / "tutorials" / "first_figure" / "index.html").is_file()
