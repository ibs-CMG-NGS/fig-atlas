"""Renderers draw results; they do not compute them (docs/decisions/0007).

A renderer may compute the geometry of its own shape: a Kaplan-Meier step curve,
the mean and confidence band of a line, the order a dendrogram puts rows in, the
density a violin draws. It may not run a test, a fit or any other analysis whose
value it prints -- those arrive as columns (``r_col``, ``pvalue_col``) or as a
statistics table the analysis script registers with ``fig_atlas.stats.record``.

``ALLOWED`` is the complete set of exceptions. Each entry states why the
computation is the shape itself, or which card removes it. A new entry is a
review decision, not a workaround: if the value is printed, it belongs in the
analysis script.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {"core": ROOT / "fig_atlas" / "renderers", "omics": ROOT / "fig_atlas_omics" / "renderers"}
ANALYSIS_ROOTS = ("scipy", "sklearn", "statsmodels")

# (package/module.py, imported module) -> why it is allowed
ALLOWED = {
    ("core/line_band.py", "scipy.stats"):
        "the t quantile of the drawn mean +/- CI band (display arithmetic, not a test)",
    ("core/heatmap.py", "scipy.cluster.hierarchy"):
        "row/column order of the dendrogram (the shape)",
    ("core/heatmap.py", "scipy.spatial.distance"):
        "the distance matrix that order comes from (the shape)",
    ("core/multi_group_heatmap.py", "scipy.cluster.hierarchy"):
        "row order of the dendrogram (the shape)",
    ("core/multi_group_heatmap.py", "scipy.spatial.distance"):
        "the distance matrix that order comes from (the shape)",
    ("omics/cross_condition_heatmap.py", "scipy.cluster.hierarchy"):
        "row order and the group cut of the dendrogram (the shape)",
    ("omics/cross_condition_heatmap.py", "scipy.spatial.distance"):
        "the distance matrix that order comes from (the shape)",
    ("core/group_scatter.py", "scipy.stats"):
        "TRANSITIONAL: Pearson r/P when r_col/p_col are absent; removed by card E-04",
    ("core/dose_response.py", "scipy.optimize"):
        "TRANSITIONAL: the in-renderer 4PL fit; removed by card E-04",
}


def _modules(path: Path) -> set[str]:
    """The modules a file imports, as dotted names (``from scipy import stats`` -> ``scipy.stats``)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if "." in node.module:
                out.add(node.module)
            else:                       # from scipy import stats -> the module scipy.stats
                out.update(f"{node.module}.{alias.name}" for alias in node.names)
    return out


def _covered(module: str, allowed: set[str]) -> bool:
    return any(module == a or module.startswith(a + ".") for a in allowed)


def _renderer_files() -> list[tuple[str, Path]]:
    files = []
    for pkg, folder in PACKAGES.items():
        for path in sorted(folder.glob("*.py")):
            if path.name != "__init__.py":
                files.append((f"{pkg}/{path.name}", path))
    return files


def test_no_renderer_computes_a_printed_result():
    offenders = []
    for key, path in _renderer_files():
        allowed = {m for (k, m) in ALLOWED if k == key}
        for module in _modules(path):
            if module.split(".")[0] in ANALYSIS_ROOTS and not _covered(module, allowed):
                offenders.append(f"{key}: imports {module}")
    assert not offenders, (
        "a renderer computes an analysis result (docs/decisions/0007). Draw the value from a column "
        "the analysis script writes, or add an entry to ALLOWED with a reason or a removal card:\n  "
        + "\n  ".join(offenders))


def test_allowlist_has_no_stale_entry():
    """When a card removes an exception, its ALLOWED entry goes with it (and this test says so)."""
    stale = []
    for (key, module), why in ALLOWED.items():
        path = PACKAGES[key.split("/")[0]] / key.split("/", 1)[1]
        if not path.exists() or module not in _modules(path):
            stale.append(f"{key}: {module} ({why})")
    assert not stale, "ALLOWED entries no longer match the code:\n  " + "\n  ".join(stale)
