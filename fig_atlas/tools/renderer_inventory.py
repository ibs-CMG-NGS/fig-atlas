"""Which project uses which renderer -- generated, so it can't go stale.

Scans every analysis script and repo script for ``from fig_atlas.renderers
import ...`` and ``from fig_atlas_omics.renderers import ...`` (the omics pack) and counts the call sites of each imported renderer (AST, no
code is run). Projects are matched to their analysis script through
``project.analysis_script`` in their config, and flagged when the storyline
compendium includes them. The result ranks renderers for regression testing
(roadmap Phase 0): compendium renderers first.

Usage:
    python scripts/renderer_inventory.py              # writes docs/reference/renderer_inventory.md
    python scripts/renderer_inventory.py --check      # exit 1 if that file is out of date
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from fig_atlas.tools import project_root  # noqa: E402  (the project repository, not this package)

ROOT = project_root()
OUT = ROOT / "docs" / "reference" / "renderer_inventory.md"
STORYLINES = sorted((ROOT / "docs" / "storylines").glob("figure_plan_*.md"))


# Renderer packages: import path -> source folder (core first, then the omics pack).
PACKAGES = {"fig_atlas.renderers": "fig_atlas/renderers", "fig_atlas_omics.renderers": "fig_atlas_omics/renderers"}


def renderer_modules() -> dict[str, str]:
    """Exported renderer function -> module file, from each package's __init__.py."""
    out = {}
    for folder in PACKAGES.values():
        tree = ast.parse((ROOT / folder / "__init__.py").read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                for a in node.names:
                    out[a.asname or a.name] = f"{folder}/{node.module}"
    return out


def renderer_calls(path: Path) -> dict[str, int]:
    """Renderer name -> number of call sites in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in PACKAGES:
            for a in node.names:
                imported[a.asname or a.name] = a.name
    calls: dict[str, int] = defaultdict(int)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in imported:
            calls[imported[node.func.id]] += 1
    for local, name in imported.items():   # imported but only passed around, never called directly
        calls.setdefault(name, 0)
    return dict(calls)


def projects_by_script() -> dict[str, tuple[str, str]]:
    """analysis script path -> (project name, namespace like <domain>/paper)."""
    out = {}
    for cfg in sorted((ROOT / "configs").rglob("config_*.yaml")):
        try:
            raw = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        script = (raw.get("project") or {}).get("analysis_script")
        if script:
            ns = "/".join(cfg.relative_to(ROOT / "configs").parts[:-1]) or "(sandbox)"
            out[script.replace("\\", "/")] = (cfg.stem[len("config_"):], ns)
    return out


def compendium_projects() -> set[str]:
    spec = importlib.util.spec_from_file_location("compile_storyline_pdf", Path(__file__).with_name("compile_storyline_pdf.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {f["project"] for md in STORYLINES for f in mod.parse_storyline_md(md)["figures"]}


def build() -> str:
    modules = renderer_modules()
    owners = projects_by_script()
    compendium = compendium_projects()

    # consumer label -> {renderer: calls}
    usage: dict[str, dict[str, int]] = {}
    labels: dict[str, str] = {}
    for path in sorted([*(ROOT / "analysis").rglob("*.py"), *(ROOT / "scripts").glob("*.py")]):
        if "__pycache__" in path.parts:
            continue
        calls = renderer_calls(path)
        if not calls:
            continue
        rel = path.relative_to(ROOT).as_posix()
        proj, ns = owners.get(rel, (None, None))
        if proj:
            label = proj
            kind = "compendium" if proj in compendium else ("archive" if "archive" in ns else ns)
        elif "archive" in path.relative_to(ROOT).parts:
            # Retired scripts: their archived configs may still point at the
            # pre-move path, so match on location instead.
            label, kind = path.stem.removesuffix("_analysis") + " (archived)", "archive"
        else:
            label, kind = rel, "script" if rel.startswith("scripts/") else "unregistered"
        usage[label] = calls
        labels[label] = kind

    by_renderer: dict[str, dict[str, int]] = defaultdict(dict)
    for consumer, calls in usage.items():
        for name, n in calls.items():
            by_renderer[name][consumer] = n

    def tier(name: str) -> str:
        kinds = {labels[c] for c in by_renderer.get(name, {})}
        if "compendium" in kinds:
            return "1 compendium"
        if kinds - {"archive"}:
            return "2 active"
        return "3 archive only" if kinds else "4 unused"

    rows = sorted(modules, key=lambda n: (tier(n), -len(by_renderer.get(n, {})), n))
    lines = [
        "# Renderer inventory",
        "",
        "<!-- Generated by scripts/renderer_inventory.py -- do not edit by hand. -->",
        "",
        "Which projects call each exported renderer (`fig_atlas.renderers`, and the omics pack's",
        "`fig_atlas_omics.renderers`), found by",
        "static analysis of `analysis/**` and `scripts/*.py`. **Tier** sets the order",
        "for renderer regression tests (roadmap Phase 0): 1 = used by a figure in the",
        "storyline compendium, 2 = used by another live project, 3 = only by archived",
        "projects, 4 = not called anywhere.",
        "",
        f"Compendium projects: {', '.join(f'`{p}`' for p in sorted(compendium)) or 'none'}.",
        "",
        "| Tier | Renderer | Module | Projects | Compendium users | Other users |",
        "|---|---|---|---:|---|---|",
    ]
    for name in rows:
        users = by_renderer.get(name, {})
        comp = sorted(c for c in users if labels[c] == "compendium")
        other = sorted(c for c in users if labels[c] != "compendium")
        fmt = lambda cs: ", ".join(f"`{c}`" for c in cs) or "—"
        lines.append(f"| {tier(name)[0]} | `{name}` | `{modules[name]}.py` | {len(users)} | {fmt(comp)} | {fmt(other)} |")

    counts = defaultdict(int)
    for name in modules:
        counts[tier(name)] += 1
    lines += ["", "Summary: " + ", ".join(f"tier {t} — {n}" for t, n in sorted(counts.items())) + "."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if the committed inventory is out of date")
    args = ap.parse_args()
    text = build()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(ROOT)} is out of date; run scripts/renderer_inventory.py")
            return 1
        print(f"{OUT.relative_to(ROOT)} is up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
