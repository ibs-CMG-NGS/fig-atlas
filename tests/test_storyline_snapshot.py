"""Storyline snapshots and revision diffs (fig_atlas/tools/storyline_snapshot.py,
roadmap S.3): what a compile snapshot keeps, and that the diff between two
snapshots reports exactly the slot moves, data, config and output changes."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def sn():
    spec = importlib.util.spec_from_file_location("storyline_snapshot", REPO / "fig_atlas" / "tools" / "storyline_snapshot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _publish(root: Path, project: str, pdf_bytes: bytes, data: Path, size: int) -> Path:
    """A published figure_01.pdf with its provenance record (as fa build leaves them)."""
    base = root / "outputs" / "lab" / project
    fig = base / "figures" / "figure_01_main" / "figure_01.pdf"
    fig.parent.mkdir(parents=True, exist_ok=True)
    fig.write_bytes(pdf_bytes)
    rec = {"figure": {"source_stem": f"outputs/lab/{project}/figures/{project}_main"},
           "inputs": [{"path": data.relative_to(root).as_posix(), "sha256": _sha(data)}],
           "code": [], "config": {"path": None, "effective": {"plots": {"dots": {"size": size}}}},
           "environment": {"packages": {"matplotlib": "3.10.9"}}, "outputs": []}
    fig.with_name("figure_01.provenance.json").write_text(json.dumps(rec), encoding="utf-8")
    (base / "manifests").mkdir(exist_ok=True)
    (base / "manifests" / "preflight.csv").write_text(
        "project,figure,n,severity,check\n"
        f"{project},{project}_main,1,error,text_overlap\n"
        f"{project},{project}_other,1,error,print_font_too_small\n", encoding="utf-8")
    return fig


def _snapshot(sn, root: Path, rev: str, slots: list[tuple[str, str, Path]]) -> Path:
    rev_dir = root / "outputs" / "storylines" / "figure_plan_demo" / rev
    rev_dir.mkdir(parents=True)
    figs = [{"role": role, "project": proj, "figure_number": 1, "source_sha256": _sha(pdf),
             "state": sn.figure_state(root, pdf)} for role, proj, pdf in slots]
    sn.snapshot_extras(root, rev_dir, root / "missing.yaml", figs)
    (rev_dir / "revision.json").write_text(json.dumps({"revision": rev, "git_commit": "abc", "figures": figs,
                                                       "tables": ["t1.csv"]}), encoding="utf-8")
    return rev_dir


def test_figure_state_freshness_and_preflight_per_figure(sn, tmp_path):
    data = tmp_path / "raw_data" / "b" / "data.csv"
    data.parent.mkdir(parents=True)
    data.write_text("x\n1\n")
    pdf = _publish(tmp_path, "proj-a", b"%PDF a", data, 6)
    st = sn.figure_state(tmp_path, pdf)
    assert st["fresh"] is True and st["preflight_errors"] == 1      # the other figure's error is not counted
    data.write_text("x\n2\n")
    st = sn.figure_state(tmp_path, pdf)
    assert st["fresh"] is False and "input changed: raw_data/b/data.csv" in st["stale_reasons"]
    h = sn.health_summary([st])
    assert h["stale"] == 1 and "1 stale figure(s), 1 preflight error(s)" in sn.health_line(h)


def test_diff_reports_slot_moves_data_config_and_output_changes(sn, tmp_path):
    data = tmp_path / "raw_data" / "b" / "data.csv"
    data.parent.mkdir(parents=True)
    data.write_text("x\n1\n")
    pa = _publish(tmp_path, "proj-a", b"%PDF a1", data, 6)
    r1 = _snapshot(sn, tmp_path, "R001", [("Main Figure 1", "proj-a", pa)])
    assert (r1 / "provenance" / "proj-a__fig01.json").is_file()

    # Next revision: new data and a config change rebuild proj-a, which moves to slot 2; proj-b takes slot 1.
    data.write_text("x\n2\n")
    pa = _publish(tmp_path, "proj-a", b"%PDF a2", data, 7)
    pb = _publish(tmp_path, "proj-b", b"%PDF b1", data, 5)
    r2 = _snapshot(sn, tmp_path, "R002", [("Main Figure 1", "proj-b", pb), ("Main Figure 2", "proj-a", pa)])

    d = sn.diff(sn.load(r1), sn.load(r2))
    assert {(p["slot"], p["a"], p["b"]) for p in d["placement"]} == {
        ("Main Figure 1", ("proj-a", 1), ("proj-b", 1)), ("Main Figure 2", None, ("proj-a", 1))}
    (fa,) = d["figures"]
    assert fa["project"] == "proj-a" and (fa["slot_a"], fa["slot_b"]) == ("Main Figure 1", "Main Figure 2")
    assert fa["pdf_changed"] and fa["inputs"] == ([], [], ["raw_data/b/data.csv"])
    assert fa["config_keys"] == [("plots.dots.size", 6, 7)] and fa["packages"] == []
    assert d["added"] == [["proj-b", 1]] and d["removed"] == []

    md = sn.render(d)
    assert "**Main Figure 1**: `proj-a` fig 1 -> `proj-b` fig 1" in md
    assert "input changed: `raw_data/b/data.csv`" in md and "config `plots.dots.size`: 6 -> 7" in md
    assert "개편(3)" in sn.draft_block(d, 3, "2026-10-07")

    # A snapshot without provenance (made before S.3) still compares by PDF hash.
    (r1 / "provenance" / "proj-a__fig01.json").unlink()
    fa = sn.diff(sn.load(r1), sn.load(r2))["figures"][0]
    assert fa["no_record"] == ["A"] and fa["pdf_changed"]


def test_snapshots_sort_by_number_and_current_state(sn, tmp_path):
    base = tmp_path / "outputs" / "storylines" / "figure_plan_demo"
    for r in ("R010", "R002", "R009", "notes"):
        (base / r).mkdir(parents=True)
        (base / r / "revision.json").write_text("{}")
    names = [d.name for d in sn.list_snapshots(tmp_path, tmp_path / "docs" / "figure_plan_demo.md")]
    assert names == ["R002", "R009", "R010"]

    data = tmp_path / "d.csv"
    data.write_text("1")
    pdf = _publish(tmp_path, "proj-a", b"%PDF", data, 6)
    cur = sn.current(tmp_path, [{"role": "Main Figure 1", "project": "proj-a", "figure_number": 1},
                                {"role": "Main Figure 2", "project": "unbuilt", "figure_number": 1}],
                     [], lambda p, n: pdf if p == "proj-a" else None)
    assert cur["revision"] == "current" and [f["project"] for f in cur["figures"]] == ["proj-a"]
    assert cur["figures"][0]["_record"]["inputs"][0]["path"] == "d.csv"
