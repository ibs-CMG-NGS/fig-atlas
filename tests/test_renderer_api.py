"""The renderer contract (fig_atlas/renderer_api.py, docs/decisions/0009): the
names a project repository's own renderers may import. Removing or renaming one
fails here first; that change needs a deprecation release and a changelog entry."""
from __future__ import annotations

import importlib
from pathlib import Path

from fig_atlas.renderer_api import API, outside

ROOT = Path(__file__).resolve().parents[1]


def test_every_contract_name_imports():
    for module, names in API.items():
        mod = importlib.import_module(module)
        for name in names:
            assert hasattr(mod, name), f"{module}.{name} is in the renderer contract but gone"


def test_public_renderers_are_in_the_contract():
    import fig_atlas.renderers as core
    public = [n for n in core.__all__ if n.startswith("render_")]
    assert public
    assert outside("from fig_atlas.renderers import " + ", ".join(public)) == []


def test_the_new_renderer_templates_import_only_the_contract():
    for name in ("renderer.py.tmpl", "renderer_test.py.tmpl", "renderer_from_test.py.tmpl"):
        text = (ROOT / "fig_atlas" / "templates" / name).read_text(encoding="utf-8")
        assert outside(text) == [], name


def test_outside_names_what_is_not_promised():
    text = ("from fig_atlas.schema import (Param, Schema,\n    uses_schema)\n"
            "from fig_atlas import stats\n"
            "from fig_atlas.renderers.violin import render_violin\n"
            "from fig_atlas.renderers._basic import TEXT, finish  # helpers\n"
            "from fig_atlas.renderers.line_band import summarise as s\n")
    assert outside(text) == ["fig_atlas.renderers._basic.TEXT", "fig_atlas.renderers._basic.finish",
                             "fig_atlas.renderers.line_band.summarise"]
