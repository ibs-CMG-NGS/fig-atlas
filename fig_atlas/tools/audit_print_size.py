"""Audit how figures would PRINT on a given page preset.

For each project, runs its real analysis script (same CONFIG_PATH wiring as
.vscode/build_task.ps1) in a subprocess with ``Figure.savefig`` intercepted:
instead of writing files, each figure is measured by
``fig_atlas.print_check.audit_figure`` -- printed width/height, how many pages
tall, smallest printed font and line. Read-only: no output file is touched.

Usage:
    fa audit-print                      # compendium figures (from the storyline)
    fa audit-print --page a4_portrait_normal
    fa audit-print --projects <project>

Writes outputs/print_audit/print_audit_<page>.csv and prints a summary table.
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

import yaml  # noqa: E402

from fig_atlas.page import PageSpec  # noqa: E402



def compendium_pages(storyline: Path | None) -> list[tuple[str, str, int]]:
    """(role, project, figure_no) per compendium page, taken from the same
    parser scripts/compile_storyline_pdf.py uses -- so the audit always
    targets exactly the projects the compendium actually pages (a separate
    hardcoded copy here once went stale when Main Figure 2 moved projects).
    ``storyline`` None: the repository's only storyline."""
    spec = importlib.util.spec_from_file_location("compile_storyline_pdf", Path(__file__).with_name("compile_storyline_pdf.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    story = module.parse_storyline_md(storyline or module.default_storyline())
    return [(f["role"], f["project"], int(f["figure_number"] or 1)) for f in story["figures"]]


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _find_config(project: str) -> Path | None:
    found = sorted((ROOT / "configs").rglob(f"config_{project}.yaml"))
    return found[0] if found else None


def _spec_stem_name(project: str, fig_no: int) -> str | None:
    """Basename of the analysis output a figure spec publishes (source_stem)."""
    found = sorted((ROOT / "figure_specs").rglob(f"figure_{fig_no:02d}_{project}.py"))
    if not found:
        return None
    mod_spec = importlib.util.spec_from_file_location(found[0].stem, found[0])
    module = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(module)
    spec = getattr(module, "SPEC", None)
    return Path(spec.source_stem).name if spec else None


# ---------------------------------------------------------------- worker ----
def run_worker(config_path: Path, page_name: str, out_json: Path) -> int:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    from fig_atlas.print_check import audit_figure

    page = PageSpec.from_dict(_load_yaml(style_path(ROOT, f"page_{page_name}"))["page"])
    thresholds = _load_yaml(style_path(ROOT, "print")).get("print_check", {})
    min_font = float(thresholds.get("min_font_pt", 5.0))
    min_line = float(thresholds.get("min_line_pt", 0.25))

    results: dict[str, dict] = {}

    def fake_savefig(self, fname, *args, **kwargs):
        stem = Path(str(fname)).with_suffix("").name
        if stem not in results:
            # Point sizes and inch geometry are dpi-independent; a low dpi just
            # keeps the measuring draw cheap for very tall figures.
            self.set_dpi(72)
            results[stem] = audit_figure(self, page, min_font, min_line)

    Figure.savefig = fake_savefig
    script = _load_yaml(config_path)["project"]["analysis_script"]
    os.chdir(ROOT)
    sys.argv = [script]
    runpy.run_path(str(ROOT / script), run_name="__main__")
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


# ------------------------------------------------------------ orchestrator ----
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="a4_portrait_narrow")
    ap.add_argument("--projects", nargs="*")
    ap.add_argument("--plan", default=None,
                    help="storyline markdown whose compendium pages to audit (default: the only one)")
    ap.add_argument("--worker", help=argparse.SUPPRESS)
    ap.add_argument("--worker-out", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.worker:
        return run_worker(Path(args.worker), args.page, Path(args.worker_out))

    targets = ([(p, p, None) for p in args.projects] if args.projects
               else compendium_pages(Path(args.plan) if args.plan else None))
    projects = list(dict.fromkeys(proj for _, proj, _ in targets))

    from fig_atlas.projects import build_env
    env = build_env()           # the running interpreter's DLL path, not a conda env inside the project

    per_project: dict[str, dict] = {}
    for proj in projects:
        cfg = _find_config(proj)
        if cfg is None:
            print(f"[skip] no config for {proj}")
            continue
        env["CONFIG_PATH"] = str(cfg.relative_to(ROOT)).replace("\\", "/")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "audit.json"
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--page", args.page,
                 "--worker", str(cfg), "--worker-out", str(out)],
                cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if proc.returncode != 0 or not out.exists():
                print(f"[fail] {proj}\n{proc.stderr[-2000:]}")
                continue
            per_project[proj] = json.loads(out.read_text(encoding="utf-8"))
        print(f"[ok] {proj}: {len(per_project[proj])} figure(s) audited")

    rows = []
    for role, proj, fig_no in targets:
        audits = per_project.get(proj, {})
        if fig_no is not None:
            stem = _spec_stem_name(proj, fig_no)
            items = [(stem, audits[stem])] if stem in audits else []
        else:
            items = list(audits.items())
        for stem, a in items:
            rows.append({"role": role, "project": proj, "stem": stem,
                         **{k: v for k, v in a.items() if not isinstance(v, (list, dict))},
                         "thin_line_kinds": json.dumps(a["thin_line_kinds"]),
                         "smallest_texts": json.dumps(a["smallest_texts"], ensure_ascii=False)})

    out_dir = ROOT / "outputs" / "print_audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"print_audit_{args.page}.csv"
    if rows:
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    print(f"\nPage: {args.page}  (report: {out_csv.relative_to(ROOT)})")
    hdr = f"{'figure':32} {'W x H mm':>15} {'scale':>6} {'pages':>5} {'minFont':>8} {'<min':>5} {'minLine':>8} {'<min':>5}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['role'][:32]:32} {r['fig_width_mm']:>6.0f} x {r['fig_height_mm']:<6.0f} "
              f"{r['scale_to_page_width']:>6.2f} {r['pages_needed']:>5} "
              f"{r['min_font_printed_pt']:>8} {r['n_texts_below_min']:>5} "
              f"{r['min_line_printed_pt']:>8} {r['n_lines_below_min']:>5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
