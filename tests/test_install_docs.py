"""The README and the install guide name one release, the package's own: at 0.4.0
the README still told people to install v0.3.1 while the guide said v0.4.0."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["README.md", "docs/howto/install.md", "docs/howto/install.ko.md"]
TAG = re.compile(r"fig-atlas(?:@|/archive/refs/tags/)v(\d+\.\d+\.\d+)")
SHOWN = re.compile(r"`fa (\d+\.\d+\.\d+) \(")


def test_readme_and_install_guide_name_the_package_release():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M).group(1)
    found = {}
    for page in PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        for v in TAG.findall(text) + SHOWN.findall(text):
            found.setdefault(v, set()).add(page)
    assert found, "no release named"
    if re.fullmatch(r"\d+\.\d+\.\d+", version):          # a release; a development version may lag
        assert set(found) == {version}, f"pyproject says {version}; pages name {found}"
    else:
        assert len(found) == 1, f"pages name more than one release: {found}"
