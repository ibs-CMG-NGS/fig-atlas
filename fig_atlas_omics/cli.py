"""`fa omics ...` -- the omics pack's own commands (fig_atlas.commands entry point).

    fa omics list [--json]    what the pack provides: helper modules, renderers,
                              bundle contracts and the plot types it can draw
"""
from __future__ import annotations

import json
from pathlib import Path


def register(subparsers) -> dict:
    """Add the pack's commands to `fa`; returns {command name: handler(args, root)}."""
    p = subparsers.add_parser("omics", help="omics pack: list its modules, renderers, contracts and plot types")
    p.add_argument("action", choices=("list",))
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return {"omics": run}


def contents() -> dict:
    from . import MODULES, renderers
    from .contracts import CONTRACTS, INGEST
    return {
        "modules": list(MODULES),
        "renderers": sorted(renderers.__all__),
        "contracts": [{"name": c.name, "plot_types": list(c.plot_types), "doc": c.doc, "title": c.title}
                      for c in CONTRACTS],
        "plot_types": dict(sorted(INGEST.items())),
    }


def run(args, root: Path) -> int:
    info = contents()
    if args.json:
        print(json.dumps(info, indent=1))
        return 0
    print(f"fig_atlas_omics -- {len(info['modules'])} helper modules, {len(info['renderers'])} renderer functions, "
          f"{len(info['contracts'])} bundle contracts, {len(info['plot_types'])} plot types")
    print("\nhelper modules:  " + ", ".join(info["modules"]))
    print("renderers:       " + ", ".join(info["renderers"]))
    print("\ncontracts:")
    for c in info["contracts"]:
        print(f"  {c['name']:<34} plot_type {', '.join(c['plot_types'])}  ({c['doc']})")
    print("\nplot types -> renderer:")
    for t, r in info["plot_types"].items():
        print(f"  {t:<26} {r}")
    return 0
