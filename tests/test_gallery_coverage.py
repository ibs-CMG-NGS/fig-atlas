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


def _extra_families() -> dict[str, str]:
    """Families of pictures that are not a renderer themselves (cases.EXTRA_FAMILIES)."""
    spec = importlib.util.spec_from_file_location("gallery_cases", ROOT / "tests" / "renderers" / "cases.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(getattr(mod, "EXTRA_FAMILIES", {}))


def _examples() -> set[str]:
    return {p.name for p in (ROOT / "examples" / "gallery").iterdir() if p.is_dir()}


def test_every_renderer_declares_a_known_family():
    """Each renderer module says which gallery family it belongs to (FAMILY, next to
    its SCHEMA; fig_atlas/family.py), so the gallery can group the pictures. A typo
    raises when the family is read."""
    from fig_atlas import renderer_registry
    missing = sorted(r["name"] for r in renderer_registry.available() if not r["family"])
    assert not missing, (f"renderers with no FAMILY: {missing} -- add `FAMILY = \"<family>\"` to the renderer "
                         "module (fig_atlas/family.py lists the families)")


def test_every_gallery_picture_has_a_family():
    """A picture in the gallery page is under a family heading: its renderer's, the
    family of the plot type it draws, or (for a helper picture) cases.EXTRA_FAMILIES."""
    from fig_atlas import family
    extra = _extra_families()
    missing = sorted(n for n in _cases() | _examples() if not (family.family_of_plot(n) or extra.get(n)))
    assert not missing, (f"gallery pictures with no family: {missing} -- a layout variant inherits its "
                         "renderer's family; name anything else in cases.EXTRA_FAMILIES")


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
