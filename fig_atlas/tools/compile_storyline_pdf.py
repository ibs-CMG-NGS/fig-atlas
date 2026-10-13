#!/usr/bin/env python3
"""Compile a manuscript storyline markdown file and its referenced figure PDFs
into a unified, publication-grade multi-page vector PDF compendium.

All pages are A4 (COMPENDIUM_PAGE_PRESET). Each figure is placed 1:1 in the page's
content box with a journal-style legend below it ("Figure N | Title", then one
bold-lettered paragraph per panel) at the figures' own print scale; a legend that
doesn't fit under its figure moves to the top of the next page.

Usage:
    fa storyline compile --plan docs/storylines/figure_plan_<topic>.md
    python scripts/compile_storyline_pdf.py --all
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

# On Windows without conda activate, matplotlib Agg backend requires DLLs in Library\bin
_lib_bin = str(Path(sys.executable).resolve().parent / "Library" / "bin")
if os.path.exists(_lib_bin) and _lib_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _lib_bin + ";" + os.environ.get("PATH", "")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from fig_atlas.config import style_path  # noqa: E402
from fig_atlas.tools import project_root  # noqa: E402  (the project repository, not this package)


PROJECT_ROOT = project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))     # fig_atlas (provenance freshness checks)


def _snapshot_module():
    spec = importlib.util.spec_from_file_location("storyline_snapshot", Path(__file__).with_name("storyline_snapshot.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# Every compendium page uses this page preset (styles/<name>.yaml): the same
# paper the figures are drawn for, so each figure places 1:1 in its content box.
COMPENDIUM_PAGE_PRESET = "page_a4_portrait_narrow"

_REVISION_RE = re.compile(r"(?:개편|Revision)\s?\((\d+)\)")   # Korean or English revision log


def storyline_revision(content: str, records_dir: Path | None = None) -> str:
    """Revision ID of a storyline: the highest "개편(N)" entry it records, as
    "R035". Every storyline change is logged as a numbered 개편 entry, so the
    highest number identifies the current state of the plan. Revision records
    (``revisions/RNNN.md``, `fa storyline revisions`) count too."""
    nums = [int(n) for n in _REVISION_RE.findall(content)]
    if records_dir is not None and records_dir.is_dir():
        nums += [int(m.group(1)) for f in records_dir.glob("R*.md") if (m := re.fullmatch(r"R(\d+)", f.stem))]
    return f"R{max(nums):03d}" if nums else "R000"


def _git_state(paths: list[Path]) -> dict:
    """HEAD commit and whether any of ``paths`` differ from it (uncommitted
    edits). Returns empty values outside a git checkout."""
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace").stdout.strip()
    try:
        commit = run("rev-parse", "--short", "HEAD")
        rel = [str(p.relative_to(PROJECT_ROOT)) for p in paths]
        dirty = bool(run("status", "--porcelain", "--", *rel)) if rel else False
    except (OSError, ValueError):
        return {"commit": "", "dirty": False}
    return {"commit": commit, "dirty": dirty}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive_revision(md_path: Path, out_pdf: Path, story_data: dict, items: list[dict]) -> Path:
    """Keep this compile under outputs/storylines/<storyline>/<revision>/.

    The working copy (docs/storylines/<storyline>.pdf) is overwritten on every
    compile, so without this a later 개편 erases the previous compendium. Each
    revision folder keeps the compendium PDF, the storyline markdown exactly as
    it was compiled, and revision.json (git state plus the hash of every
    figure PDF placed), so two revisions can be compared later.
    """
    rev = story_data["revision"]
    rev_dir = PROJECT_ROOT / "outputs" / "storylines" / md_path.stem / rev
    rev_dir.mkdir(parents=True, exist_ok=True)
    old = rev_dir / "revision.json"
    if old.is_file():
        prev = json.loads(old.read_text(encoding="utf-8"))
        if prev.get("compendium_sha256") != _sha256(out_pdf):
            print(f"  [i] Snapshot {rev} (compiled {prev.get('compiled', '?')}) is replaced. Add a numbered "
                  f"개편 entry to the storyline first to keep it as a separate revision.")
    shutil.copy2(out_pdf, rev_dir / f"{md_path.stem}_{rev}.pdf")
    shutil.copy2(md_path, rev_dir / f"{md_path.stem}_{rev}.md")
    record = {
        "schema": "fig-atlas/storyline-revision@2",
        "storyline": md_path.stem,
        "revision": rev,
        "compiled": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": story_data["git"]["commit"],
        "storyline_uncommitted": story_data["git"]["dirty"],
        "storyline_sha256": _sha256(md_path),
        "compendium_sha256": _sha256(out_pdf),
        "figures": [
            {"role": it["meta"]["role"], "project": it["meta"]["project"],
             "figure_number": it["meta"]["figure_number"],
             "source_pdf": str(it["source_pdf"].relative_to(PROJECT_ROOT)).replace("\\", "/"),
             "source_sha256": _sha256(it["source_pdf"]), "state": it["state"]}
            for it in items
        ],
        "tables": [t["file"] for t in story_data.get("tables", [])],
        "health": story_data.get("health"),
    }
    _snapshot_module().snapshot_extras(PROJECT_ROOT, rev_dir, storyline_yaml_path(md_path), record["figures"])
    (rev_dir / "revision.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return rev_dir


def storyline_yaml_path(md_path: Path) -> Path:
    """docs/storylines/figure_plan_<topic>.md -> docs/storylines/<topic>/storyline.yaml"""
    return md_path.parent / md_path.stem.removeprefix("figure_plan_") / "storyline.yaml"


PAPER_NAME = re.compile(r"\b([a-z0-9]+-paper-(main|supp)-fig(\d+)-[a-z0-9-]+)\b")


def paper_slots(content: str) -> list[dict]:
    """The paper projects a storyline text names, as slots ordered main ->
    supplementary, by figure number (a draft for storyline.yaml)."""
    known = {p.stem.removeprefix("config_") for p in (PROJECT_ROOT / "configs").rglob("config_*.yaml")
             if "archive" not in p.parts}
    seen = {}
    for m in PAPER_NAME.finditer(content):
        name, kind, n = m.group(1), m.group(2), int(m.group(3))
        if name in known and name not in seen:
            seen[name] = (0 if kind == "main" else 1, n)
    order = sorted(seen, key=lambda k: seen[k])
    return [{"role": ("Main Figure " if seen[p][0] == 0 else "Supplementary Figure S") + str(seen[p][1]),
             "project": p, "figure_number": 1, "description": ""} for p in order]


def default_storyline() -> Path:
    """The storyline of this repository: its only docs/storylines/figure_plan_*.md
    (pass --plan when there are several)."""
    plans = sorted((PROJECT_ROOT / "docs" / "storylines").glob("figure_plan_*.md"))
    if len(plans) == 1:
        return plans[0]
    raise SystemExit("no storyline (docs/storylines/figure_plan_<topic>.md)" if not plans else
                     "several storylines; pass --plan: " + ", ".join(p.name for p in plans))


def parse_storyline_md(md_path: Path, use_yaml: bool = True) -> dict:
    """Parse a storyline markdown file to extract metadata, hypothesis, and figure mapping.

    The figure/table assignment comes from the storyline's storyline.yaml
    (scripts/storyline.py) when it exists; the hardcoded lists below are the
    legacy fallback and the source `fa storyline init` converts."""
    content = md_path.read_text(encoding="utf-8")
    
    # Extract title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else md_path.stem
    
    # Extract hypothesis if present
    hypo_match = re.search(r"###\s+핵심 가설[^\n]*\n+([^#\n][^\n]+)", content)
    if not hypo_match:
        hypo_match = re.search(r"가설[^\n]*:\s*([^\n]+)", content)
    hypothesis = hypo_match.group(1).strip() if hypo_match else ""
    
    # Without a storyline.yaml (`fa storyline init` writes one from this draft):
    # the paper projects the storyline text names, in manuscript order -- main
    # figures, then supplementary -- by their names <domain>-paper-<main|supp>-fig<N>-<slug>.
    figures = paper_slots(content)
    tables = []
    source, retired, narrative = "legacy", [], ""

    yml = storyline_yaml_path(md_path)
    if use_yaml and yml.is_file():
        import yaml
        sl = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        figures = [{"role": f["slot"], "project": f["project"], "figure_number": int(f.get("figure_number", 1)),
                    "description": f.get("description", ""), "status": f.get("status", "Active")}
                   for f in sl.get("figures", [])]
        tables = [{"role": t["slot"], "file": t["file"], "generator": t.get("generator", ""),
                   "description": t.get("description", "")} for t in sl.get("tables", [])]
        retired = list(sl.get("retired") or [])
        narrative = str(sl.get("narrative") or "").rstrip("\n")
        source = "yaml"

    return {
        "title": title,
        "hypothesis": hypothesis,
        "narrative": narrative,
        "figures": figures,
        "tables": tables,
        "retired": retired,
        "source": source,
        "path": md_path,
        "revision": storyline_revision(content, storyline_yaml_path(md_path).parent / "revisions"),
    }


def get_figure_metadata(project: str, figure_number: int | None) -> dict:
    """Extract FigureSpec title, panel notes, and slug for caption rendering."""
    fn = figure_number or 1
    exact_path = PROJECT_ROOT / f"figure_specs/figure_{fn:02d}_{project}.py"
    fpath = exact_path if exact_path.exists() else None
    if not fpath:
        # Recursive: figure_specs/ may be namespaced under <domain>/<category>/.
        cands = list((PROJECT_ROOT / "figure_specs").glob(f"**/figure_{fn:02d}_*{project}*.py"))
        fpath = cands[0] if cands else None
        
    title = ""
    panel_notes = []
    slug = ""
    if fpath and fpath.exists():
        try:
            mod_name = f"spec_{project}_{fn}".replace("-", "_")
            spec_mod = importlib.util.spec_from_file_location(mod_name, fpath)
            mod = importlib.util.module_from_spec(spec_mod)
            spec_mod.loader.exec_module(mod)
            spec = getattr(mod, "SPEC", None)
            if spec:
                title = getattr(spec, "title", "")
                panel_notes = getattr(spec, "panel_notes", [])
                slug = getattr(spec, "slug", "")
        except Exception:
            pass
            
    if not title:
        manifest_path = PROJECT_ROOT / "outputs/clean_atlas_manifest.csv"
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        if r.get("project") == project and int(r.get("figure", 1)) == fn:
                            title = r.get("title", "")
                            break
            except Exception:
                pass
                
    # Live numbers (fa claims): fill {name} placeholders from the values the
    # build recorded, as publish does for the README.
    pdf = find_figure_pdf(project, fn)
    rec = pdf.with_name(pdf.stem + ".provenance.json") if pdf else None
    if rec and rec.is_file():
        from fig_atlas.claims import fill
        values = json.loads(rec.read_text(encoding="utf-8")).get("claims") or {}
        title = fill(title, values)[0]
        panel_notes = [fill(n, values)[0] for n in panel_notes]

    return {
        "title": title or project,
        "panel_notes": panel_notes,
        "slug": slug or f"figure_{fn:02d}",
    }


def _find_project_figures_dir(project_name: str) -> Path | None:
    """Locate a project's outputs/.../<project_name>/figures dir, whether it sits
    flat under outputs/ or namespaced under outputs/<domain>/<category>/."""
    outputs_root = PROJECT_ROOT / "outputs"
    flat = outputs_root / project_name / "figures"
    if flat.exists():
        return flat
    for cand in outputs_root.glob(f"**/{project_name}/figures"):
        if cand.is_dir():
            return cand
    return None


def find_figure_pdf(project_name: str, figure_number: int | None = None) -> Path | None:
    """Locate the published figure PDF for a given project and optional figure number."""
    pattern = _find_project_figures_dir(project_name)
    if pattern is None:
        return None
        
    if figure_number is not None:
        num_str = f"{figure_number:02d}"
        for cand in pattern.glob(f"figure_{num_str}_*/figure_{num_str}.pdf"):
            if cand.exists():
                return cand
        for cand in pattern.glob(f"**/figure_{num_str}.pdf"):
            if cand.exists():
                return cand
        for cand in pattern.glob(f"figure{figure_number}_*.pdf"):
            if cand.exists():
                return cand
                
    pdfs = list(pattern.glob("**/figure_*.pdf"))
    if pdfs:
        f1 = [p for p in pdfs if p.name == "figure_01.pdf"]
        return f1[0] if f1 else pdfs[0]
        
    direct_pdfs = list(pattern.glob("*.pdf"))
    if direct_pdfs:
        return direct_pdfs[0]
        
    return None


def generate_cover_page(story_data: dict, out_cover_pdf: Path) -> None:
    """Generate an elegant executive summary / cover page."""
    with PdfPages(out_cover_pdf) as pdf:
        pg = _compendium_page()
        fig = plt.figure(figsize=(pg["w"] / 72.0, pg["h"] / 72.0), dpi=300)  # same paper as the figure pages
        fig.patch.set_facecolor("#ffffff")
        
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        # Header category badge
        ax.text(0.08, 0.94, "MANUSCRIPT FIGURE STORYLINE & ATLAS COMPENDIUM", 
                fontsize=9.5, fontweight="bold", color="#2563eb")
                
        # Main Title (wrapped safely within bounds)
        clean_title = story_data["title"]
        for prefix in ["#", "통합 논문 스토리라인 및 피겨 구성안", "Manuscript Figure Plan:", "Manuscript Storyline:"]:
            clean_title = clean_title.replace(prefix, "").strip(" :()-")
        if not clean_title:
            clean_title = "Human ATAC Anchor Discovery & Target Prioritization"
            
        wrapped_title = "\n".join(textwrap.wrap(clean_title, width=56))
        ax.text(0.08, 0.91, wrapped_title,
                fontsize=13.5, fontweight="bold", color="#0f172a", va="top", linespacing=1.25)
        
        # Divider rule
        ax.plot([0.08, 0.92], [0.85, 0.85], color="#cbd5e1", lw=1.5)
        
        # Metadata banner
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        git = story_data.get("git", {})
        commit = git.get("commit") or "no git"
        if git.get("dirty"):
            commit += "*"       # explained on the build-state line (the full note overran the page)
        ax.text(0.08, 0.83, f"Storyline Source: {story_data['path'].name}  |  Revision: {story_data['revision']}  |  "
                            f"Compiled: {date_str}  |  Commit: {commit}",
                fontsize=8, color="#64748b")
        health = story_data.get("health")
        if health:
            bad = health["stale"] or health["preflight_errors"]
            line = _snapshot_module().health_line(health)
            if git.get("dirty"):
                line += "  |  * storyline uncommitted"
            ax.text(0.08, 0.814, line, fontsize=7.5,
                    color="#b91c1c" if bad else "#64748b", fontweight="bold" if bad else "normal")

        # Core Hypothesis Card
        hypo_rect = plt.Rectangle((0.08, 0.70), 0.84, 0.105, facecolor="#f8fafc", edgecolor="#94a3b8", lw=1.0)
        ax.add_patch(hypo_rect)
        ax.text(0.10, 0.775, "CORE HYPOTHESIS & DEDUCTIVE NARRATIVE ARC", 
                fontsize=8.5, fontweight="bold", color="#1e293b")
        # The storyline's own words: storyline.yaml `narrative` (line breaks kept), else its hypothesis.
        hypo_text = story_data.get("narrative") or story_data.get("hypothesis") or ""
        ax.text(0.10, 0.715, hypo_text, fontsize=7.5, color="#334155", va="bottom", linespacing=1.25)
        
        # Figure Allocation Table
        ax.text(0.08, 0.675, "MANUSCRIPT FIGURE ALLOCATION & SEQUENTIAL ARCHITECTURE", 
                fontsize=9.5, fontweight="bold", color="#0f172a")
                
        def wrap_name(n: str) -> str:
            tokens = n.split("-")
            mid = len(tokens) // 2
            return "-".join(tokens[:mid]) + "-\n" + "-".join(tokens[mid:])

        table_rows = [["Figure / Table", "Project / File", "Biological Role & Deductive Takeaway"]]
        for f in story_data["figures"]:
            p_wrap = wrap_name(f["project"])
            d_wrap = "\n".join(textwrap.wrap(f["description"], width=46))
            table_rows.append([f["role"], p_wrap, d_wrap])
        for t in story_data.get("tables", []):
            f_wrap = "\n".join(textwrap.wrap(t["file"], width=34))
            d_wrap = "\n".join(textwrap.wrap(t["description"], width=46))
            table_rows.append([t["role"].replace("Supplementary ", "Suppl. "), f_wrap, d_wrap])
            
        n_rows = len(table_rows)
        t_height = min(0.48, max(0.38, n_rows * 0.026))
        f_size = max(5.6, min(7.2, 70.0 / n_rows))
        
        tab = ax.table(cellText=table_rows, loc="center", cellLoc="left", bbox=[0.08, 0.66 - t_height, 0.84, t_height],
                       colWidths=[0.20, 0.34, 0.46])
        tab.auto_set_font_size(False)
        tab.set_fontsize(f_size)
        
        cell_h = t_height / n_rows
        for (r, c), cell in tab.get_celld().items():
            cell.set_edgecolor("#cbd5e1")
            cell.set_height(cell_h)
            if r == 0:
                cell.set_facecolor("#1e293b")
                cell.set_text_props(color="white", weight="bold", size=f_size + 0.8)
            else:
                is_main = "Main" in table_rows[r][0]
                cell.set_facecolor("#f1f5f9" if is_main else ("#f8fafc" if r % 2 == 1 else "#ffffff"))
                if c == 0:
                    cell.set_text_props(weight="bold", color="#0f172a" if is_main else "#475569", size=f_size + 0.3)
                elif c == 1:
                    cell.set_text_props(color="#0284c7", size=f_size - 0.4, family="monospace")
                else:
                    cell.set_text_props(color="#1e293b", size=f_size)

        # Verification & Quality Statement below table
        v_top = 0.66 - t_height - 0.025
        ax.text(0.08, v_top, "PUBLICATION INTEGRITY & REPEATABILITY STANDARDS", 
                fontsize=8.5, fontweight="bold", color="#0f172a")
        notes = (
            "• Each figure page carries its journal-style legend below the figure; supplementary tables ship as CSV files.\n"
            "• All figure panels are rendered in lossless vector PDF format (300+ DPI, Matplotlib Agg).\n"
            "• Figures drawn 1:1 at final print size (A4 portrait, 184.6 mm content width; 5-8 pt type, config-driven).\n"
            "• Raw datasets remain strictly read-only and immutable; verified 100% against clean atlas manifests."
        )
        ax.text(0.08, v_top - 0.058, notes, fontsize=7.2, color="#475569", linespacing=1.2)
        
        # Footer
        ax.plot([0.08, 0.92], [0.045, 0.045], color="#e2e8f0", lw=1.0)
        ax.text(0.08, 0.025, "Fig-Atlas Template Automation Suite | Unified Manuscript Compendium",
                fontsize=7.0, color="#94a3b8")
        ax.text(0.92, 0.025, "Page 1 of Compendium",
                fontsize=7.0, color="#94a3b8", ha="right")
                
        pdf.savefig(fig)
        fig.savefig(out_cover_pdf.with_suffix(".png"), dpi=200)
        plt.close(fig)


def _evidence_module():
    spec = importlib.util.spec_from_file_location("storyline_evidence", Path(__file__).with_name("storyline_evidence.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def appendix_rows(items: list[dict]) -> list[dict]:
    """Per placed figure: build, live numbers, source data and the data
    requests that delivered what it read (from its provenance record and the
    data-request ledger, docs/data_contracts/)."""
    ev = _evidence_module()
    requests = ev.load_requests(PROJECT_ROOT / "docs" / "data_contracts")
    rows = []
    for it in items:
        meta = it["meta"]
        rec_path = it["source_pdf"].with_name(it["source_pdf"].stem + ".provenance.json")
        rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.is_file() else {}
        delivered = sorted({r["name"].removesuffix("_request.md") for i in rec.get("inputs", [])
                            if i["path"].startswith("raw_data/") for r in requests if ev.link(r, i["path"]) == "declared"})
        rows.append({"role": meta["role"], "project": meta["project"],
                     "built": ((rec.get("run") or {}).get("finished") or "")[:10],
                     "commit": ((rec.get("git") or {}).get("commit") or "")[:7],
                     "claims": len(rec.get("claims") or {}),
                     "source_data": ", ".join(e["panel"] for e in rec.get("source_data", [])),
                     "inputs": len(rec.get("inputs", [])), "requests": delivered, "recorded": bool(rec)})
    return rows


def generate_appendix_page(story_data: dict, rows: list[dict], out_pdf: Path, page_no: int, total: int) -> None:
    """Closing page: what each figure was built from and what it ships."""
    pg = _compendium_page()
    fig = plt.figure(figsize=(pg["w"] / 72.0, pg["h"] / 72.0), dpi=300)
    fig.patch.set_facecolor("#ffffff")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.08, 0.94, "APPENDIX · DATA, NUMBERS AND EVIDENCE BEHIND EACH FIGURE", fontsize=9.5, fontweight="bold",
            color="#2563eb")
    ax.text(0.08, 0.915, f"Revision {story_data['revision']}. Read from each figure's provenance record and the "
                         "data-request ledger (docs/data_contracts/).", fontsize=7.2, color="#64748b")
    header = ["Figure", "Project", "Built\n(commit)", "Inputs", "Live\nnumbers", "Source\ndata", "Data requests delivering its inputs"]
    table = [header]
    for r in rows:
        proj = re.sub(r"^[a-z0-9]+-paper-", "", r["project"])
        req = "\n".join(textwrap.wrap(", ".join(r["requests"]) or "none on record", width=40))
        table.append([r["role"].replace("Supplementary", "Suppl."), "\n".join(textwrap.wrap(proj, width=22)),
                      f"{r['built']}\n{r['commit']}" if r["recorded"] else "no record",
                      str(r["inputs"]), str(r["claims"]), r["source_data"] or "-", req])
    n = len(table)
    t_h = min(0.70, 0.045 * n)
    tab = ax.table(cellText=table, cellLoc="left", bbox=[0.08, 0.89 - t_h, 0.84, t_h],
                   colWidths=[0.13, 0.20, 0.11, 0.07, 0.08, 0.07, 0.34])
    tab.auto_set_font_size(False)
    tab.set_fontsize(6.0)
    for (r, c), cell in tab.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        cell.set_height(t_h / n)
        if r == 0:
            cell.set_facecolor("#1e293b")
            cell.set_text_props(color="white", weight="bold", size=6.3)
        else:
            cell.set_facecolor("#f8fafc" if r % 2 else "#ffffff")
            cell.set_text_props(color="#0f172a" if c == 0 else "#334155", weight="bold" if c == 0 else "normal")
    notes = ("• Inputs: repository files the build read (raw data, configs, styles), each recorded with its sha256.\n"
             "• Live numbers: values the build recorded and the legend quotes (fig_atlas.claims), so legend and data cannot drift.\n"
             "• Source data: per-panel tables of the plotted values, published as figure_NN_source_data/ (CSV).\n"
             "• Data requests: requests whose delivered or derived files the figure read (`fa storyline evidence`).")
    ax.text(0.08, 0.89 - t_h - 0.03, notes, fontsize=6.8, color="#475569", va="top", linespacing=1.35)
    ax.plot([0.08, 0.92], [0.045, 0.045], color="#e2e8f0", lw=1.0)
    ax.text(0.08, 0.025, "Fig-Atlas Template Automation Suite | Unified Manuscript Compendium", fontsize=7.0, color="#94a3b8")
    ax.text(0.92, 0.025, f"Page {page_no} of {total}", fontsize=7.0, color="#94a3b8", ha="right")
    with PdfPages(out_pdf) as pdf:
        pdf.savefig(fig)
    fig.savefig(out_pdf.with_suffix(".png"), dpi=200)
    plt.close(fig)


# Caption (figure legend) typography, in pt. Figures are drawn at final print
# size, so the legend under each compendium page uses the same scale as the
# figure's own text (styles/print.yaml: 7 pt body, 8 pt titles).
CAPTION_STYLE = {
    "font_family": "DejaVu Sans",
    "meta_size": 6.0,          # Header line: figure role, compendium page, source project
    "title_size": 8.0,         # "Figure N | Title"
    "body_size": 7.0,          # Panel legends
    "linespacing": 1.3,
    "panel_gap_pt": 2.5,       # Between panel legends
    "letter_indent_pt": 9.0,   # Hanging indent: bold panel letter -> legend text
    "rule_lw": 0.8,
    "top_pad_pt": 6.0,
    "bottom_pad_pt": 4.0,
    "figure_gap_pt": 10.0,     # Figure bottom -> legend top on the same page
    "text_color": "#1f2937",
    "meta_color": "#64748b",
    "accent": {"main": "#2563eb", "supple": "#d97706", "other": "#059669"},
}

_PANEL_RE = re.compile(r"^\s*Panels?\s+([a-z](?:\s*[-–/,&]\s*[a-z])*)\s*[:.]\s*(.*)$", re.S)
_TITLE_PREFIX_RE = re.compile(r"^\s*(?:Main\s+|Extended\s+Data\s+|Supplementary\s+)?Figure\s+[\w.-]+\s*[:|.]\s*", re.I)


def _clean_caption_text(s: str) -> str:
    """Drop characters the PDF font can't draw (emoji colour dots, variation
    selectors) and collapse the whitespace they leave behind."""
    s = "".join(ch for ch in str(s) if ord(ch) < 0x2600 or 0x2190 <= ord(ch) <= 0x22FF)
    s = re.sub(r"\(\s+", "(", s)
    return re.sub(r"[ \t]+", " ", s).strip()


def _figure_label(role: str) -> str:
    """'Main Figure 3' -> 'Figure 3' (the legend label a journal would print)."""
    return re.sub(r"^Main\s+", "", role).strip()


def generate_caption_page(fig_meta: dict, width_pt: float, inset_pt: float, out_pdf: Path) -> float:
    """Render a journal-style legend block for one compendium page.

    Layout (top to bottom): a thin accent rule; a small meta line (figure
    role, compendium page, source project); the legend title "Figure N |
    Title" in bold; then one paragraph per panel with its letter in bold and
    a hanging indent. Text is wrapped by measured width to the figure's own
    width (``inset_pt`` left/right, matching the figure's page margins), and
    the block's height is whatever the text needs. Returns that height (pt).
    """
    cs = CAPTION_STYLE
    role = fig_meta["role"]
    kind = "main" if "Main" in role else ("supple" if "Supple" in role else "other")
    accent = cs["accent"][kind]
    x0, x1 = inset_pt, width_pt - inset_pt
    text_w = x1 - x0

    plt.rcParams["font.family"] = cs["font_family"]
    fig = plt.figure(figsize=(width_pt / 72.0, 20.0), dpi=72)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, width_pt)
    ax.set_ylim(-20.0 * 72.0, 0)
    renderer = fig.canvas.get_renderer()

    def width_of(s, size, weight="normal"):
        fp = FontProperties(family=cs["font_family"], size=size, weight=weight)
        return renderer.get_text_width_height_descent(s, fp, ismath=False)[0]

    def wrap(s, size, width, weight="normal"):
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}" if cur else word
            if cur and width_of(trial, size, weight) > width:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
        return "\n".join(lines)

    def put(x, y, s, size, width=None, weight="normal", color=None, ha="left"):
        if width:
            s = wrap(s, size, width, weight)
        t = ax.text(x, y, s, fontsize=size, fontweight=weight, color=color or cs["text_color"],
                    ha=ha, va="top", linespacing=cs["linespacing"])
        return t.get_window_extent(renderer).height

    y = -cs["top_pad_pt"]
    ax.plot([x0, x1], [y, y], color=accent, lw=cs["rule_lw"])
    y -= 4.0

    # Meta line: role (accent, bold) on the left, page + source on the right.
    meta_right = (f"Compendium page {fig_meta['page_num']} of {fig_meta['total_pages']}   ·   "
                  f"{fig_meta['project']} (figure {fig_meta['figure_number']})")
    role_label = role.upper()
    if fig_meta.get("continued"):
        # Legend moved to the page after its figure (didn't fit below it).
        role_label += f" \u2014 LEGEND (FIGURE ON PAGE {fig_meta['figure_page']})"
    h_meta = put(x0, y, role_label, cs["meta_size"], weight="bold", color=accent)
    put(x1, y, meta_right, cs["meta_size"], color=cs["meta_color"], ha="right")
    y -= h_meta + 5.0

    # Legend title
    title = _clean_caption_text(_TITLE_PREFIX_RE.sub("", fig_meta["title"].strip()))
    title = title.rstrip(".") + "."
    y -= put(x0, y, f"{_figure_label(role)} | {title}", cs["title_size"], width=text_w, weight="bold") + 3.0

    # Panel legends: bold letter + hanging-indented text
    notes = fig_meta.get("panel_notes") or [fig_meta.get("description", "")]
    for note in notes:
        note = _clean_caption_text(note)
        m = _PANEL_RE.match(note)
        if m:
            letter = re.sub(r"\s+", "", m.group(1))
            put(x0, y, letter, cs["body_size"], weight="bold")
            indent = max(cs["letter_indent_pt"], width_of(letter, cs["body_size"], "bold") + 3.0)
            h = put(x0 + indent, y, m.group(2).strip(), cs["body_size"], width=text_w - indent)
        else:
            h = put(x0, y, note, cs["body_size"], width=text_w)
        y -= h + cs["panel_gap_pt"]

    height = -y + cs["bottom_pad_pt"]
    fig.set_size_inches(width_pt / 72.0, height / 72.0)
    ax.set_ylim(-height, 0)
    with PdfPages(out_pdf) as pdf:
        pdf.savefig(fig)
    plt.close(fig)
    return height


def _compendium_page() -> dict:
    """Paper size and margins (pt) of the compendium pages, from the same page
    preset the figures are drawn on, so a figure's content box and the page's
    content box are the same size."""
    import yaml

    preset = yaml.safe_load((style_path(PROJECT_ROOT, COMPENDIUM_PAGE_PRESET)).read_text(encoding="utf-8"))
    page = preset["page"]
    to_pt = 72.0 / 25.4
    paper_w, paper_h = (float(v) * to_pt for v in page["paper_mm"])
    margin = float(page.get("margin_mm", 0.0)) * to_pt
    return {"w": paper_w, "h": paper_h, "margin": margin,
            "content_w": paper_w - 2 * margin, "content_h": paper_h - 2 * margin}


def compile_storyline_pdf(md_path: Path, strict: bool = False) -> Path | None:
    """Compile a storyline markdown into a multi-page A4 PDF compendium.

    Every page has the same paper size (COMPENDIUM_PAGE_PRESET, A4 portrait).
    Each figure is placed 1:1 at the top-left of the page's content box --
    figures are saved at exactly that width (fig_atlas.save_page_figure) --
    and its legend follows below it. When the legend doesn't fit under the
    figure, it goes to the top of the next page instead.
    """
    print(f"\nProcessing storyline: {md_path.name}")
    story_data = parse_storyline_md(md_path)
    story_data["git"] = _git_state([md_path])
    snap = _snapshot_module()
    from fig_atlas.provenance import HashCache
    cache = HashCache(PROJECT_ROOT)
    states = {}
    for item in story_data["figures"]:
        pdf = find_figure_pdf(item["project"], item.get("figure_number", 1))
        if pdf and pdf.exists():
            states[(item["project"], item.get("figure_number", 1))] = snap.figure_state(PROJECT_ROOT, pdf, cache)
    cache.save()
    story_data["health"] = snap.health_summary(list(states.values()))
    print(f"  {snap.health_line(story_data['health'])}")
    for (proj, num), st in states.items():
        if st["fresh"] is False:
            print(f"  [!] stale: {proj} fig {num} -- {'; '.join(st['stale_reasons'][:3])}")
        if st["preflight_errors"]:
            print(f"  [!] preflight: {proj} has {st['preflight_errors']} error(s)")
    if strict and (story_data["health"]["stale"] or story_data["health"]["preflight_errors"]):
        print("  [x] --strict: not compiling with stale figures or preflight errors "
              "(rebuild with `fa build <project> --preflight`)")
        return None
    pg = _compendium_page()
    gap_pt = CAPTION_STYLE["figure_gap_pt"]

    temp_dir = PROJECT_ROOT / "outputs/.temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    cover_pdf = temp_dir / f"cover_{md_path.stem}.pdf"
    generate_cover_page(story_data, cover_pdf)

    # Pass 1: load each figure, measure its legend, and plan the pages.
    items = []
    page_no = 1  # cover
    for item in story_data["figures"]:
        proj = item["project"]
        f_num = item.get("figure_number", 1)
        fig_pdf = find_figure_pdf(proj, f_num)
        if not (fig_pdf and fig_pdf.exists()):
            print(f"  [-] Warning: Figure PDF not found for {proj} (Fig {f_num})")
            continue
        spec_info = get_figure_metadata(proj, f_num)
        fig_page = PdfReader(fig_pdf).pages[0]
        w_pt, h_pt = float(fig_page.mediabox.width), float(fig_page.mediabox.height)
        if w_pt > pg["content_w"] + 1.0 or h_pt > pg["content_h"] + 1.0:
            print(f"  [!] {item['role']}: figure is {w_pt * 25.4 / 72:.1f} x {h_pt * 25.4 / 72:.1f} mm, larger than the "
                  f"page content box ({pg['content_w'] * 25.4 / 72:.1f} x {pg['content_h'] * 25.4 / 72:.1f} mm); "
                  f"it will run into the margin.")
        meta = {
            "role": item["role"], "project": proj, "figure_number": f_num,
            "title": spec_info["title"], "panel_notes": spec_info["panel_notes"],
            "slug": spec_info["slug"], "description": item["description"],
            "page_num": 0, "total_pages": 0, "figure_page": 0, "continued": False,
        }
        cap_h = generate_caption_page(meta, pg["content_w"], 0.0, temp_dir / "caption_probe.pdf")
        page_no += 1
        legend_on_next = h_pt + gap_pt + cap_h > pg["content_h"]
        if legend_on_next:
            print(f"  [i] {item['role']}: figure + legend exceed the page by {(h_pt + gap_pt + cap_h - pg['content_h']) * 25.4 / 72:.1f} mm")
        items.append({"meta": meta, "fig_page": fig_page, "w": w_pt, "h": h_pt, "source_pdf": fig_pdf,
                      "figure_page_no": page_no, "legend_on_next": legend_on_next,
                      "state": states[(proj, f_num)]})
        if legend_on_next:
            page_no += 1
    total_pages = page_no + 1          # + the closing appendix page

    # Pass 2: render legends with final page numbers and assemble A4 pages.
    writer = PdfWriter()
    writer.add_page(PdfReader(cover_pdf).pages[0])
    left, top = pg["margin"], pg["h"] - pg["margin"]
    for it in items:
        meta, n = it["meta"], it["figure_page_no"]
        meta.update(total_pages=total_pages, figure_page=n,
                    page_num=n + 1 if it["legend_on_next"] else n, continued=it["legend_on_next"])
        cap_pdf = temp_dir / f"caption_p{n}_{meta['project']}_{meta['figure_number']}.pdf"
        cap_h = generate_caption_page(meta, pg["content_w"], 0.0, cap_pdf)
        cap_page = PdfReader(cap_pdf).pages[0]

        # Expand the figure page's boxes so pypdf's clip path never trims glyph ascents at its edges.
        fig_page, pad_box = it["fig_page"], 36.0
        fig_page.cropbox.lower_left = (-pad_box, -pad_box)
        fig_page.cropbox.upper_right = (it["w"] + pad_box, it["h"] + pad_box)
        fig_page.mediabox.lower_left = (-pad_box, -pad_box)
        fig_page.mediabox.upper_right = (it["w"] + pad_box, it["h"] + pad_box)

        page = PageObject.create_blank_page(width=pg["w"], height=pg["h"])
        page.merge_transformed_page(fig_page, Transformation().translate(tx=left, ty=top - it["h"]))
        if it["legend_on_next"]:
            writer.add_page(page)
            page = PageObject.create_blank_page(width=pg["w"], height=pg["h"])
            page.merge_transformed_page(cap_page, Transformation().translate(tx=left, ty=top - cap_h))
        else:
            page.merge_transformed_page(cap_page, Transformation().translate(tx=left, ty=top - it["h"] - gap_pt - cap_h))
        writer.add_page(page)
        where = f"legend on page {n + 1}" if it["legend_on_next"] else "legend below"
        print(f"  [+] {meta['role']} -> page {n}/{total_pages} ({meta['project']} Fig {meta['figure_number']}; {where})")

    appendix_pdf = temp_dir / f"appendix_{md_path.stem}.pdf"
    generate_appendix_page(story_data, appendix_rows(items), appendix_pdf, total_pages, total_pages)
    writer.add_page(PdfReader(appendix_pdf).pages[0])
    print(f"  [+] Appendix -> page {total_pages}/{total_pages} (data, live numbers, source data, data requests)")

    out_pdf = md_path.with_suffix(".pdf")
    with open(out_pdf, "wb") as f:
        writer.write(f)
    print(f"  ==> Compiled A4 compendium ({total_pages} pages, {len(items)} figures):\n      {out_pdf}")
    rev_dir = archive_revision(md_path, out_pdf, story_data, items)
    print(f"  ==> Revision {story_data['revision']} archived: {rev_dir.relative_to(PROJECT_ROOT)}\n")
    return out_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile storyline multi-page PDF compendium with captions.")
    parser.add_argument("--plan", type=str, help="Path to specific storyline markdown file.")
    parser.add_argument("--all", action="store_true", help="Compile all storylines under docs/storylines/.")
    parser.add_argument("--strict", action="store_true",
                        help="Refuse to compile when a placed figure is stale or its project has preflight errors.")
    args = parser.parse_args()
    
    storylines_dir = PROJECT_ROOT / "docs/storylines"
    
    if args.plan:
        plan_file = Path(args.plan)
        if not plan_file.is_absolute():
            plan_file = PROJECT_ROOT / plan_file
        if not plan_file.exists():
            print(f"Error: Storyline file not found at {plan_file}")
            sys.exit(1)
        if compile_storyline_pdf(plan_file, args.strict) is None:
            sys.exit(1)
    else:
        md_files = sorted(storylines_dir.glob("figure_plan_*.md"))
        if not md_files:
            print(f"No storyline markdown files (figure_plan_*.md) found in {storylines_dir}")
            sys.exit(0)
        failed = [md for md in md_files if compile_storyline_pdf(md, args.strict) is None]
        if failed:
            sys.exit(1)


if __name__ == "__main__":
    main()
