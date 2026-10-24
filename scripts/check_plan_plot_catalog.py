"""Check the plot-catalog plan's status file against the installed fig-atlas.

    python scripts/check_plan_plot_catalog.py          # from the cmg-figures root, fig-atlas environment

Reads docs/PLAN_PLOT_CATALOG.status.yaml (the single source of task state;
docs/PLAN_PLOT_CATALOG.md section 9) and reports:
- the cards by status, and the cards that can be started now (todo, every
  dependency done);
- a done plot card whose assets are missing from the package: renderer
  registered, plot_type in the ingest map, a contract, an example bundle,
  a snapshot case, a gallery picture;
- a plot card that is not done although its plot_type is already in the
  package (the status file was not updated);
- a card claimed or further along before its dependencies are done, or
  before the gates of its phase have passed (gates, phase_gates).
Exit code 1 when anything disagrees.
"""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "docs" / "PLAN_PLOT_CATALOG.status.yaml"
ORDER = ["todo", "claimed", "in_review", "done", "blocked", "dropped"]


def package_root() -> Path:
    import fig_atlas
    return Path(fig_atlas.__file__).resolve().parents[1]


def snapshot_cases(pkg: Path) -> set[str]:
    path = pkg / "tests" / "renderers" / "cases.py"
    if not path.is_file():
        return set()
    spec = importlib.util.spec_from_file_location("plan_cases", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return set(mod.CASES)


def main() -> int:
    from fig_atlas import renderer_registry
    from fig_atlas.contracts import all_contracts, ingest_map

    plan = yaml.safe_load(STATUS.read_text(encoding="utf-8"))
    cards = plan["cards"]
    by_id = {c["id"]: c for c in cards}
    pkg = package_root()
    renderers = {r["name"] for r in renderer_registry.available()}
    ingest = set(ingest_map())
    contracted = {t for c in all_contracts() for t in c.plot_types}
    examples = {p.name for p in (pkg / "examples" / "gallery").iterdir() if p.is_dir()}
    cases = snapshot_cases(pkg)
    pictures = {p.stem for p in (pkg / "docs" / "reference" / "gallery").rglob("*.png")}

    problems: list[str] = []
    print(f"plan v{plan['plan_version']} | package {plan['package_version']} | fig-atlas at {pkg}")
    print(f"package now: {len(renderers)} renderers, {len(ingest)} plot types "
          f"(baseline {plan['baseline']['renderers']} / {plan['baseline']['plot_types']})\n")

    counts = Counter(c["status"] for c in cards)
    print("status: " + ", ".join(f"{s} {counts[s]}" for s in ORDER if counts[s]))
    for c in cards:
        if c["status"] not in ORDER:
            problems.append(f"{c['id']}: unknown status {c['status']!r}")
        for d in c.get("depends_on") or []:
            if d not in by_id:
                problems.append(f"{c['id']}: depends on unknown card {d}")
            elif c["status"] in ("claimed", "in_review", "done") and by_id[d]["status"] != "done":
                problems.append(f"{c['id']} is {c['status']} but its dependency {d} is {by_id[d]['status']}")

    gates = plan.get("gates") or {}
    open_gates = {g for g, v in gates.items() if not str(v).startswith("passed")}
    held = lambda c: [g for g in (plan.get("phase_gates") or {}).get(c["phase"], []) if g in open_gates]  # noqa: E731
    print("gates: " + ", ".join(f"{g} {v}" for g, v in gates.items()))
    ready = [c for c in cards if c["status"] == "todo" and not held(c)
             and all(by_id.get(d, {}).get("status") == "done" for d in c.get("depends_on") or [])]
    for c in cards:
        if c["status"] in ("claimed", "in_review", "done") and held(c):
            problems.append(f"{c['id']} is {c['status']} but gate(s) {', '.join(held(c))} have not passed")
    prio = {"P1": 0, "P2": 1, "P3": 2}
    ready.sort(key=lambda c: (c["phase"], prio.get(c["priority"], 9), c["id"]))
    waiting = sum(1 for c in cards if c["status"] == "todo" and held(c))
    print(f"\ncan start now (phase, priority); {waiting} more wait for a gate:")
    for c in ready:
        print(f"  {c['id']:6} phase {c['phase']} {c['priority']}  {c['title']}")
    active = [c for c in cards if c["status"] in ("claimed", "in_review", "blocked")]
    if active:
        print("\nin progress:")
        for c in active:
            print(f"  {c['id']:6} {c['status']:9} {c.get('owner') or '-'}  {c.get('branch') or ''}  {c.get('notes') or ''}")

    for c in cards:
        pt = c.get("plot_type")
        if c["kind"] != "plot" or not pt:
            continue
        have = {"renderer": pt in renderers, "ingest": pt in ingest, "contract": pt in contracted,
                "example bundle": pt in examples, "snapshot case": pt in cases, "gallery picture": pt in pictures}
        if c["status"] == "done":
            missing = [k for k, ok in have.items() if not ok]
            if missing:
                problems.append(f"{c['id']} is done but the package lacks for {pt}: {', '.join(missing)}")
            if not c.get("commits") or not c.get("version"):
                problems.append(f"{c['id']} is done but has no commits/version recorded")
        elif have["ingest"] and have["example bundle"]:
            problems.append(f"{c['id']} ({pt}) is already in the package but the card says {c['status']}")

    print()
    if problems:
        print("DISAGREEMENTS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("status file agrees with the package")
    return 0


if __name__ == "__main__":
    sys.exit(main())
