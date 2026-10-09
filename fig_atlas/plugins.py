"""Plugin points for domain packs (roadmap Phase 6a, step 6a.2).

A domain pack (e.g. the omics pack, ``fig_atlas_omics``) extends the core
through Python entry points; the core never imports a pack by name. Groups:

    fig_atlas.renderers   a renderer package (module path), e.g. "fig_atlas_omics.renderers"
    fig_atlas.contracts   a list of bundle contracts (fig_atlas.contracts.Contract)
    fig_atlas.ingest      a dict {plot_type: "package.module:render_function"}
    fig_atlas.recipes     a list of recipes (a generic renderer + column roles + defaults)
    fig_atlas.commands    a function register(subparsers) -> {command name: handler(args, root)}

Declared in the pack's pyproject.toml, e.g.::

    [project.entry-points."fig_atlas.contracts"]
    omics = "fig_atlas_omics.contracts:CONTRACTS"

Entry points are read from the installed package metadata: after adding or
changing one, re-run ``pip install -e .``.
"""
from __future__ import annotations

import importlib
import warnings
from dataclasses import dataclass
from typing import Any

GROUPS = {
    "renderers": "fig_atlas.renderers",
    "contracts": "fig_atlas.contracts",
    "ingest": "fig_atlas.ingest",
    "recipes": "fig_atlas.recipes",
    "commands": "fig_atlas.commands",
}


@dataclass(frozen=True)
class Plugin:
    group: str      # short group name ("contracts", ...)
    name: str       # entry-point name ("omics")
    value: str      # "module" or "module:attribute"
    dist: str       # distribution that declares it


def entry_points(group: str) -> list[Plugin]:
    """Declared plugins of a group (short name or full entry-point group), sorted by name."""
    from importlib.metadata import entry_points as _eps
    full = GROUPS.get(group, group)
    short = next((k for k, v in GROUPS.items() if v == full), group)
    out = []
    for ep in _eps(group=full):
        dist = getattr(getattr(ep, "dist", None), "name", "") or ""
        out.append(Plugin(short, ep.name, ep.value, dist))
    return sorted(out, key=lambda p: (p.name, p.value))


def load(plugin: Plugin) -> Any:
    """Import a plugin's object: a module, or ``module:attribute``."""
    module, _, attr = plugin.value.partition(":")
    obj = importlib.import_module(module.strip())
    for part in filter(None, attr.strip().split(".")):
        obj = getattr(obj, part)
    return obj


def load_all(group: str) -> list[tuple[Plugin, Any]]:
    """Every plugin of a group, loaded; one that fails to import is skipped
    with a warning naming it, so a broken pack cannot stop the core."""
    out = []
    for p in entry_points(group):
        try:
            out.append((p, load(p)))
        except Exception as exc:                       # noqa: BLE001 -- report and keep going
            warnings.warn(f"fig-atlas plugin {p.group}:{p.name} ({p.value}) failed to load: {exc}",
                          RuntimeWarning, stacklevel=2)
    return out
