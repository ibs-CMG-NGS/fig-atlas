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


def _examples() -> set[str]:
    return {p.name for p in (ROOT / "examples" / "gallery").iterdir() if p.is_dir()}


def test_every_bundle_plot_type_has_an_example_bundle():
    """A plot_type `fa ingest bundle` can draw has a bundle to copy in examples/gallery/
    (the gallery's "Start from an example"), and a contract `fa bundle check` applies."""
    from fig_atlas.contracts import all_contracts, ingest_map
    plot_types = set(ingest_map())
    missing = sorted(plot_types - _examples())
    assert not missing, f"plot types with no example bundle: {missing} -- add one to examples/make_gallery.py"
    covered = {t for c in all_contracts() for t in c.plot_types}
    assert not sorted(plot_types - covered), f"plot types with no contract: {sorted(plot_types - covered)}"


def test_every_renderer_has_a_gallery_picture():
    pictured = _cases() | _examples()
    missing = sorted(r["name"] for r in renderer_registry.available() if r["name"] not in pictured)
    assert not missing, (f"renderers with no gallery picture: {missing} -- add a case to tests/renderers/cases.py "
                         "(or an example bundle to examples/gallery/), then run `fa reference`")
