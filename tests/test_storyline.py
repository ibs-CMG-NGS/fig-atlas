"""Storyline tools (scripts/storyline.py, roadmap S.1): storyline.yaml as the
single source of the figure assignment, the generated registry table, and the
consistency check. Runs the package tools (fig_atlas/tools/) on a throwaway
project repository, named by $FA_ROOT."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

MD = """# Manuscript Figure Plan: Demo

### Master Figure-Project 1:1 Mapping Registry

| Manuscript Figure | Project Identifier (`<project_name>`) | Configuration (`configs/`) | Analysis Script (`analysis/`) | Primary Figure Spec (`figure_specs/`) | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Main Figure 1** | `lab-paper-main-fig1-a` | hand-written | hand-written | hand-written | Active |

## Narrative
2026-09 개편(1): first draft.
"""

YAML = """storyline: "demo"
plan: "docs/storylines/figure_plan_demo.md"
figures:
  - slot: "Main Figure 1"
    project: "lab-paper-main-fig1-a"
    figure_number: 1
    description: "first"
  - slot: "Main Figure 2"
    project: "lab-paper-main-fig2-b"
    figure_number: 1
    description: "second"
    status: "Active (Promoted)"
tables: []
retired:
  - "lab-paper-main-fig9-old"
"""


def _project(root: Path, ns: str, name: str):
    cfg = root / "configs" / ns / f"config_{name}.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    script = f"analysis/{ns}/{name}_analysis.py"
    cfg.write_text(f'project:\n  name: "{name}"\n  analysis_script: "{script}"\n')
    (root / script).parent.mkdir(parents=True, exist_ok=True)
    (root / script).write_text("")
    spec = root / "figure_specs" / ns / f"figure_01_{name}.py"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("")


@pytest.fixture
def tool(tmp_path: Path, monkeypatch):
    (tmp_path / ".fig-atlas").write_text("")                 # marks a project repository
    monkeypatch.setenv("FA_ROOT", str(tmp_path))
    _project(tmp_path, "lab/paper", "lab-paper-main-fig1-a")
    _project(tmp_path, "lab/paper", "lab-paper-main-fig2-b")
    _project(tmp_path, "lab/archive", "lab-paper-main-fig9-old")
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode" / "tasks.json").write_text(json.dumps({"inputs": [
        {"id": "projectSelector", "options": ["lab-paper-main-fig1-a", "lab-paper-main-fig2-b"]}]}))
    (tmp_path / "docs" / "storylines" / "demo").mkdir(parents=True)
    (tmp_path / "docs" / "storylines" / "figure_plan_demo.md").write_text(MD, encoding="utf-8")
    (tmp_path / "docs" / "storylines" / "demo" / "storyline.yaml").write_text(YAML, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("storyline_under_test", REPO / "fig_atlas" / "tools" / "storyline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DEFAULT_PLAN = tmp_path / "docs" / "storylines" / "figure_plan_demo.md"
    return mod, tmp_path


def run(mod, *argv):
    return mod.main(list(argv))


def test_yaml_is_the_assignment(tool):
    mod, root = tool
    story = mod._compile_module().parse_storyline_md(mod.DEFAULT_PLAN)
    assert story["source"] == "yaml"
    assert [f["project"] for f in story["figures"]] == ["lab-paper-main-fig1-a", "lab-paper-main-fig2-b"]
    assert story["retired"] == ["lab-paper-main-fig9-old"]


def test_registry_then_check_is_clean_and_idempotent(tool, capsys):
    mod, root = tool
    assert run(mod, "check") == 1                        # hand-written table is out of date
    assert run(mod, "registry") == 0
    md = mod.DEFAULT_PLAN.read_text(encoding="utf-8")
    assert "Active (Promoted)" in md and "lab-paper-main-fig9-old" in md and "hand-written" not in md
    assert "## Narrative" in md                          # the rest of the document is untouched
    assert run(mod, "check") == 0
    run(mod, "registry")
    assert mod.DEFAULT_PLAN.read_text(encoding="utf-8") == md


@pytest.mark.parametrize("breakage,expected", [
    ("unregistered", "missing from .vscode/tasks.json"),
    ("retired_registered", "still in .vscode/tasks.json"),
    ("spec_missing", "figure_01_lab-paper-main-fig2-b.py missing"),
])
def test_check_reports_inconsistencies(tool, capsys, breakage, expected):
    mod, root = tool
    run(mod, "registry")
    tasks = root / ".vscode" / "tasks.json"
    if breakage == "unregistered":
        tasks.write_text(json.dumps({"inputs": [{"id": "projectSelector", "options": ["lab-paper-main-fig1-a"]}]}))
    elif breakage == "retired_registered":
        tasks.write_text(json.dumps({"inputs": [{"id": "projectSelector", "options": [
            "lab-paper-main-fig1-a", "lab-paper-main-fig2-b", "lab-paper-main-fig9-old"]}]}))
    else:
        (root / "figure_specs/lab/paper/figure_01_lab-paper-main-fig2-b.py").unlink()
    assert run(mod, "check") == 1
    assert expected in capsys.readouterr().out


def test_check_needs_no_vscode(tool):
    """The VS Code build dropdown is optional: without .vscode/tasks.json the
    other checks still run and a consistent storyline passes."""
    mod, root = tool
    run(mod, "registry")
    shutil.rmtree(root / ".vscode")
    assert run(mod, "check") == 0


# --------------------------------------------------------------- revisions (S.2) --
LOG = """# Plan

## Figure 1
> **2026-09 개편(3) — first layout**: moved panel b of `lab-paper-main-fig1-a`.
> continues on a second line (`extra_request.md`).
>
> not part of the block

## Figure 2
> *(이력)* **2026-09 개편(3)**: same change, logged here too.

> **개편(5) — renumber (2026-10-01)**: `lab-paper-main-fig2-b` becomes Figure 2.
> **개편(5) — something else (2026-10-02)**: a different change reusing the number.
"""


def test_revision_records_are_lossless_and_report_gaps_and_collisions(tool, capsys):
    mod, root = tool
    mod.DEFAULT_PLAN.write_text(LOG, encoding="utf-8")
    before = mod.DEFAULT_PLAN.read_bytes()
    assert run(mod, "revisions", "--sync") == 0
    out = capsys.readouterr().out
    assert mod.DEFAULT_PLAN.read_bytes() == before                  # the md is never modified
    assert "numbers never used: 1, 2, 4" in out
    assert "collision, revision 5" in out and "more than one place: 3" in out

    rv = mod._revisions_module()
    rdir = root / "docs" / "storylines" / "demo" / "revisions"
    by_n = rv.group(rv.extract_blocks(mod.DEFAULT_PLAN))
    assert sorted(by_n) == [3, 5]
    for n, bs in by_n.items():                                      # reassembled text == original blocks
        assert rv.blocks_in_record(rdir / f"R{n:03d}.md") == [b["text"] for b in bs]
        assert all(b["text"] in LOG for b in bs)
    assert "not part of the block" not in (rdir / "R003.md").read_text(encoding="utf-8")

    import yaml
    fm = yaml.safe_load((rdir / "R003.md").read_text(encoding="utf-8").split("---\n")[1])
    assert fm["id"] == "R003" and fm["figures"] == ["lab-paper-main-fig1-a"]
    assert fm["evidence"]["requests"] == ["extra_request.md"] and len(fm["sections"]) == 2
    fm5 = yaml.safe_load((rdir / "R005.md").read_text(encoding="utf-8").split("---\n")[1])
    assert fm5["date"] == "2026-10-02"
    assert "R005" in (rdir / "README.md").read_text(encoding="utf-8")


def test_revision_sync_never_overwrites_and_sets_revision_id(tool):
    mod, root = tool
    mod.DEFAULT_PLAN.write_text(LOG, encoding="utf-8")
    run(mod, "revisions", "--sync")
    rec = root / "docs" / "storylines" / "demo" / "revisions" / "R003.md"
    edited = rec.read_text(encoding="utf-8").replace("kind: []", "kind: [layout]")
    rec.write_text(edited, encoding="utf-8")
    run(mod, "revisions", "--sync")
    assert rec.read_text(encoding="utf-8") == edited                # hand-filled front matter survives
    # A record written ahead of the md (new revision) moves the revision ID.
    (rec.parent / "R007.md").write_text("---\nid: R007\n---\n", encoding="utf-8")
    assert mod._compile_module().parse_storyline_md(mod.DEFAULT_PLAN)["revision"] == "R007"


def test_diff_command_writes_changes_and_new_records_link_snapshots(tool, capsys):
    mod, root = tool
    mod.DEFAULT_PLAN.write_text(LOG, encoding="utf-8")
    base = root / "outputs" / "storylines" / "figure_plan_demo"
    for rev, proj in (("R003", "lab-paper-main-fig1-a"), ("R005", "lab-paper-main-fig2-b")):
        (base / rev).mkdir(parents=True)
        (base / rev / "revision.json").write_text(json.dumps({"revision": rev, "figures": [
            {"role": "Main Figure 1", "project": proj, "figure_number": 1, "source_sha256": rev}], "tables": []}))
    assert run(mod, "diff", "--write") == 0                       # default: the last two snapshots
    changes = root / "docs" / "storylines" / "demo" / "revisions" / "R005.changes.md"
    assert "**Main Figure 1**: `lab-paper-main-fig1-a` fig 1 -> `lab-paper-main-fig2-b` fig 1" in \
        changes.read_text(encoding="utf-8")
    assert run(mod, "diff", "R004") == 2                          # unknown snapshot

    run(mod, "revisions", "--sync")
    import yaml
    head = lambda n: yaml.safe_load((changes.parent / f"R00{n}.md").read_text(encoding="utf-8").split("---\n")[1])  # noqa: E731
    assert head(5)["snapshot"] == "outputs/storylines/figure_plan_demo/R005/"
    assert head(3)["snapshot"] == "outputs/storylines/figure_plan_demo/R003/"
    (changes.parent / "R009.changes.md").write_text("x")          # companion files are not revisions
    assert mod._compile_module().parse_storyline_md(mod.DEFAULT_PLAN)["revision"] == "R005"


def test_evidence_follows_slot_to_requests_and_revisions(tool, capsys):
    mod, root = tool
    data = root / "raw_data" / "s" / "anchor" / "ora_v2" / "ora.csv"
    data.parent.mkdir(parents=True)
    data.write_text("term\n")
    import hashlib
    fig = root / "outputs" / "lab" / "paper" / "lab-paper-main-fig1-a" / "figures" / "figure_01_x" / "figure_01.pdf"
    fig.parent.mkdir(parents=True)
    fig.write_bytes(b"%PDF")
    fig.with_name("figure_01.provenance.json").write_text(json.dumps({
        "run": {"finished": "2026-10-07"}, "code": [], "config": {},
        "inputs": [{"path": "raw_data/s/anchor/ora_v2/ora.csv", "sha256": hashlib.sha256(data.read_bytes()).hexdigest()}]}))
    reqs = root / "docs" / "data_contracts"
    reqs.mkdir(parents=True)
    (reqs / "rerun_request.md").write_text(
        "# R\n\n**Status**: **DELIVERED 2026-10-01**\n\n---\nDelivery: `raw_data/s/anchor/ora_v2/`\n", encoding="utf-8")
    rev = root / "docs" / "storylines" / "demo" / "revisions"
    rev.mkdir(parents=True)
    (rev / "R033.md").write_text('---\nid: R033\nfigures: []\nevidence:\n  requests: ["rerun_request.md"]\n---\n',
                                 encoding="utf-8")

    assert run(mod, "requests", "--sync") == 0
    assert "delivered   2026-10-01  rerun_request.md  -- integrated: 1 figure(s)" in capsys.readouterr().out
    assert run(mod, "evidence", "Main Figure 1") == 0
    out = capsys.readouterr().out
    assert "Main Figure 1 -> lab-paper-main-fig1-a" in out and "[fresh]" in out
    assert "<- rerun_request.md" in out and "rerun_request.md  delivered 2026-10-01; revisions R033" in out
    data.write_text("term\nchanged\n")
    run(mod, "evidence", "Main Figure 1")
    out = capsys.readouterr().out
    assert "[STALE]" in out and "CHANGED since the figure was built" in out
    assert run(mod, "evidence", "Main Figure 9") == 2
