"""Check the layout-catalog plan's status file against the installed fig-atlas.

    python scripts/check_plan_layout_catalog.py          # from the fig-atlas root, fig-atlas environment

Reads plans/PLAN_LAYOUT_CATALOG.status.yaml (the single source of task state;
plans/PLAN_LAYOUT_CATALOG.md section 8) and reports:

- the cards by status, and the cards that can be started now (todo, every
  dependency done, the gates of their phase passed);
- a card id that the plan's card table does not list, or a plan card missing
  from the status file (the two must agree);
- a done card whose asset is not in the package (a layout module, an example,
  the guide chapter, ...);
- a card claimed or further along before its dependencies are done, or before
  the gates of its phase have passed;
- dependency cycles.

Exit code 1 when anything disagrees.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "plans" / "PLAN_LAYOUT_CATALOG.md"
STATUS = ROOT / "plans" / "PLAN_LAYOUT_CATALOG.status.yaml"
ORDER = ["todo", "claimed", "in_review", "done", "blocked", "dropped"]
DONE_OR_LATER = {"in_review", "done"}
ID = re.compile(r"^L-\d{2}[a-z]?$")
CARD_ROW = re.compile(r"^\|\s*(L-\d{2}[a-z]?)\s*\|", re.M)

# What a done card must leave in the package. The value names the expected
# files/directories; a callable check is added for cards whose shape is easier
# to test in code.
ASSETS = {
    "L-01": [STATUS, ROOT / "scripts" / "check_plan_layout_catalog.py"],
    "L-02": [ROOT / "fig_atlas" / "layouts" / "_core.py", ROOT / "fig_atlas" / "layouts" / "__init__.py"],
    "L-03": [ROOT / "fig_atlas" / "layouts" / "wide_bottom.py", ROOT / "tests" / "layouts" / "test_wide_bottom.py"],
    "L-04": [ROOT / "fig_atlas" / "layouts" / "stack.py", ROOT / "tests" / "layouts" / "test_stack.py"],
    "L-05": [ROOT / "fig_atlas" / "layouts" / "grid.py"],
    "L-06": [ROOT / "fig_atlas" / "layouts" / "matrix.py", ROOT / "tests" / "layouts" / "test_matrix.py"],
    "L-07": [ROOT / "fig_atlas" / "layouts" / "row.py", ROOT / "tests" / "layouts" / "test_row.py"],
    "L-08": [ROOT / "scripts" / "make_layout_gallery.py", ROOT / "tests" / "test_layouts_gallery.py"],
    "L-09a": [ROOT / "docs" / "guide" / "08-results.md"],
    "L-09b": [ROOT / "docs" / "guide" / "07-layouts.md", ROOT / "docs" / "guide" / "07-layouts.ko.md"],
    "L-10": [ROOT / "scripts" / "layout_coverage.py"],
}


def _plan_ids() -> set[str]:
    return set(CARD_ROW.findall(PLAN.read_text(encoding="utf-8")))


def _cycles(cards: dict[str, dict]) -> list[list[str]]:
    found, state = [], {}

    def visit(cid: str, stack: list[str]) -> None:
        if state.get(cid) == "done":
            return
        if state.get(cid) == "open":
            found.append(stack[stack.index(cid):] + [cid])
            return
        state[cid] = "open"
        for dep in cards[cid].get("depends_on") or []:
            if dep in cards:
                visit(dep, stack + [cid])
        state[cid] = "done"

    for cid in cards:
        visit(cid, [])
    return found


def main() -> int:
    problems: list[str] = []
    if not PLAN.is_file() or not STATUS.is_file():
        print("missing plans/PLAN_LAYOUT_CATALOG.md or .status.yaml")
        return 1
    plan = yaml.safe_load(STATUS.read_text(encoding="utf-8")) or {}
    cards = plan.get("cards") or []
    gates = plan.get("gates") or {}
    phase_gates = plan.get("phase_gates") or {}
    by_id: dict[str, dict] = {}

    for key in ("plan_version", "package_version", "baseline", "gates", "phase_gates", "cards"):
        if key not in plan:
            problems.append(f"status: missing top-level key {key!r}")

    for c in cards:
        cid = c.get("id", "")
        if not ID.match(cid):
            problems.append(f"card {cid!r}: id must look like L-01 or L-09a")
            continue
        if cid in by_id:
            problems.append(f"card {cid}: duplicate id")
        by_id[cid] = c
        for key in ("title", "kind", "phase", "priority", "status", "depends_on", "owner",
                    "branch", "commits", "review", "notes"):
            if key not in c:
                problems.append(f"card {cid}: missing field {key!r}")
        if c.get("status") not in ORDER:
            problems.append(f"card {cid}: status {c.get('status')!r} not in {ORDER}")
        if c.get("priority") not in ("P1", "P2", "P3"):
            problems.append(f"card {cid}: priority {c.get('priority')!r} not in P1..P3")
        if c.get("phase") not in phase_gates:
            problems.append(f"card {cid}: phase {c.get('phase')!r} has no phase_gates entry")
        for dep in c.get("depends_on") or []:
            if dep == cid:
                problems.append(f"card {cid}: depends on itself")
            elif dep not in by_id and dep not in {x.get("id") for x in cards}:
                problems.append(f"card {cid}: depends_on {dep!r} is not a card")

    for cycle in _cycles(by_id):
        problems.append("dependency cycle: " + " -> ".join(cycle))

    for cid, c in by_id.items():
        status = c.get("status")
        if status in ("todo", "claimed", "in_review", "done"):
            for gate in phase_gates.get(c.get("phase"), []):
                state = str(gates.get(gate, "pending"))
                if not state.startswith("passed"):
                    problems.append(f"card {cid}: phase {c.get('phase')} needs gate {gate} ({state})")
        if status in DONE_OR_LATER:
            for dep in c.get("depends_on") or []:
                if by_id.get(dep, {}).get("status") != "done":
                    problems.append(f"card {cid}: is {status} but dependency {dep} is "
                                    f"{by_id.get(dep, {}).get('status')!r}")
        if status == "done":
            for path in ASSETS.get(cid, []):
                if not Path(path).exists():
                    problems.append(f"card {cid}: done but missing {Path(path).relative_to(ROOT).as_posix()}")

    plan_ids, status_ids = _plan_ids(), set(by_id)
    if plan_ids != status_ids:
        problems.append(f"plan and status disagree: only in plan {sorted(plan_ids - status_ids)}, "
                        f"only in status {sorted(status_ids - plan_ids)}")

    counts = Counter(c.get("status") for c in cards)
    print(f"{len(cards)} cards: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
    ready = [cid for cid, c in by_id.items()
             if c.get("status") == "todo"
             and all(by_id.get(d, {}).get("status") == "done" for d in c.get("depends_on") or [])
             and all(str(gates.get(g, "pending")).startswith("passed")
                     for g in phase_gates.get(c.get("phase"), []))]
    if ready:
        print("ready to start: " + ", ".join(sorted(ready)))
    for cid in sorted(by_id):
        c = by_id[cid]
        print(f"  {cid:6} {c.get('status', '?'):9} {c.get('title', '')}")
    if problems:
        print("\nproblems:")
        for p in problems:
            print("  - " + p)
        return 1
    print("\nok: the status file, the plan and the package agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
