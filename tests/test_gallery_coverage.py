"""Every registered renderer has a picture in the gallery (docs/reference/gallery.md):
a snapshot case (tests/renderers/cases.py) or an example bundle (examples/gallery/)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fig_atlas import renderer_registry

ROOT = Path(__file__).resolve().parents[1]


def _cases() -> set[str]:
    spec = importlib.util.spec_from_file_location("gallery_cases", ROOT / "tests" / "renderers" / "cases.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return set(mod.CASES)


def test_every_renderer_has_a_gallery_picture():
    pictured = _cases() | {p.name for p in (ROOT / "examples" / "gallery").iterdir() if p.is_dir()}
    missing = sorted(r["name"] for r in renderer_registry.available() if r["name"] not in pictured)
    assert not missing, (f"renderers with no gallery picture: {missing} -- add a case to tests/renderers/cases.py "
                         "(or an example bundle to examples/gallery/), then run `fa reference`")
