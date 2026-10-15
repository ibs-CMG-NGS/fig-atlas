"""Domain-neutral core boundary (docs/ROADMAP_ECOSYSTEM_STRATEGY.md §11, steps 6a.0-6a.1).

fig_atlas is meant to manage figures for any kind of project, not only NGS.
The omics helpers live in their own domain pack, ``fig_atlas_omics``, which
may use the core; the core (``fig_atlas``, renderers included) must never
import the pack. The only exceptions are the deprecation aliases left at the
old paths (``fig_atlas/<module>.py`` for each moved module), which must stay
bare aliases. No package code may hardcode one study's paths (configs/<domain>/...).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "fig_atlas"
PACK = ROOT / "fig_atlas_omics"

MOVED = {"da_ingest", "go_term_clustering"}   # the study-specific ones went to the study's own repository

# Omics renderers moved to fig_atlas_omics/renderers (6a.1b); the core keeps
# name/path aliases for them in fig_atlas/renderers/__init__.py.
MOVED_RENDERERS = {
    "binary_motif_heatmap", "cis_linkage", "clustered_go_heatmap", "count_summary",
    "cross_condition_dotplot", "cross_condition_heatmap", "go_bar", "go_cluster_dot", "go_dot",
    "go_rrvgo_treemap", "ma_plot", "motif_dotplot", "motif_table", "pathway_evidence_dotplot",
    "pathway_test_matrix", "peak_feature_enrichment", "species_response_scatter",
    "tf_expression_bars", "volcano",
}

# A literal path into one study's namespace (configs/<domain>/<category>/); "lab" and
# placeholders are the documentation's example names.
STUDY_PATH = re.compile(r"configs/(?!lab/|<)[a-z0-9]+/(paper|exploratory|archive)/")


def _imports(path: Path) -> set[str]:
    """Top-level packages a file imports (absolute imports only; relative
    imports stay inside the file's own package)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
    return found


def _code_strings(path: Path) -> list[str]:
    """String constants in a module, excluding docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


def _aliases() -> set[Path]:
    return {PKG / f"{m}.py" for m in MOVED}


def test_moved_modules_live_in_the_pack():
    assert {p.stem for p in PACK.glob("*.py")} >= MOVED
    assert {p.stem for p in (PACK / "renderers").glob("*.py")} >= MOVED_RENDERERS
    assert not MOVED_RENDERERS & {p.stem for p in (PKG / "renderers").glob("*.py")}, "a moved renderer is back in the core"


def test_renderer_aliases_match_the_pack():
    """The core's alias lists name exactly what the pack provides."""
    import fig_atlas.renderers as core
    import fig_atlas_omics.renderers as pack
    assert core._MOVED_MODULES == MOVED_RENDERERS
    # Every name moved out of the core is aliased; names born in the pack
    # (a renderer module the core never had) need no alias.
    born_in_pack = {n for n in pack.__all__
                    if getattr(pack, n).__module__.rsplit(".", 1)[-1] not in MOVED_RENDERERS}
    assert core._MOVED_NAMES == set(pack.__all__) - born_in_pack


def test_core_never_imports_the_pack():
    violations = [
        str(p.relative_to(ROOT)) for p in sorted(PKG.rglob("*.py"))
        if p not in _aliases() and "fig_atlas_omics" in _imports(p)
    ]
    assert not violations, "core modules importing fig_atlas_omics:\n" + "\n".join(violations)


def test_old_paths_are_bare_aliases():
    """Each alias only re-points the old module name at the pack, with a warning."""
    for p in sorted(_aliases()):
        text = p.read_text(encoding="utf-8")
        assert f"from fig_atlas_omics import {p.stem} as _moved" in text, p
        assert "DeprecationWarning" in text and "sys.modules[__name__] = _moved" in text, p
        defs = [n for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        assert not defs, f"{p.name}: an alias must not define code"


def test_repository_code_uses_the_new_paths():
    """Analysis scripts, scripts and specs import from the pack, not through the aliases."""
    old = re.compile(r"\bfig_atlas\.(" + "|".join(sorted(MOVED)) + r")\b|from fig_atlas import [^\n]*prep_da_"
                     r"|\bfig_atlas\.renderers\.(" + "|".join(sorted(MOVED_RENDERERS)) + r")\b")
    hits = [
        f"{p.relative_to(ROOT)}"
        for d in ("analysis", "scripts", "figure_specs")
        for p in sorted((ROOT / d).rglob("*.py"))
        if "__pycache__" not in p.parts and old.search(p.read_text(encoding="utf-8"))
    ]
    assert not hits, "old import paths (use fig_atlas_omics):\n" + "\n".join(hits)


def test_old_renderer_paths_still_work_and_warn():
    import importlib
    import sys

    import pytest

    import fig_atlas_omics.renderers as pack
    with pytest.warns(DeprecationWarning, match="fig_atlas_omics.renderers"):
        from fig_atlas.renderers import render_volcano
    # the pack's exported name (a build may have wrapped it to track config reads)
    assert render_volcano is pack.render_volcano
    sys.modules.pop("fig_atlas.renderers.ma_plot", None)
    with pytest.warns(DeprecationWarning, match="fig_atlas_omics.renderers.ma_plot"):
        old = importlib.import_module("fig_atlas.renderers.ma_plot")
    assert old is importlib.import_module("fig_atlas_omics.renderers.ma_plot")


def test_repository_code_imports_moved_renderers_from_the_pack():
    """No `from fig_atlas.renderers import render_volcano` (a moved name) in repo code."""
    import fig_atlas.renderers as core
    hits = []
    for d in ("analysis", "scripts", "figure_specs", "tests"):
        for p in sorted((ROOT / d).rglob("*.py")):
            if "__pycache__" in p.parts or p == Path(__file__).resolve():   # this file tests the aliases
                continue
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom) and node.module == "fig_atlas.renderers":
                    moved = [a.name for a in node.names if a.name in core._MOVED_NAMES | core._MOVED_MODULES]
                    if moved:
                        hits.append(f"{p.relative_to(ROOT)}:{node.lineno} {moved}")
    assert not hits, "import these from fig_atlas_omics.renderers:\n" + "\n".join(hits)


def test_no_study_specific_paths_in_package_code():
    hits = [
        f"{p.relative_to(ROOT)}: {s!r}"
        for pkg in (PKG, PACK)
        for p in sorted(pkg.rglob("*.py"))
        for s in _code_strings(p)
        if STUDY_PATH.search(s)
    ]
    assert not hits, "hardcoded study paths (use fig_atlas.config.find_config_file):\n" + "\n".join(hits)
