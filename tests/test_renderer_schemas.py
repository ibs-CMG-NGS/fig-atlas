"""Renderer schemas agree with the renderer code (roadmap 2.2).

For every renderer module that declares a ``SCHEMA``: each key its code reads
(``params.get`` / ``text_param``) is in the schema, and each schema default
is exactly the code's own default -- the literal it passes, or CODE_DEFAULT
where the code's default is computed or differs between branches. So adding
or editing a schema can never change a figure; a default changes only by
editing both, on purpose.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from fig_atlas.renderer_registry import modules, packages
from fig_atlas.schema import CODE_DEFAULT, StyleRef
from fig_atlas.schema_tools import by_key, extract_defaults

# Every renderer module of every renderer package: the core and the installed
# packs (fig_atlas.renderer_registry), as {short name: module}.
ALL = modules()
MODULES = sorted(n for n, m in ALL.items() if hasattr(m, "SCHEMA"))


def _file(module: str) -> Path:
    return Path(ALL[module].__file__)


def test_the_omics_pack_is_registered():
    """The pack's renderers are found through the entry point; without it
    (a stale editable install) they would silently drop out of these tests."""
    assert "fig_atlas_omics.renderers" in packages(), "re-run `pip install -e .`"


def _fallback(default):
    return default.fallback if isinstance(default, StyleRef) else default


@pytest.mark.parametrize("module", MODULES)
def test_schema_matches_code(module):
    params = ALL[module].SCHEMA.all()
    reads = by_key(extract_defaults(_file(module)))
    missing = sorted(set(reads) - set(params))
    assert not missing, f"{module}: code reads keys the schema does not declare: {missing}"
    for key, rs in reads.items():
        declared = _fallback(params[key].default)
        literal = {repr(r.default) for r in rs if r.literal}
        computed = any(not r.literal for r in rs) or len(literal) > 1
        if computed:
            assert declared is CODE_DEFAULT, f"{module}.{key}: code default is computed or branch-dependent; use CODE_DEFAULT"
        else:
            (only,) = [r.default for r in rs if r.literal][:1] or [None]
            assert declared is not CODE_DEFAULT and declared == only, \
                f"{module}.{key}: schema default {declared!r} != code default {only!r}"


@pytest.mark.parametrize("module", MODULES)
def test_every_param_is_documented(module):
    for name, p in ALL[module].SCHEMA.all().items():
        assert p.role, f"{module}.{name}: role missing (what it controls)"
        if p.type in (float, int) and not p.unit and name not in ("n_cols",):
            pytest.fail(f"{module}.{name}: numeric parameter without a unit")


def test_every_renderer_that_reads_params_has_a_schema():
    """A new renderer must declare its parameters (roadmap 2.4)."""
    missing = [n for n in ALL if n not in MODULES and extract_defaults(_file(n))]
    assert not missing, f"renderers without a SCHEMA: {missing}"
