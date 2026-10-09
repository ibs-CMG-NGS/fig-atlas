"""Storyline snapshots and revision diffs (roadmap Phase 3S, step S.3).

Compiling a storyline (scripts/compile_storyline_pdf.py) archives the
compendium under ``outputs/storylines/<storyline>/<RNNN>/``. This module adds
what makes two such snapshots comparable:

* ``storyline.yaml`` as compiled (the slot -> project assignment),
* a copy of every placed figure's provenance record (``provenance/``) -- the
  inputs, code, effective config and environment it was built from,
* per figure: whether it was stale when compiled, and the project's preflight
  error count.

``diff`` compares two snapshots: slots added, removed or reassigned, and per
figure (matched by project + figure number, which survive renumbering) the
inputs, code, config keys and package versions that changed.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

SCHEMA = "fig-atlas/storyline-revision@2"
MAX_KEYS = 12          # config keys listed per figure before "... N more"


# ------------------------------------------------------------- figure state --
def provenance_path(fig_pdf: Path) -> Path:
    """Published figure_NN.pdf -> its figure_NN.provenance.json."""
    return fig_pdf.with_name(fig_pdf.stem + ".provenance.json")


def preflight_errors(fig_pdf: Path, source_stem: str | None = None) -> int | None:
    """Preflight errors of a published figure, from its project's
    manifests/preflight.csv; None when preflight never ran. Preflight names
    figures by the stem the analysis script saved (the provenance record's
    source_stem); without it, every error of the project counts."""
    csv_path = fig_pdf.parents[2] / "manifests" / "preflight.csv"
    if not csv_path.is_file():
        return None
    name = Path(source_stem).name if source_stem else None
    with open(csv_path, encoding="utf-8", newline="") as fh:
        return sum(1 for r in csv.DictReader(fh)
                   if r.get("severity") == "error" and (name is None or r.get("figure") == name))


def figure_state(root: Path, fig_pdf: Path, cache=None) -> dict:
    """Provenance record, freshness and preflight errors of a published figure."""
    from fig_atlas.provenance import check_freshness
    rec_path = provenance_path(fig_pdf)
    state = {"provenance": None, "fresh": None, "stale_reasons": []}
    stem = None
    if rec_path.is_file():
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        reasons = check_freshness(root, rec, cache)
        state.update(provenance=rec_path, fresh=not reasons, stale_reasons=reasons)
        stem = (rec.get("figure") or {}).get("source_stem")
    state["preflight_errors"] = preflight_errors(fig_pdf, stem)
    return state


def health_summary(states: list[dict]) -> dict:
    stale = sum(1 for s in states if s["fresh"] is False)
    unrecorded = sum(1 for s in states if s["provenance"] is None)
    errors = sum(s["preflight_errors"] or 0 for s in states)
    no_preflight = sum(1 for s in states if s["preflight_errors"] is None)
    return {"stale": stale, "unrecorded": unrecorded, "preflight_errors": errors, "no_preflight": no_preflight}


def health_line(h: dict) -> str:
    parts = [f"{h['stale']} stale figure(s)" if h["stale"] else "all figures fresh",
             f"{h['preflight_errors']} preflight error(s)"]
    if h["unrecorded"]:
        parts.append(f"{h['unrecorded']} without provenance")
    if h["no_preflight"]:
        parts.append(f"{h['no_preflight']} not preflighted")
    return "Build state: " + ", ".join(parts)


# ----------------------------------------------------------------- snapshot --
def snapshot_extras(root: Path, rev_dir: Path, yaml_path: Path, figures: list[dict]) -> None:
    """Copy storyline.yaml and the figures' provenance records into a
    revision folder. ``figures`` are revision.json figure entries carrying a
    ``state`` (from figure_state); the entry gets relative paths in place."""
    if yaml_path.is_file():
        shutil.copy2(yaml_path, rev_dir / "storyline.yaml")
    prov_dir = rev_dir / "provenance"
    if prov_dir.exists():
        shutil.rmtree(prov_dir)                 # a recompile of the same revision replaces it whole
    for f in figures:
        st = f.pop("state")
        f.update(fresh=st["fresh"], stale_reasons=st["stale_reasons"], preflight_errors=st["preflight_errors"])
        f["provenance"] = None
        if st["provenance"]:
            prov_dir.mkdir(exist_ok=True)
            name = f"{f['project']}__fig{int(f['figure_number'] or 1):02d}.json"
            shutil.copy2(st["provenance"], prov_dir / name)
            f["provenance"] = f"provenance/{name}"


def revision_number(rev: str) -> int:
    m = re.fullmatch(r"R(\d+)", rev)
    return int(m.group(1)) if m else -1


def list_snapshots(root: Path, md: Path) -> list[Path]:
    base = root / "outputs" / "storylines" / md.stem
    dirs = [d for d in base.glob("R*") if (d / "revision.json").is_file() and revision_number(d.name) >= 0]
    return sorted(dirs, key=lambda d: revision_number(d.name))


# --------------------------------------------------------------------- diff --
def _short(v, n: int = 40) -> str:
    s = json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[: n - 3] + "..."


def load(rev_dir: Path) -> dict:
    """A snapshot's revision.json with each figure's provenance record attached."""
    rev = json.loads((rev_dir / "revision.json").read_text(encoding="utf-8"))
    for f in rev.get("figures", []):
        p = f.get("provenance")
        f["_record"] = json.loads((rev_dir / p).read_text(encoding="utf-8")) if p and (rev_dir / p).is_file() else None
    return rev


def figure_changes(fa: dict, fb: dict) -> dict:
    """What changed between two snapshot entries of the same figure."""
    out = {"pdf_changed": fa.get("source_sha256") != fb.get("source_sha256")}
    ra, rb = fa.get("_record"), fb.get("_record")
    if not (ra and rb):
        out["no_record"] = [side for side, r in (("A", ra), ("B", rb)) if not r]
        return out
    from fig_atlas.provenance import diff_records      # shared with `fa diff-figure`
    d = diff_records(ra, rb)
    out.update({k: d[k] for k in ("inputs", "code", "config_keys", "config_file_changed", "packages")})
    return out


def current(root: Path, figures: list[dict], tables: list[str], find_pdf) -> dict:
    """The working state in snapshot form (not written anywhere): published
    figure PDFs and provenance records as they are now."""
    import hashlib
    out = []
    for f in figures:
        pdf = find_pdf(f["project"], f.get("figure_number", 1))
        if not (pdf and pdf.is_file()):
            continue
        rec = provenance_path(pdf)
        out.append({"role": f["role"], "project": f["project"], "figure_number": f.get("figure_number", 1),
                    "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    "_record": json.loads(rec.read_text(encoding="utf-8")) if rec.is_file() else None})
    return {"revision": "current", "git_commit": None, "figures": out, "tables": tables}


def diff(a: dict, b: dict) -> dict:
    """Compare two snapshots (from load() or current())."""
    slots_a = {f["role"]: f for f in a.get("figures", [])}
    slots_b = {f["role"]: f for f in b.get("figures", [])}
    placement = []
    for slot in list(slots_a) + [s for s in slots_b if s not in slots_a]:
        fa_, fb_ = slots_a.get(slot), slots_b.get(slot)
        ida = fa_ and (fa_["project"], fa_["figure_number"])
        idb = fb_ and (fb_["project"], fb_["figure_number"])
        if ida != idb:
            placement.append({"slot": slot, "a": ida, "b": idb})
    key = lambda f: (f["project"], f["figure_number"])   # noqa: E731 -- the stable figure ID
    by_a = {key(f): f for f in a.get("figures", [])}
    by_b = {key(f): f for f in b.get("figures", [])}
    figures = []
    for k in [k for k in by_b if k in by_a]:
        ch = figure_changes(by_a[k], by_b[k])
        figures.append({"project": k[0], "figure_number": k[1], "slot_a": by_a[k]["role"],
                        "slot_b": by_b[k]["role"], **ch})
    ta, tb = set(a.get("tables", [])), set(b.get("tables", []))
    return {"a": a.get("revision"), "b": b.get("revision"),
            "a_commit": a.get("git_commit"), "b_commit": b.get("git_commit"),
            "placement": placement, "tables_added": sorted(tb - ta), "tables_removed": sorted(ta - tb),
            "figures": figures, "added": [list(k) for k in by_b if k not in by_a],
            "removed": [list(k) for k in by_a if k not in by_b]}


def _has_changes(f: dict) -> bool:
    return bool(f["pdf_changed"] or f["slot_a"] != f["slot_b"] or any(f.get("inputs", [[]])) or
                any(f.get("code", [[]])) or f.get("config_keys") or f.get("packages"))


def _id(x) -> str:
    return f"`{x[0]}` fig {x[1]}" if x else "(empty)"


def render(d: dict) -> str:
    """The diff as markdown (also the body of RNNN.changes.md)."""
    L = [f"# Storyline changes {d['a']} -> {d['b']}", "",
         f"<!-- generated by `fa storyline diff {d['a']} {d['b']}` from the two compile snapshots -->", "",
         f"Commits: {d['a_commit'] or 'working tree'} -> {d['b_commit'] or 'working tree'}", "", "## Placement", ""]
    if not (d["placement"] or d["tables_added"] or d["tables_removed"]):
        L.append("No slot changes.")
    for p in d["placement"]:
        L.append(f"- **{p['slot']}**: {_id(p['a'])} -> {_id(p['b'])}")
    L += [f"- table added: `{t}`" for t in d["tables_added"]]
    L += [f"- table removed: `{t}`" for t in d["tables_removed"]]
    L += ["", "## Figures", ""]
    changed = [f for f in d["figures"] if _has_changes(f)]
    if not changed:
        L.append("No figure changed.")
    for f in changed:
        slot = f["slot_b"] if f["slot_a"] == f["slot_b"] else f"{f['slot_a']} -> {f['slot_b']}"
        L.append(f"### {slot}: `{f['project']}` fig {f['figure_number']}")
        L.append("")
        L.append(f"- figure PDF: {'changed' if f['pdf_changed'] else 'identical'}")
        if f.get("no_record"):
            L.append(f"- no provenance record in snapshot {' and '.join(d[s.lower()] for s in f['no_record'])}; "
                     "only the PDF hash can be compared")
            L.append("")
            continue
        for label, (added, removed, mod) in (("input", f["inputs"]), ("code", f["code"])):
            L += [f"- {label} changed: `{p}`" for p in mod]
            L += [f"- {label} added: `{p}`" for p in added]
            L += [f"- {label} removed: `{p}`" for p in removed]
        keys = f["config_keys"]
        for k, va, vb in keys[:MAX_KEYS]:
            L.append(f"- config `{k}`: {_short(va)} -> {_short(vb)}")
        if len(keys) > MAX_KEYS:
            L.append(f"- ... {len(keys) - MAX_KEYS} more config key(s)")
        L += [f"- package {k}: {va} -> {vb}" for k, va, vb in f["packages"]]
        L.append("")
    if d["added"]:
        L += ["## Added figures", ""] + [f"- {_id(x)}" for x in d["added"]] + [""]
    if d["removed"]:
        L += ["## Removed figures", ""] + [f"- {_id(x)}" for x in d["removed"]] + [""]
    return "\n".join(L).rstrip() + "\n"


def draft_block(d: dict, n: int, today: str) -> str:
    """A suggested 개편(N) header for the storyline md, listing what changed;
    the author adds the why."""
    what = [f"{p['slot']} {_id(p['a'])} -> {_id(p['b'])}" for p in d["placement"]]
    what += [f"`{f['project']}` ({', '.join(x for x in ('data' if any(f.get('inputs', [[]])) else '', 'config' if f.get('config_keys') else '', 'code' if any(f.get('code', [[]])) else '') if x) or 'output'})"
             for f in d["figures"] if _has_changes(f) and f["slot_a"] == f["slot_b"]]
    return (f"> **{today} 개편({n}) — <title>**: <why>. Changes since {d['a']}: "
            + ("; ".join(what) if what else "none recorded") + ".")
