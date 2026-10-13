"""fa: one command-line entry point for building and checking figure atlases.

    fa list                         projects and where their configs live
    fa build <project>... | --all   analysis -> publish -> verify
    fa verify <project>             completeness checks for a built project
    fa status [project...]          which published figures are stale (content changed since built)
    fa impact <file|folder>         which published figures used a file
    fa lineage <project>            a figure's upstream: outputs <- run <- config <- code <- data bundles
    fa diff-figure <project>        what changed in a figure since a storyline snapshot (or a saved record)
    fa claims [project...]          numbers typed by hand into figure legends (--list, --write, --check)
    fa export <project>             a published figure as an RO-Crate (files, source data, provenance)
    fa lint [project...]            config keys the build never read, likely typos, defaults used (--hardcoded)
    fa param scaffold|explain|sync  renderer parameters: commented YAML, where a value comes from, fill defaults
    fa audit-print ...              printed font/line sizes on a page preset
    fa preflight ...                overlap, clipping and panel-intrusion checks
    fa baseline check|record ...    compendium output hashes (regression check)
    fa inventory [--check]          which project uses which renderer
    fa storyline [--plan ...]       compile storyline compendium PDF(s); also init | registry | check | revisions | snapshots | diff | requests | evidence
    fa manifest                     consolidate the master manifest

Run it from anywhere inside the repository (installed with ``pip install -e .``)
or as ``python -m fig_atlas`` without installing. ``--json`` prints machine-
readable results (list/build/verify) for scripts and AI agents; ``--dry-run``
shows what ``build`` would run without running it.

Exit codes: 0 success, 1 a build or check failed, 2 usage or configuration error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .projects import ProjectError, build_env, build_project, build_steps, find_project, find_root, list_projects

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2


def _emit(args, payload, text: str) -> None:
    print(json.dumps(payload, indent=1, ensure_ascii=False) if args.json else text)


# ------------------------------------------------------------------ commands --
def cmd_list(args, root: Path) -> int:
    projects = [p for p in list_projects(root) if args.archived or not p.archived]
    payload = [{"name": p.name, "namespace": p.namespace, "config": p.config_rel(root),
                "analysis_script": p.analysis_script, "archived": p.archived} for p in projects]
    width = max((len(p.name) for p in projects), default=10)
    text = "\n".join(f"{p.name:<{width}}  {p.namespace or '(top level)'}{'  [archived]' if p.archived else ''}"
                     for p in projects)
    _emit(args, payload, text + f"\n\n{len(projects)} project(s)" + ("" if args.archived else "; --archived to include retired ones"))
    return EXIT_OK


def cmd_build(args, root: Path) -> int:
    if args.all and args.projects:
        print("fa build: give project names or --all, not both", file=sys.stderr)
        return EXIT_USAGE
    if not (args.all or args.projects):
        print("fa build: name at least one project (see `fa list`) or use --all", file=sys.stderr)
        return EXIT_USAGE
    projects = list_projects(root) if args.all else [find_project(root, n) for n in args.projects]

    if args.dry_run:
        plan = [{"project": p.name, "config": p.config_rel(root),
                 "steps": [" ".join(Path(a).name if i == 0 else a for i, a in enumerate(s))
                           for s in build_steps(root, p, preflight=args.preflight)]} for p in projects]
        text = "\n".join(f"{x['project']}  (CONFIG_PATH={x['config']})\n" + "\n".join(f"  {s}" for s in x["steps"])
                         for x in plan)
        _emit(args, {"dry_run": True, "plan": plan}, text)
        return EXIT_OK

    results = []
    for p in projects:
        if not args.json:
            print(f"\n==== {p.name} ====", flush=True)
        r = build_project(root, p, capture=args.json, preflight=args.preflight)
        results.append(r)
        if not args.json and not r.ok:
            print(f"FAILED at {r.failed_step}", file=sys.stderr)
    failed = [r for r in results if not r.ok]
    if args.all and not failed:
        # Same as the old -Project ALL: consolidate only after a clean full build.
        from . import projects as _projects
        subprocess.run([sys.executable, *_projects.MANIFEST_STEP], cwd=root, env=build_env(),
                       stdout=subprocess.DEVNULL if args.json else None)
    payload = {"ok": not failed, "results": [r.__dict__ for r in results]}
    summary = (f"\nALL {len(results)} PROJECT(S) PASSED" if not failed else
               f"\nFAILED ({len(failed)}/{len(results)}): " + ", ".join(f"{r.project} [{r.failed_step}]" for r in failed))
    _emit(args, payload, summary)
    return EXIT_OK if not failed else EXIT_FAILED


def cmd_verify(args, root: Path) -> int:
    from . import get_config, verify_atlas, write_report
    p = find_project(root, args.project)
    config = get_config(p.config)
    rows = verify_atlas(config)
    failures = write_report(rows, config.manifests_root / "clean_atlas_verification.csv")
    warns = [r for r in rows if r["status"] == "WARN"]
    text = "\n".join(f"{r['status']:4}  [{r['kind']}] {r['id']}  {r['detail']}".rstrip()
                     for r in rows if r["status"] != "PASS")
    text = (text + "\n" if text else "") + (
        f"{'FAIL' if failures else 'PASS'}: {len(rows) - failures - len(warns)}/{len(rows)} checks passed"
        + (f", {len(warns)} warning(s)" if warns else ""))
    _emit(args, {"ok": failures == 0, "project": p.name, "rows": rows}, text)
    return EXIT_OK if failures == 0 else EXIT_FAILED


def cmd_status(args, root: Path) -> int:
    from . import get_config
    from .provenance import HashCache, check_freshness, is_orphan, published_records
    bases = [get_config(find_project(root, n).config).figures_root for n in args.projects] if args.projects else [None]
    cache = HashCache(root)
    rows, orphans = [], []
    for base in bases:
        for rec_path, rec in published_records(root, base):
            if is_orphan(root, rec):
                orphans.append(rec_path.parent.relative_to(root).as_posix())
                continue
            reasons = check_freshness(root, rec, cache)
            rows.append({"figure": rec_path.parent.relative_to(root).as_posix(), "fresh": not reasons,
                         "reasons": reasons, "built": (rec.get("run") or {}).get("finished")})
    cache.save()
    stale = [r for r in rows if not r["fresh"]]
    lines = []
    for r in rows:
        if r["fresh"] and not args.all:
            continue
        lines.append(f"{'fresh' if r['fresh'] else 'STALE'}  {r['figure']}")
        for why in r["reasons"][:5]:
            lines.append(f"         {why}")
        if len(r["reasons"]) > 5:
            lines.append(f"         ... {len(r['reasons']) - 5} more")
    summary = (f"\n{len(rows)} figure(s) with a provenance record: {len(rows) - len(stale)} fresh, "
               f"{len(stale)} stale" + ("" if args.all else " (--all lists the fresh ones too)"))
    if orphans:
        summary += (f"\n{len(orphans)} old output folder(s) of projects that no longer exist (moved or removed), not "
                    "checked: " + ", ".join(orphans[:5]) + (" ..." if len(orphans) > 5 else ""))
    text = "\n".join(lines + [summary])
    _emit(args, {"figures": rows, "stale": len(stale), "orphans": orphans}, text)
    return EXIT_FAILED if (args.check and stale) else EXIT_OK


def cmd_impact(args, root: Path) -> int:
    from .provenance import impacted_by
    found = impacted_by(root, args.path)
    hits = [h for h in found if not h["orphan"]]
    old = [h for h in found if h["orphan"]]
    text = "\n".join(f"{h['figure']}\n    via {', '.join(h['via'][:3])}{' ...' if len(h['via']) > 3 else ''}"
                     for h in hits) or f"no published figure records {args.path} among what it read"
    if hits:
        text += f"\n\n{len(hits)} figure(s) affected"
    if old:
        text += (f"\n{len(old)} old output folder(s) of projects that no longer exist also read it: "
                 + ", ".join(h["figure"] for h in old[:5]))
    _emit(args, {"path": args.path, "figures": hits, "old_outputs": old}, text)
    return EXIT_OK


def _figure_record(root: Path, project: str, number: int) -> tuple[Path, dict]:
    from . import get_config
    p = find_project(root, project)
    hits = sorted(get_config(p.config).figures_root.glob(f"figure_{number:02d}_*/figure_{number:02d}.provenance.json"))
    if not hits:
        raise ProjectError(f"{project} figure {number}: no published provenance record; build it with `fa build {project}`")
    return hits[0], json.loads(hits[0].read_text(encoding="utf-8"))


def cmd_lineage(args, root: Path) -> int:
    from .provenance import lineage
    rec_path, rec = _figure_record(root, args.project, args.figure)
    lines = lineage(rec)
    _emit(args, {"record": rec_path.relative_to(root).as_posix(), "record_data": rec},
          f"{args.project} figure {args.figure}  ({rec_path.parent.relative_to(root).as_posix()})\n" + "\n".join(lines))
    return EXIT_OK


def cmd_diff_figure(args, root: Path) -> int:
    from .provenance import diff_records
    rec_path, now = _figure_record(root, args.project, args.figure)
    name = f"{args.project}__fig{args.figure:02d}.json"
    if args.against:
        old_path = Path(args.against)
        old_path = old_path if old_path.is_absolute() else Path.cwd() / old_path
    else:
        snaps = sorted((root / "outputs" / "storylines").glob(f"*/{args.snapshot or 'R*'}/provenance/{name}"),
                       key=lambda q: int(q.parents[1].name[1:]) if q.parents[1].name[1:].isdigit() else -1)
        if not snaps:
            print(f"fa diff-figure: no storyline snapshot holds {name}"
                  + (f" for {args.snapshot}" if args.snapshot else "") + "; give --against <record.json>",
                  file=sys.stderr)
            return EXIT_USAGE
        old_path = snaps[-1]
    if not old_path.is_file():
        print(f"fa diff-figure: {old_path} not found", file=sys.stderr)
        return EXIT_USAGE
    d = diff_records(json.loads(old_path.read_text(encoding="utf-8")), now)
    try:
        label = old_path.relative_to(root).as_posix()
    except ValueError:
        label = str(old_path)
    lines = [f"{args.project} figure {args.figure}: {label} -> published record",
             f"  built  {d['built'][0]} -> {d['built'][1]}   commit {d['commits'][0] or '?'} -> {d['commits'][1] or '?'}",
             f"  outputs changed: {', '.join(d['outputs_changed']) or 'none (identical files)'}"]
    for kind in ("inputs", "code"):
        added, removed, changed = d[kind]
        lines += [f"  {kind[:-1] if kind == 'inputs' else kind} changed: {x}" for x in changed]
        lines += [f"  {kind[:-1] if kind == 'inputs' else kind} added:   {x}" for x in added]
        lines += [f"  {kind[:-1] if kind == 'inputs' else kind} removed: {x}" for x in removed]
    for k, va, vb in d["config_keys"][:args.max_keys]:
        lines.append(f"  config {k}: {json.dumps(va, ensure_ascii=False)} -> {json.dumps(vb, ensure_ascii=False)}")
    if len(d["config_keys"]) > args.max_keys:
        lines.append(f"  ... {len(d['config_keys']) - args.max_keys} more config key(s) (--max-keys, --json)")
    lines += [f"  package {k}: {va} -> {vb}" for k, va, vb in d["packages"]]
    if len(lines) == 3 and not d["outputs_changed"]:
        lines.append("  no recorded difference")
    _emit(args, {"old": label, "new": rec_path.relative_to(root).as_posix(), **d}, "\n".join(lines))
    return EXIT_OK


def cmd_export(args, root: Path) -> int:
    import shutil
    from .export import export_figure
    rec_path, _ = _figure_record(root, args.project, args.figure)
    out = Path(args.out) if args.out else root / "outputs" / "exports" / f"{args.project}_figure_{args.figure:02d}"
    out = out if out.is_absolute() else Path.cwd() / out
    export_figure(root, rec_path.parent, out, include_inputs=args.include_inputs)
    shown = out
    if args.zip:
        shown = Path(shutil.make_archive(str(out), "zip", root_dir=out))
    meta = json.loads((out / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    n_files = sum(1 for e in meta["@graph"] if e.get("@type") == "File" and not e["@id"].startswith("#"))
    try:
        shown = shown.relative_to(root)
    except ValueError:
        pass
    _emit(args, {"crate": str(shown), "files": n_files},
          f"RO-Crate: {shown}  ({n_files} file(s); inputs {'included' if args.include_inputs else 'listed by path and hash'})")
    return EXIT_OK


def _latest_record(root: Path, project) -> tuple[Path, dict] | tuple[None, None]:
    from . import get_config
    from .provenance import published_records
    recs = published_records(root, get_config(project.config).figures_root)
    recs = [(p, r) for p, r in recs if ((r.get("config") or {}).get("usage"))]
    return max(recs, key=lambda x: (x[1].get("run") or {}).get("finished") or "") if recs else (None, None)


def cmd_param(args, root: Path) -> int:
    from . import param_tools as pt
    if args.action == "scaffold":
        schemas = pt.renderer_schemas()
        name = args.target.removeprefix("render_")
        if name not in schemas:
            print(f"fa param: no schema for {args.target}; renderers with one: {', '.join(sorted(schemas))}",
                  file=sys.stderr)
            return EXIT_USAGE
        print(pt.scaffold(name), end="")
        return EXIT_OK
    p = find_project(root, args.target)
    _, rec = _latest_record(root, p)
    if args.action == "explain":
        if not args.key:
            print("fa param explain: give a dotted key, e.g. plots.volcano.lfc_min", file=sys.stderr)
            return EXIT_USAGE
        print(f"{p.name}: {args.key}")
        layout = pt.layout_schema(root / p.analysis_script) if p.analysis_script else []
        print("\n".join(pt.explain(root, p.config, args.key, rec, layout)))
        return EXIT_OK
    # sync
    if rec is None:
        print(f"fa param sync: no recorded key usage for {p.name}; build it first (`fa build {p.name}`)", file=sys.stderr)
        return EXIT_USAGE
    import yaml as _yaml
    raw = _yaml.safe_load(p.config.read_text(encoding="utf-8")) or {}
    layout = pt.layout_schema(root / p.analysis_script) if p.analysis_script else []
    plan = pt.sync_plan(rec, layout, raw)
    present = set()
    for item in plan:
        if pt._lookup(raw, item["path"])[0]:
            present.add(item["path"])
    plan = [i for i in plan if i["path"] not in present]
    todo = [i for i in plan if not i["skip"] or (args.include_computed and i["computed"] and i["comment"])]
    for i in todo:
        print(f"  + {i['path']}: {pt._yaml_value(i['value'])}  # {i['comment']}")
    skipped: dict[str, list] = {}
    for i in plan:
        if i not in todo:
            skipped.setdefault(i["skip"], []).append(i["path"])
    for why, paths in skipped.items():
        print(f"  skipped {len(paths)}: {why}")
        for path in paths[:args.max_keys]:
            print(f"      {path}")
        if len(paths) > args.max_keys:
            print(f"      ... {len(paths) - args.max_keys} more")
    if not args.apply:
        print(f"\n{len(todo)} key(s) would be added to {p.config_rel(root)}; --apply writes them")
        return EXIT_OK
    try:
        written = pt.apply_sync(p.config, plan, include_computed=args.include_computed)
    except yamledit_error() as exc:
        print(f"fa param sync: {exc}", file=sys.stderr)
        return EXIT_FAILED
    print(f"\nwrote {len(written)} key(s) to {p.config_rel(root)}; values are the defaults the build used, "
          "so figures do not change")
    return EXIT_OK


def yamledit_error():
    from .yamledit import NotRoundTrippable
    return NotRoundTrippable


def _lint_hardcoded(args, root: Path) -> int:
    from .param_tools import hardcoded
    if args.projects:
        files = [root / find_project(root, n).analysis_script for n in args.projects]
    else:
        from .renderer_registry import directories
        # This repository's own code: its analysis scripts, and the renderer packages that live in
        # it (the fig-atlas source tree, a pack under development). An installed package's
        # renderers are checked in its own repository.
        mine = [d for d in directories() if d.resolve().is_relative_to(root.resolve())]
        files = sorted(f for d in mine for f in d.glob("*.py")) + sorted((root / "analysis").rglob("*.py"))
        files = [f for f in files if "archive" not in f.parts]
    hits = hardcoded([f for f in files if f.is_file()])
    by_file: dict[str, list] = {}
    for h in hits:
        by_file.setdefault(Path(h["file"]).relative_to(root).as_posix(), []).append(h)
    base = root / HARDCODED_BASELINE
    if args.write:
        base.parent.mkdir(parents=True, exist_ok=True)
        base.write_text("file,count\n" + "".join(f"{f},{len(hs)}\n" for f, hs in sorted(by_file.items())),
                        encoding="utf-8")
        print(f"baseline written: {HARDCODED_BASELINE} ({len(hits)} literal(s) in {len(by_file)} file(s))")
    if args.check:
        if not base.is_file():
            print(f"fa lint --hardcoded --check: no baseline {HARDCODED_BASELINE}; record one with --write",
                  file=sys.stderr)
            return EXIT_USAGE
        import csv as _csv
        before = {r["file"]: int(r["count"]) for r in _csv.DictReader(base.open(encoding="utf-8"))}
        worse = [(f, before.get(f, 0), len(hs)) for f, hs in by_file.items() if len(hs) > before.get(f, 0)]
        for f, b, n in worse:
            print(f"INCREASED  {f}: {b} -> {n} literal style value(s)")
        if worse:
            return EXIT_FAILED
    if args.json:
        print(json.dumps(hits, indent=1, ensure_ascii=False))
        return EXIT_OK
    for f, hs in sorted(by_file.items(), key=lambda x: -len(x[1])):
        print(f"{len(hs):4}  {f}")
        if args.verbose:
            for h in hs:
                print(f"        {h['line']:5}  {h['kwarg']}={h['value']}   {h['code']}")
    print(f"\n{len(hits)} literal style value(s) in {len(by_file)} file(s) (fontsize=, linewidth=, s=, pad=, ...); "
          f"move them to the config, or mark a deliberate one with `# fa: allow-literal <reason>`. --verbose lists them.")
    return EXIT_OK


def cmd_lint(args, root: Path) -> int:
    if args.hardcoded:
        return _lint_hardcoded(args, root)
    import yaml
    from . import get_config
    from .config_usage import classify_unread, lint
    from .provenance import published_records
    projects = ([find_project(root, n) for n in args.projects] if args.projects
                else [p for p in list_projects(root) if not p.archived])
    results, typos_total = [], 0
    for p in projects:
        recs = published_records(root, get_config(p.config).figures_root)
        usages = [(r.get("config") or {}).get("usage") for _, r in recs]
        usages = [u for u in usages if u]
        if not usages:
            results.append({"project": p.name, "recorded": False})
            continue
        read = set().union(*(u["read"] for u in usages))
        missed = set().union(*(u["missed"] for u in usages)) - read
        raw = yaml.safe_load(p.config.read_text(encoding="utf-8")) or {}
        res = lint(raw, read, missed)
        # The code the build ran (script, fig_atlas modules, renderers): a key
        # whose name it never mentions has no code left that could read it.
        code_files = {c["path"] for _, r in recs for c in r.get("code", [])}
        code_text = "\n".join((root / c).read_text(encoding="utf-8", errors="replace")
                              for c in sorted(code_files) if (root / c).is_file())
        res["unread_groups"] = classify_unread(raw, res["unread"], read, code_text)
        typos_total += len(res["typos"])
        results.append({"project": p.name, "recorded": True, "config": p.config_rel(root), **res})
    fail = EXIT_FAILED if (args.check and typos_total) else EXIT_OK
    if args.json:
        print(json.dumps(results, indent=1, ensure_ascii=False))
        return fail
    for r in results:
        if not r["recorded"]:
            if args.projects:
                print(f"{r['project']}: no key usage recorded yet; build it with `fa build {r['project']}`")
            continue
        print(f"{r['project']}  ({r['config']})")
        for t in r["typos"]:
            print(f"  TYPO?   {t['key']}  -- not read; the code reads {t['code_reads']}, which is absent (default used)")
        labels = {
            "no_code": "no code mentions it (editing it changes nothing; remove it, or restore the code)",
            "switched_off": "feature switched off (kept: turn the toggle on to use it)",
            "not_reached": "not reached by this build (alternative panel or data-dependent branch; kept)",
        }
        for why, label in labels.items():
            groups = [g for g in r["unread_groups"] if g["why"] == why]
            if not groups:
                continue
            print(f"  unread  {sum(g['keys'] for g in groups)} key(s): {label}")
            shown = groups if args.verbose else groups[:args.max_keys]
            for g in shown:
                extra = f"  <- {g['toggle']}: false" if g.get("toggle") else ""
                print(f"          {g['key']}" + (f"  ({g['keys']} keys)" if g["keys"] > 1 else "") + extra)
            if len(shown) < len(groups):
                print(f"          ... {len(groups) - len(shown)} more (--verbose)")
        print(f"  default {len(r['missed'])} key(s) the code read but the config lacks (a Python default was used)")
        if args.defaults:
            for k in r["missed"]:
                print(f"          {k}")
    linted = [r for r in results if r["recorded"]]
    print(f"\n{len(linted)} project(s) linted ({len(results) - len(linted)} without recorded key usage): "
          f"{typos_total} likely typo(s), {sum(len(r['unread']) for r in linted)} unread key(s), "
          f"{sum(len(r['missed']) for r in linted)} default(s) used. A likely typo is a name-similarity guess: "
          f"check it before renaming.")
    return fail


CLAIMS_BASELINE = Path("docs") / "baselines" / "hand_typed_numbers.csv"
HARDCODED_BASELINE = Path("docs") / "baselines" / "hardcoded_literals.csv"


def _specs(root: Path, project) -> list:
    """The FigureSpecs a project publishes (its project.spec_pattern under figure_specs/)."""
    import importlib.util
    import yaml
    raw = yaml.safe_load(project.config.read_text(encoding="utf-8")) or {}
    pattern = (raw.get("project") or {}).get("spec_pattern") or f"figure_*_{project.name}.py"
    out = []
    for path in sorted((root / "figure_specs").glob(f"**/{pattern}")):
        mod_spec = importlib.util.spec_from_file_location(f"_fa_spec_{path.stem}".replace("-", "_"), path)
        module = importlib.util.module_from_spec(mod_spec)
        try:
            mod_spec.loader.exec_module(module)
        except Exception:
            continue
        if hasattr(module, "SPEC"):
            out.append(module.SPEC)
    return out


def cmd_claims(args, root: Path) -> int:
    import csv
    from .claims import placeholders, scan
    projects = ([find_project(root, n) for n in args.projects] if args.projects
                else [p for p in list_projects(root) if not p.archived])
    rows = []
    for p in projects:
        for spec in _specs(root, p):
            text = "\n".join([spec.title, *spec.panel_notes, spec.claim_boundary])
            for h in scan(text):
                rows.append({"project": p.name, "figure": spec.number, **h})
            for name in placeholders(text):
                rows.append({"project": p.name, "figure": spec.number, "number": "{" + name + "}",
                             "kind": "live", "context": ""})
    fields = ["project", "figure", "kind", "number", "context"]
    if args.write:
        out = root / CLAIMS_BASELINE
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(r for r in rows if r["kind"] == "claim")
    counts: dict[tuple, dict] = {}
    for r in rows:
        c = counts.setdefault((r["project"], r["figure"]), {})
        c[r["kind"]] = c.get(r["kind"], 0) + 1
    worse = []
    if args.check:
        base = root / CLAIMS_BASELINE
        if not base.is_file():
            print(f"fa claims: no baseline {CLAIMS_BASELINE}; record one with --write", file=sys.stderr)
            return EXIT_USAGE
        before: dict[tuple, int] = {}
        with base.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                k = (r["project"], int(r["figure"]))
                before[k] = before.get(k, 0) + 1
        worse = [(k, before.get(k, 0), c.get("claim", 0)) for k, c in counts.items() if c.get("claim", 0) > before.get(k, 0)]
    if args.json:
        print(json.dumps({"rows": rows, "increased": worse}, indent=1, ensure_ascii=False))
    else:
        width = max((len(k[0]) for k in counts), default=10)
        print(f"{'project':<{width}}  fig  hand-typed claims  (thresholds / references / other)  live")
        for (proj, fig), c in sorted(counts.items()):
            print(f"{proj:<{width}}  {fig:>3}  {c.get('claim', 0):>17}  ({c.get('threshold', 0)} / "
                  f"{c.get('reference', 0)} / {c.get('other', 0)})  {c.get('live', 0)}")
            if args.list:
                for r in rows:
                    if (r["project"], r["figure"]) == (proj, fig) and r["kind"] == "claim":
                        print(f"        {r['number']:>8}  ...{r['context']}...")
        total = sum(c.get("claim", 0) for c in counts.values())
        live = sum(c.get("live", 0) for c in counts.values())
        print(f"\n{total} hand-typed number(s) that look like data results, {live} live placeholder(s), "
              f"in {len(counts)} figure(s). The sort is heuristic: --list shows them.")
        if args.write:
            print(f"baseline written: {CLAIMS_BASELINE}")
        for k, b, n in worse:
            print(f"INCREASED  {k[0]} figure {k[1]}: {b} -> {n} hand-typed numbers")
    return EXIT_FAILED if worse else EXIT_OK


def cmd_bundle(args, root: Path) -> int:
    """`fa bundle check <path>... | --all` and `fa bundle contracts` (fig_atlas.contracts)."""
    from .contracts import all_contracts, check_bundle, find_bundles, ingest_map
    contracts, ingest = all_contracts(), ingest_map()
    if args.action == "contracts":
        rows = [{"name": c.name, "plot_types": list(c.plot_types), "required": list(c.required),
                 "expected": list(c.expected), "renderer": {t: ingest.get(t) for t in c.plot_types},
                 "role_columns": {p: d for p, d in c.role_columns}, "role_optional": list(c.role_optional),
                 "doc": c.doc} for c in contracts]
        uncovered = sorted(set(ingest) - {t for c in contracts for t in c.plot_types})
        if args.json:
            print(json.dumps({"contracts": rows, "plot_types_without_contract": uncovered}, indent=1))
            return EXIT_OK
        for r in rows:
            print(f"{r['name']:<34} plot_type {', '.join(r['plot_types'])}")
            if r["role_columns"]:
                roles = ", ".join(f"{p} (default {d})" if d else p for p, d in r["role_columns"].items())
                print(f"    columns named in plot_params: {roles}"
                      + (f"; optional: {', '.join(r['role_optional'])}" if r["role_optional"] else ""))
            else:
                print(f"    required: {', '.join(r['required']) or '-'}")
            if r["expected"]:
                print(f"    expected: {', '.join(r['expected'])}")
            print(f"    renderer: {', '.join(str(v) for v in r['renderer'].values())}   doc: {r['doc']}")
        if uncovered:
            print(f"\nplot types with a renderer but no contract: {', '.join(uncovered)}")
        return EXIT_OK
    paths = [Path(p) for p in args.paths]
    if args.all or not paths:
        paths = find_bundles(root / "raw_data")
    if not paths:
        print("fa: no bundles found", file=sys.stderr)
        return EXIT_USAGE
    reports = [check_bundle(p if p.is_absolute() else (Path.cwd() / p), contracts, ingest, rel_to=root)
               for p in paths]
    if args.json:
        print(json.dumps([r.as_dict() for r in reports], indent=1))
    else:
        for r in reports:
            if not (r.findings and (args.verbose or r.errors or r.warnings)):
                continue
            print(f"{r.bundle}  [{r.plot_type or 'no plot_type'}"
                  + (f" -> {r.contract}" if r.contract else "") + "]")
            for f in r.findings:
                if args.verbose or f.level != "info":
                    print(f"    {f.level.upper():<5} {f.message}")
        n_err = sum(r.errors > 0 for r in reports)
        n_warn = sum(r.warnings > 0 and r.errors == 0 for r in reports)
        n_contract = sum(r.contract is not None for r in reports)
        print(f"\n{len(reports)} bundle(s): {len(reports) - n_err - n_warn} ok, {n_warn} with warnings, "
              f"{n_err} with errors; {n_contract} matched a contract. --verbose lists every finding.")
    return EXIT_FAILED if any(r.errors for r in reports) else EXIT_OK


def _run_changeset(cs, args, after=None) -> int:
    """Show (--dry-run) or apply a ChangeSet; ``after`` checks the result."""
    if cs.empty:
        msg = "nothing to change: already in place"
        print(json.dumps({"applied": False, "changes": [], "notes": [msg]}) if args.json else msg)
        return EXIT_OK
    if args.dry_run:
        if args.json:
            print(cs.as_json(applied=False))
        else:
            print("\n".join(cs.summary()) + "\n\n" + cs.diff())
            for n in cs.notes:
                print(f"note: {n}")
            print("\n(dry run: nothing written)")
        return EXIT_OK
    cs.apply()
    problems = after() if after else []
    if args.json:
        out = json.loads(cs.as_json(applied=True))
        out["problems"] = problems
        print(json.dumps(out, indent=1))
    else:
        print("\n".join(cs.summary()))
        for n in cs.notes:
            print(f"note: {n}")
        for p in problems:
            print(f"PROBLEM: {p}")
    return EXIT_FAILED if problems else EXIT_OK


def cmd_init(args) -> int:
    """`fa init [PATH]`: an empty project repository (fig_atlas.repo_commands.plan_init)."""
    from .repo_commands import plan_init
    target = Path(args.path).resolve()
    target.mkdir(parents=True, exist_ok=True)
    cs, err = _plan_or_fail(lambda: plan_init(target))
    return err if err else _run_changeset(cs, args)


def cmd_new(args, root: Path) -> int:
    """`fa new project <name> [--domain D --category C]` or `fa new renderer <name>`."""
    from .changeset import ChangeConflict
    from .repo_commands import plan_new_project, plan_new_renderer
    if args.kind == "renderer":
        cs, err = _plan_or_fail(lambda: plan_new_renderer(root, args.name, args.package, args.plot_type, args.doc,
                                                          start_from=args.start_from))
        return err if err else _run_changeset(cs, args)
    try:
        cs = plan_new_project(root, args.name, args.domain, args.category, args.raw_root, args.slug)
    except ChangeConflict as exc:
        print(f"fa: {exc}", file=sys.stderr)
        return EXIT_FAILED

    def check():
        try:
            p = find_project(root, args.name)
            from .config import ProjectConfig
            ProjectConfig(p.config)
            return []
        except Exception as exc:                          # noqa: BLE001 -- reported, not raised
            return [f"the new project does not load: {exc}"]
    return _run_changeset(cs, args, after=check)


def _plan_or_fail(plan):
    from .changeset import ChangeConflict
    try:
        return plan(), None
    except (ChangeConflict, ProjectError) as exc:
        print(f"fa: {exc}", file=sys.stderr)
        return None, EXIT_FAILED


def _build_check(root: Path, name: str, skip: bool):
    """After a move: build the project once to confirm it still builds (AGENTS.md 5.3)."""
    def check():
        if skip:
            return []
        from .projects import build_project
        result = build_project(root, find_project(root, name), capture=True)
        return [] if result.ok else [f"{name} no longer builds: step {result.failed_step!r} failed (see `fa build {name}`)"]
    return check


def cmd_retire(args, root: Path) -> int:
    """`fa retire <project>`: move it to <domain>/archive/ and build it once."""
    from .repo_commands import plan_retire
    cs, err = _plan_or_fail(lambda: plan_retire(root, args.project))
    if err:
        return err
    return _run_changeset(cs, args, after=_build_check(root, args.project, args.no_build))


def cmd_promote(args, root: Path) -> int:
    """`fa promote <project> --figure N --slug s [--supp]`."""
    from .repo_commands import paper_name, plan_promote
    cs, err = _plan_or_fail(lambda: plan_promote(root, args.project, args.figure, args.slug, args.supp))
    if err:
        return err
    domain = find_project(root, args.project).namespace.split("/")[0] if not cs.empty else ""
    new = paper_name(domain, args.figure, args.slug, args.supp) if domain else args.project
    return _run_changeset(cs, args, after=_build_check(root, new, args.no_build))


def cmd_ingest(args, root: Path) -> int:
    """`fa ingest bundle <bundle> --project P [--name N]`: Case B as one command."""
    from .repo_commands import plan_ingest_bundle
    cs, err = _plan_or_fail(lambda: plan_ingest_bundle(root, Path(args.path), args.project, args.name))
    if err:
        return err
    return _run_changeset(cs, args, after=_build_check(root, args.project, args.no_build))


def cmd_mcp(args, root: Path) -> int:
    """`fa mcp`: an MCP server on stdin/stdout (fig_atlas.mcp_server)."""
    from .mcp_server import serve
    return serve(root)


def cmd_renderers(args, root: Path) -> int:
    """`fa renderers`: every plot name fig_atlas.render() can draw, and where it lives."""
    from .renderer_registry import available
    rows = available()
    if args.json:
        print(json.dumps(rows, indent=1))
        return EXIT_OK
    width = max(len(r["name"]) for r in rows)
    for r in rows:
        print(f"{r['name']:<{width}}  {r['source']:<34} {r['function']}")
    print(f"\n{len({r['name'] for r in rows})} plot names. Draw one with fig_atlas.render(name, ax, data, params).")
    return EXIT_OK


def _plugin_commands(sub) -> dict:
    """Commands that installed packs add (fig_atlas.commands entry points)."""
    from .plugins import load_all
    handlers: dict = {}
    for plugin, register in load_all("commands"):
        try:
            handlers.update(register(sub))
        except Exception as exc:                        # noqa: BLE001 -- a broken pack must not break `fa`
            print(f"fa: plugin command {plugin.name} failed to register: {exc}", file=sys.stderr)
    return handlers


def _passthrough(target: str, extra: list[str], root: Path) -> int:
    """Run a tool with the build environment in the project repository; its
    exit code becomes ours. ``target`` is a module of the package
    (fig_atlas.tools.*) or, for development tools of the fig-atlas source
    repository, a script path in it."""
    if target.endswith(".py"):
        if not (root / target).is_file():
            print(f"fa: {target} is a development tool of the fig-atlas source repository, not found here",
                  file=sys.stderr)
            return EXIT_USAGE
        cmd = [sys.executable, target]
    else:
        cmd = [sys.executable, "-m", target]
    return subprocess.run([*cmd, *extra], cwd=root, env=build_env()).returncode


PASSTHROUGH = {
    "audit-print": ("fig_atlas.tools.audit_print_size", "printed font/line sizes of figures on a page preset"),
    "baseline": ("fig_atlas.tools.figure_baseline", "record/check compendium output hashes (check|record [--build])"),
    "inventory": ("fig_atlas.tools.renderer_inventory", "regenerate (or --check) docs/reference/renderer_inventory.md"),
    "preflight": ("fig_atlas.tools.preflight", "overlap, clipping and panel-intrusion checks (--projects ...)"),
    "storyline": ("fig_atlas.tools.storyline", "storyline tools: new | compile [--plan|--all] | init | registry | check | revisions | snapshots | diff | requests | evidence"),
    "manifest": ("fig_atlas.tools.consolidate_manifest", "consolidate outputs/clean_atlas_manifest.csv"),
    "reference": ("scripts/make_reference.py", "regenerate (or --check) docs/reference/{cli,api,config,gallery}.md"),
}


# -------------------------------------------------------------------- parser --
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="fa", description=__doc__.split("\n\n")[0],
                                 epilog="Run `fa <command> -h` for a command's options.")
    ap.add_argument("--root", type=Path, help="repository root (default: found from the working directory)")
    sub = ap.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("list", help="list projects")
    p.add_argument("--archived", action="store_true", help="include retired (archive/) projects")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("build", help="analysis -> publish -> verify for projects")
    p.add_argument("projects", nargs="*", metavar="PROJECT", help="bare project name(s), see `fa list`")
    p.add_argument("--all", action="store_true", help="every project, then consolidate the master manifest")
    p.add_argument("--dry-run", action="store_true", help="show the steps without running them")
    p.add_argument("--preflight", action="store_true",
                   help="run `fa preflight` after publishing, before verify (verify then reports its findings)")
    p.add_argument("--json", action="store_true", help="machine-readable result (child output is captured)")

    p = sub.add_parser("verify", help="completeness checks for one built project")
    p.add_argument("project", metavar="PROJECT")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("status", help="which published figures are stale (inputs/code/config changed)")
    p.add_argument("projects", nargs="*", metavar="PROJECT", help="limit to these projects (default: all)")
    p.add_argument("--all", action="store_true", help="also list the fresh figures")
    p.add_argument("--check", action="store_true", help="exit 1 if any figure is stale")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("impact", help="which published figures used a given file or folder")
    p.add_argument("path", help="a file or folder, e.g. raw_data/<study>/<bundle>/inputs/data.csv")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("lineage", help="a published figure's upstream: outputs <- run <- config <- code <- data")
    p.add_argument("project", metavar="PROJECT")
    p.add_argument("--figure", type=int, default=1, help="figure number (default 1)")
    p.add_argument("--json", action="store_true", help="machine-readable output (the full record)")

    p = sub.add_parser("diff-figure", help="what changed in a figure since a storyline snapshot or a saved record")
    p.add_argument("project", metavar="PROJECT")
    p.add_argument("--figure", type=int, default=1, help="figure number (default 1)")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--snapshot", metavar="RNNN", help="storyline snapshot (default: the latest holding the figure)")
    src.add_argument("--against", metavar="RECORD", help="a provenance record file to compare with")
    p.add_argument("--max-keys", type=int, default=20, help="config keys listed (default 20)")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("lint", help="config keys the build never read, likely typos, and defaults used")
    p.add_argument("projects", nargs="*", metavar="PROJECT", help="limit to these projects (default: all active)")
    p.add_argument("--defaults", action="store_true", help="list the keys that fell back to Python defaults")
    p.add_argument("--verbose", action="store_true", help="list every unread key")
    p.add_argument("--max-keys", type=int, default=15, help="unread keys listed per project (default 15)")
    p.add_argument("--check", action="store_true", help="exit 1 if a likely typo is found")
    p.add_argument("--hardcoded", action="store_true",
                   help="instead: literal style values (fontsize=7, ...) in renderers and analysis scripts")
    p.add_argument("--write", action="store_true", help="--hardcoded: record the baseline")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("param", help="renderer parameters: scaffold | explain | sync")
    p.add_argument("action", choices=("scaffold", "explain", "sync"))
    p.add_argument("target", metavar="RENDERER|PROJECT", help="a renderer (scaffold) or a project (explain, sync)")
    p.add_argument("key", nargs="?", help="explain: dotted config key, e.g. plots.volcano.lfc_min")
    p.add_argument("--apply", action="store_true", help="sync: write the keys (default: show them)")
    p.add_argument("--max-keys", type=int, default=8, help="sync: skipped keys listed per reason")
    p.add_argument("--include-computed", action="store_true",
                   help="sync: also write defaults the renderer computes (freezes today's value)")

    p = sub.add_parser("export", help="package a published figure as an RO-Crate (files, source data, provenance)")
    p.add_argument("project", metavar="PROJECT")
    p.add_argument("--figure", type=int, default=1, help="figure number (default 1)")
    p.add_argument("--out", metavar="DIR", help="crate folder (default outputs/exports/<project>_figure_NN)")
    p.add_argument("--zip", action="store_true", help="also write <DIR>.zip")
    p.add_argument("--include-inputs", action="store_true", help="copy the raw inputs into the crate (default: list them)")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("claims", help="numbers typed by hand into figure legends (they go stale when data changes)")
    p.add_argument("projects", nargs="*", metavar="PROJECT", help="limit to these projects (default: all active)")
    p.add_argument("--list", action="store_true", help="show each hand-typed number in context")
    p.add_argument("--write", action="store_true", help=f"record the baseline ({CLAIMS_BASELINE.as_posix()})")
    p.add_argument("--check", action="store_true", help="exit 1 if any figure has more than the baseline")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("init", help="make a project repository here (or in PATH): folders, marker, rules, .gitignore")
    p.add_argument("path", nargs="?", default=".", help="folder to set up (default: the working directory)")
    p.add_argument("--dry-run", action="store_true", help="show the files; write nothing")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("new", help="create a project (config, analysis script, figure spec, build-list entry) "
                                   "or a renderer (module with its SCHEMA, test, export)")
    p.add_argument("kind", choices=("project", "renderer"))
    p.add_argument("name", help="project name (lower-case letters, digits, -) or renderer name (a Python name: "
                                "letters, digits, _)")
    p.add_argument("--package", default="fig_atlas.renderers",
                   help="renderer: the package it goes in (default the core; a pack only for a field-specific shape)")
    p.add_argument("--plot-type", help="renderer: bundles with this plot_type are drawn by it (fa ingest bundle)")
    p.add_argument("--doc", help="renderer: one line on what the plot shows (module docstring)")
    p.add_argument("--from", dest="start_from", metavar="RENDERER",
                   help="renderer: start from a copy of this existing renderer (`fa renderers`; the gallery shows "
                        "each) instead of the placeholder scatter plot")
    p.add_argument("--domain", help="namespace domain, e.g. lab (omit with --category for a flat sandbox project)")
    p.add_argument("--category", choices=("exploratory", "paper"), help="namespace category")
    p.add_argument("--raw-root", help="input bundle folder (default raw_data/<name>)")
    p.add_argument("--slug", default="main", help="figure 1 slug used in file names (default main)")
    p.add_argument("--dry-run", action="store_true", help="show the files and diffs; write nothing")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("ingest", help="add a data bundle to a project: check it, write its full plots block, build")
    p.add_argument("kind", choices=("bundle",))
    p.add_argument("path", metavar="BUNDLE", help="bundle folder (inputs/ + metadata/metadata.yaml)")
    p.add_argument("--project", required=True, help="the project whose config gets the plots block")
    p.add_argument("--name", help="plots.<name> (default: the bundle folder name without _bundle)")
    p.add_argument("--no-build", action="store_true", help="skip the confirming build")
    p.add_argument("--dry-run", action="store_true", help="show the config change; write nothing")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("retire", help="move a project to <domain>/archive/ (AGENTS.md 5.3) and build it once")
    p.add_argument("project", metavar="PROJECT")
    p.add_argument("--no-build", action="store_true", help="skip the confirming build")
    p.add_argument("--dry-run", action="store_true", help="show the moves and diffs; write nothing")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("promote", help="promote an exploratory project to a paper figure (AGENTS.md 5.2)")
    p.add_argument("project", metavar="PROJECT")
    p.add_argument("--figure", type=int, required=True, help="figure number in the storyline")
    p.add_argument("--slug", required=True, help="short name: <domain>-paper-main-fig<N>-<slug>")
    p.add_argument("--supp", action="store_true", help="a supplementary figure (...-paper-supp-fig<N>-<slug>)")
    p.add_argument("--no-build", action="store_true", help="skip the confirming build")
    p.add_argument("--dry-run", action="store_true", help="show the moves and diffs; write nothing")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("mcp", help="serve the fa commands as tools to AI agents (Model Context Protocol, stdio)")

    p = sub.add_parser("renderers", help="plot names fig_atlas.render() can draw: core, packs and recipes")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("bundle", help="data bundles: check them against their contract, or list the contracts")
    p.add_argument("action", choices=("check", "contracts"))
    p.add_argument("paths", nargs="*", metavar="BUNDLE", help="bundle folder(s) (default with check: every bundle under raw_data/)")
    p.add_argument("--all", action="store_true", help="check every bundle under raw_data/")
    p.add_argument("--verbose", action="store_true", help="also list bundles and findings at info level")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    for name, (_, help_) in PASSTHROUGH.items():
        sub.add_parser(name, help=help_, add_help=False)
    ap.plugin_handlers = _plugin_commands(sub)
    return ap


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = build_parser()
    # Pass-through commands forward every remaining argument (including -h) to
    # their script, so they're dispatched before argparse sees those options.
    root_arg = None
    if len(argv) >= 2 and argv[0] == "--root":
        root_arg, argv = Path(argv[1]), argv[2:]
    if argv and argv[0] == "init":
        # `fa init [PATH]` makes a project repository, so it needs none to exist.
        return cmd_init(ap.parse_args(argv))
    if argv and argv[0] in PASSTHROUGH:
        try:
            root = find_root(root_arg)
        except ProjectError as exc:
            print(f"fa: {exc}", file=sys.stderr)
            return EXIT_USAGE
        return _passthrough(PASSTHROUGH[argv[0]][0], argv[1:], root)

    args = ap.parse_args(argv)
    if root_arg is not None:
        args.root = root_arg
    if not args.command:
        ap.print_help()
        return EXIT_USAGE
    try:
        root = find_root(args.root)
        handlers = {"list": cmd_list, "build": cmd_build, "verify": cmd_verify, "status": cmd_status,
                    "impact": cmd_impact, "lineage": cmd_lineage, "diff-figure": cmd_diff_figure,
                    "claims": cmd_claims, "export": cmd_export, "lint": cmd_lint,
                    "param": cmd_param, "bundle": cmd_bundle, "renderers": cmd_renderers, "new": cmd_new, "retire": cmd_retire, "promote": cmd_promote, "ingest": cmd_ingest,
                    "mcp": cmd_mcp}
        return {**ap.plugin_handlers, **handlers}[args.command](args, root)
    except ProjectError as exc:
        print(f"fa: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
