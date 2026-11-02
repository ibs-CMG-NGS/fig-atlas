"""Every public layout ships with its asset set (plans/PLAN_LAYOUT_CATALOG.md section 4):
a docstring with the shape drawn in ASCII, an example in examples/layouts/<name>/ that
calls it and builds clean at print size, a picture and a section in
docs/reference/layouts.md."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import make_layout_gallery as gallery  # noqa: E402

from fig_atlas.preflight import preflight  # noqa: E402

NAMES = gallery.layout_names()
MAX_SCRIPT_LINES = 25                       # plan section 4: an example is short enough to read at a glance


def test_the_catalog_has_the_five_layouts_of_the_plan():
    assert sorted(NAMES) == ["grid", "matrix", "row", "stack", "wide_bottom"]


@pytest.mark.parametrize("name", NAMES)
def test_layout_has_its_assets(name):
    example = gallery.EXAMPLES / name
    script = example / "script.py"
    assert (example / "config.yaml").is_file() and script.is_file()
    assert f"layouts.{name}(" in script.read_text(encoding="utf-8")
    assert gallery.code_lines(script) <= MAX_SCRIPT_LINES
    assert "+---" in "\n".join(gallery._doc_lines(name))          # the shape, drawn
    assert (gallery.PICTURES / f"{name}.png").is_file()
    page = (ROOT / "docs" / "reference" / "layouts.md").read_text(encoding="utf-8")
    assert f"\n## {name}\n" in page and f"gallery/layouts/{name}.png" in page


def test_composition_has_its_example_picture_and_section():
    script = gallery.EXAMPLES / "compose" / "script.py"
    assert script.is_file() and gallery.code_lines(script) <= MAX_SCRIPT_LINES
    assert (gallery.PICTURES / "compose.png").is_file()
    page = (ROOT / "docs" / "reference" / "layouts.md").read_text(encoding="utf-8")
    assert "\n## Composition\n" in page and "gallery/layouts/compose.png" in page


@pytest.mark.parametrize("name", NAMES + gallery.COMPOSED)
def test_example_builds_clean(name):
    with plt.rc_context():
        fig = gallery.load_example(name).build()
        bad = [f"{f.check}: {f.message}" for f in preflight(fig, saved_bbox_in=None)
               if f.severity in ("error", "warn")]
        tags = sorted(t.get_text() for t in fig.texts if t.get_gid() == "panel-tag")
        plt.close(fig)
    assert not bad, bad
    assert tags and tags == sorted(tags) and tags[0] == "a"
