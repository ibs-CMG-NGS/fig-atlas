"""Run preflight checks on projects' figures (roadmap Phase 3).

For each project, runs its analysis script in a subprocess with
``Figure.savefig`` intercepted (the same approach as audit_print_size.py):
each figure is checked by ``fig_atlas.preflight.preflight`` against the area
it is actually saved with -- the canvas for a plain savefig, nothing for
``bbox_inches="tight"``, or the box ``save_page_figure`` passes -- and no
output file is written. Thresholds come from the project's resolved config
(``preflight:`` block, e.g. styles/print.yaml).

Also checks, while the script renders, for font families that had to be
substituted and missing glyphs, and -- on the files the project last
published -- PDF fonts (Type 3 / not embedded / not allowed) and PNG
resolution at the printed size. Run `fa build` first so those files are current.

Writes outputs/preflight/preflight_findings.csv and, per figure with
findings, an overlay PNG (outputs/preflight/<project>/<figure>.png) with each
finding outlined and numbered (red = error, orange = warn).

Usage:
    python scripts/preflight.py                         # storyline compendium projects
    python scripts/preflight.py --projects <name> ...
    fa preflight ...                                    # same
Exit code 1 if any error-level finding.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path
from fig_atlas.config import style_path  # noqa: E402
from fig_atlas.tools import project_root  # noqa: E402  (the project repository, not this package)

ROOT = project_root()
sys.path.insert(0, str(ROOT))

from fig_atlas.projects import ProjectError, build_env, find_project  # noqa: E402

OUT = ROOT / "outputs" / "preflight"


def compendium_projects() -> list[str]:
    spec = importlib.util.spec_from_file_location("figure_baseline", Path(__file__).with_name("figure_baseline.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compendium_projects()


# ----------------------------------------------------------------- worker ----
def run_worker(project: str, out_json: Path) -> int:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.transforms import Bbox

    from fig_atlas import get_config
    from fig_atlas.preflight import capture_font_issues, check_print_size, draw_overlay, preflight

    p = find_project(ROOT, project)
    config = get_config(p.config)
    params = config._raw.get("preflight", {}) or {}
    real_savefig = Figure.savefig
    results: dict[str, list] = {}
    profiles: dict[str, dict] = {}

    def fake_savefig(self, fname, *args, **kwargs):
        stem = Path(str(fname)).with_suffix("").name
        if stem in results:
            return
        bb = kwargs.get("bbox_inches")
        if bb == "tight":
            saved = "tight"
        elif isinstance(bb, Bbox):
            saved = (bb.x0, bb.y0, bb.x1, bb.y1)
        else:
            saved = None
        dpi = kwargs.get("dpi", matplotlib.rcParams["savefig.dpi"])
        save_dpi = float(self.dpi if dpi in (None, "figure") else dpi)
        prof: dict = {}
        findings = preflight(self, saved_bbox_in=saved, params=params, save_dpi=save_dpi, profile=prof)
        if config.page is not None:   # C1: only figures drawn for a page preset have a print size
            pc = config.print_check
            findings += check_print_size(self, config.page, pc["min_font_pt"], pc["min_line_pt"],
                                         allow=params.get("allow"))
        results[stem] = [f.to_dict() for f in findings]
        profiles[stem] = {role: {str(k): v for k, v in sizes.items()} for role, sizes in prof.items()}
        if findings:
            d = OUT / project
            d.mkdir(parents=True, exist_ok=True)
            Figure.savefig = real_savefig
            try:
                draw_overlay(self, findings, d / f"{stem}.png")
            finally:
                Figure.savefig = fake_savefig

    Figure.savefig = fake_savefig
    os.chdir(ROOT)
    sys.argv = [p.analysis_script]
    # Font substitutions and missing glyphs surface as log records / warnings
    # while the script renders, not per figure, so they are reported once
    # for the whole run under "(render)".
    with capture_font_issues() as font_findings:
        runpy.run_path(str(ROOT / p.analysis_script), run_name="__main__")
    if font_findings:
        results["(render)"] = [f.to_dict() for f in font_findings]
    out_json.write_text(json.dumps({"findings": results, "profiles": profiles}, default=float), encoding="utf-8")
    return 0


# ------------------------------------------------------- published files ----
def check_published_files(project) -> dict[str, list]:
    """Font and resolution checks on the files the project published
    (outputs/.../figures/figure_*/figure_*.pdf|png). A PNG wider than the
    page preset's content box prints scaled down to that width."""
    from fig_atlas import get_config
    from fig_atlas.preflight import check_pdf, check_png

    config = get_config(project.config)
    params = config._raw.get("preflight", {}) or {}
    page_w = config.page.content_width_in if config.page is not None else None
    out: dict[str, list] = {}
    for f in sorted(config.figures_root.glob("figure_*/figure_*.*")):
        if f.suffix == ".pdf":
            found = check_pdf(f, params)
        elif f.suffix == ".png":
            printed = None
            if page_w:
                from PIL import Image
                limit, Image.MAX_IMAGE_PIXELS = Image.MAX_IMAGE_PIXELS, None   # header only
                try:
                    with Image.open(f) as im:
                        own = im.size[0] / float((im.info.get("dpi") or (config.dpi,))[0])
                finally:
                    Image.MAX_IMAGE_PIXELS = limit
                printed = min(own, page_w)
            found = check_png(f, params, printed_width_in=printed)
        else:
            continue
        if found:
            out[f.relative_to(ROOT).as_posix()] = [x.to_dict() for x in found]
    return out


# ---------------------------------------------------- across figures (C8) ----
# Text roles -> the shared style preset's size key (styles/print.yaml figures:).
PRESET_KEYS = {"tick": "tick_label_size", "axis_label": "axes_label_size", "panel_tag": "subpanel_label_size"}


def consistency_rows(profiles: dict[tuple[str, str], dict]) -> list[dict]:
    """Figures drawn on one print preset should use one size per text role.

    Reference per role: the size the project's style presets declare (their
    merged ``figures:`` block -- print.yaml, or a journal preset layered on it)
    where they have one, otherwise the size most
    figures use (one vote per figure, so a figure with hundreds of tiny
    labels doesn't set the standard). Reported as info: a figure's own config
    may shrink a dense panel on purpose; this lists where figures diverge.
    """
    from collections import Counter

    import yaml

    from fig_atlas.config import _deep_merge, find_config_file

    def preset_sizes(project: str) -> tuple[dict, str]:
        names = ["print"]
        try:
            cfg = yaml.safe_load(find_config_file(ROOT, f"config_{project}.yaml").read_text(encoding="utf-8")) or {}
            names = (cfg.get("project") or {}).get("style") or names
        except FileNotFoundError:
            pass
        names = [names] if isinstance(names, str) else list(names)
        merged: dict = {}
        for name in names:
            path = style_path(ROOT, name)
            if path.exists():
                merged = _deep_merge(merged, yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        return merged.get("figures", {}), names[-1]

    if len(profiles) < 2:
        return []
    presets = {project: preset_sizes(project) for project, _ in profiles}
    modes = {key: {role: float(max(sizes, key=sizes.get)) for role, sizes in prof.items()}
             for key, prof in profiles.items()}
    votes: dict[str, Counter] = {}
    for m in modes.values():
        for role, size in m.items():
            votes.setdefault(role, Counter())[size] += 1
    rows = []
    for (project, stem), m in sorted(modes.items()):
        for role, mine in m.items():
            preset, last = presets[project]
            if role in PRESET_KEYS and preset.get(PRESET_KEYS[role]) is not None:
                ref, src = float(preset[PRESET_KEYS[role]]), f"the {last} preset ({PRESET_KEYS[role]})"
            else:
                ref, src = votes[role].most_common(1)[0][0], f"most of the {len(modes)} figures checked"
            if abs(mine - ref) > 0.05:
                rows.append({"project": project, "figure": stem, "n": 0, "severity": "info",
                             "check": "font_size_across_figures",
                             "message": f"{role.replace('_', ' ')}s are mostly {mine:g} pt here; {src} uses {ref:g} pt",
                             "panel": "", "measured": mine, "threshold": ref, "bbox_mm": "[]",
                             "hint": "fine if this figure shrinks text on purpose (its config); otherwise use the "
                                     "preset size so all figures read alike"})
    return rows


# ------------------------------------------------------------ orchestrator ----
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projects", nargs="*", help="project names (default: the storyline compendium)")
    ap.add_argument("--report-only", action="store_true",
                    help="always exit 0 (used by `fa build --preflight`; `fa verify` decides via preflight.mode)")
    ap.add_argument("--worker", help=argparse.SUPPRESS)
    ap.add_argument("--worker-out", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.worker:
        return run_worker(args.worker, Path(args.worker_out))

    projects = args.projects or compendium_projects()
    rows = []
    all_profiles: dict[tuple[str, str], dict] = {}
    checked: dict[str, object] = {}
    for name in projects:
        try:
            p = find_project(ROOT, name)
        except ProjectError as exc:
            print(f"[skip] {exc}")
            continue
        env = build_env()
        env["CONFIG_PATH"] = p.config_rel(ROOT)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "findings.json"
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", name,
                                   "--worker-out", str(out)], cwd=ROOT, env=env, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace")
            if proc.returncode != 0 or not out.exists():
                print(f"[fail] {name}\n{proc.stderr[-1500:]}")
                continue
            payload = json.loads(out.read_text(encoding="utf-8"))
        per_fig = payload["findings"]
        for stem, prof in payload["profiles"].items():
            all_profiles[(name, stem)] = prof
        per_fig.update(check_published_files(p))
        for stem, findings in per_fig.items():
            for n, f in enumerate(findings, 1):
                rows.append({"project": name, "figure": stem, "n": n, **f,
                             "bbox_mm": json.dumps([round(v, 1) for v in f["bbox_mm"]])})
        checked[name] = p
        n_err = sum(1 for fs in per_fig.values() for f in fs if f["severity"] == "error")
        n_warn = sum(1 for fs in per_fig.values() for f in fs if f["severity"] == "warn")
        print(f"[ok] {name}: {n_err} error(s), {n_warn} warning(s)")

    rows += consistency_rows(all_profiles)
    OUT.mkdir(parents=True, exist_ok=True)
    report = OUT / "preflight_findings.csv"
    _write_rows(report, rows)
    # Each project's own findings also go next to its manifests, where
    # `fa verify` picks them up (preflight.mode: report | enforce).
    from fig_atlas import get_config
    for name, p in checked.items():
        _write_rows(get_config(p.config).manifests_root / "preflight.csv", [r for r in rows if r["project"] == name])
    by = {}
    for r in rows:
        by[(r["severity"], r["check"])] = by.get((r["severity"], r["check"]), 0) + 1
    print(f"\nReport: {report.relative_to(ROOT)}  (overlays: {OUT.relative_to(ROOT)}/<project>/)")
    for (sev, chk), n in sorted(by.items()):
        print(f"  {sev:5} {chk:28} {n}")
    if args.report_only:
        return 0
    return 1 if any(r["severity"] == "error" for r in rows) else 0


FIELDS = ["project", "figure", "n", "severity", "check", "message", "panel", "measured", "threshold",
          "bbox_mm", "hint"]


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    sys.exit(main())
