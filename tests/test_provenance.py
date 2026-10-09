"""Provenance records (fig_atlas/provenance.py, roadmap P.1).

A throwaway repository with a data bundle, a config, a style preset and an
analysis script that reads files in three different ways (pandas, yaml,
open()) and reads another project's output. The script runs under
`python -m fig_atlas.provenance` exactly as `fa build` runs it.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fig_atlas import FigureSpec, ProjectConfig, publish

SCRIPT = """
import json, sys
from pathlib import Path
import pandas as pd, yaml
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
root = Path.cwd()
df = pd.read_csv(root / "raw_data/study/proj/bundle/inputs/data.csv")
cfg = yaml.safe_load(open(root / "configs/lab/paper/config_proj.yaml"))
notes = (root / "outputs/other/table.txt").read_text()
if "--fail" in open(root / "raw_data/study/proj/flag.txt").read():
    sys.exit(4)
out = root / "outputs/lab/paper/proj/figures"
out.mkdir(parents=True, exist_ok=True)
fig, ax = plt.subplots()
ax.plot(df["x"], df["y"])
for fmt in ("png", "pdf"):
    fig.savefig(out / f"figure1_demo.{fmt}")
(out / "stats.csv").write_text("a,b\\n1,2\\n")
"""


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "build_atlas.py").write_text("")
    bundle = tmp_path / "raw_data/study/proj/bundle"
    (bundle / "inputs").mkdir(parents=True)
    (bundle / "metadata").mkdir()
    (bundle / "inputs" / "data.csv").write_text("x,y\n0,1\n1,3\n")
    (bundle / "metadata" / "metadata.yaml").write_text("app_version: upstream-exporter-2\nplot_type: line\n")
    (tmp_path / "raw_data/study/proj/flag.txt").write_text("ok")
    (tmp_path / "styles").mkdir()
    (tmp_path / "styles" / "house.yaml").write_text("figures:\n  font_size: 7\n")
    cfg = tmp_path / "configs/lab/paper/config_proj.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('project:\n  name: "proj"\n  figure_count: 1\n  style: ["house"]\n'
                   '  analysis_script: "analysis/lab/paper/proj_analysis.py"\npaths:\n  raw_root: "raw_data"\n'
                   '  output_root: "outputs"\nfigures:\n  formats: ["png", "pdf"]\n')
    (tmp_path / "outputs/other").mkdir(parents=True)
    (tmp_path / "outputs/other/table.txt").write_text("from another project")
    script = tmp_path / "analysis/lab/paper/proj_analysis.py"
    script.parent.mkdir(parents=True)
    script.write_text(SCRIPT)
    return tmp_path


def _run(repo: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, CONFIG_PATH="configs/lab/paper/config_proj.yaml", SOURCE_DATE_EPOCH="0")
    return subprocess.run([sys.executable, "-m", "fig_atlas.provenance", "analysis/lab/paper/proj_analysis.py"],
                          cwd=repo, env=env, capture_output=True, text=True)


def _record(repo: Path) -> dict:
    return json.loads((repo / "outputs/lab/paper/proj/figures/figure1_demo.provenance.json").read_text())


def test_inputs_are_exactly_the_files_read(repo):
    assert _run(repo).returncode == 0
    rec = _record(repo)
    got = {i["path"] for i in rec["inputs"]}
    # Observed, not declared: the script reads the config with yaml itself, so
    # the style preset it names is never opened and is not an input.
    assert got == {"raw_data/study/proj/bundle/inputs/data.csv", "configs/lab/paper/config_proj.yaml",
                   "outputs/other/table.txt", "raw_data/study/proj/flag.txt"}
    data = next(i for i in rec["inputs"] if i["path"].endswith("data.csv"))
    assert data["sha256"] == _sha(repo / "raw_data/study/proj/bundle/inputs/data.csv")
    assert data["bundle"]["app_version"] == "upstream-exporter-2"


def test_outputs_code_config_environment(repo):
    assert _run(repo).returncode == 0
    rec = _record(repo)
    outs = {o["path"]: o["sha256"] for o in rec["outputs"]}
    assert set(outs) == {"outputs/lab/paper/proj/figures/figure1_demo.png",
                         "outputs/lab/paper/proj/figures/figure1_demo.pdf"}
    png = repo / "outputs/lab/paper/proj/figures/figure1_demo.png"
    assert outs["outputs/lab/paper/proj/figures/figure1_demo.png"] == _sha(png)
    assert [w["path"] for w in rec["other_files_written"]] == ["outputs/lab/paper/proj/figures/stats.csv"]
    assert "analysis/lab/paper/proj_analysis.py" in {c["path"] for c in rec["code"]}
    assert rec["config"]["effective"]["figures"]["font_size"] == 7      # style preset merged in
    assert rec["environment"]["packages"]["matplotlib"]
    assert rec["schema"] == "fig-atlas/provenance@1"


def test_failed_script_writes_no_record(repo):
    (repo / "raw_data/study/proj/flag.txt").write_text("--fail")
    proc = _run(repo)
    assert proc.returncode == 4
    assert not (repo / "outputs/lab/paper/proj/figures/figure1_demo.provenance.json").exists()


def test_publish_copies_record_and_summarises_it(repo):
    assert _run(repo).returncode == 0
    config = ProjectConfig(repo / "configs/lab/paper/config_proj.yaml")
    spec = FigureSpec(number=1, slug="demo", title="Demo", source_stem="lab/paper/proj/figures/figure1_demo",
                      primary_code="analysis/lab/paper/proj_analysis.py", panel_notes=["Panel a."])
    publish(spec, config)
    out = config.figures_root / "figure_01_demo"
    assert (out / "figure_01.provenance.json").is_file()
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "## Provenance" in readme and "raw_data/study/proj/bundle/inputs/data.csv" in readme
    assert "upstream-exporter-2" in readme


def test_style_presets_are_inputs_when_the_script_loads_the_config(repo):
    script = repo / "analysis/lab/paper/proj_analysis.py"
    script.write_text("from fig_atlas import get_config\nget_config()\n" + script.read_text())
    assert _run(repo).returncode == 0
    assert "styles/house.yaml" in {i["path"] for i in _record(repo)["inputs"]}


# ------------------------------------------------- freshness & impact (P.3) --
from fig_atlas import verify_atlas  # noqa: E402
from fig_atlas.provenance import check_freshness, impacted_by, published_records  # noqa: E402


def _published(repo):
    assert _run(repo).returncode == 0
    config = ProjectConfig(repo / "configs/lab/paper/config_proj.yaml")
    spec = FigureSpec(number=1, slug="demo", title="Demo", source_stem="lab/paper/proj/figures/figure1_demo",
                      primary_code="analysis/lab/paper/proj_analysis.py", panel_notes=["Panel a."])
    publish(spec, config)
    (rec_path, rec), = published_records(repo)
    return config, rec


def test_fresh_after_build(repo):
    _, rec = _published(repo)
    assert check_freshness(repo, rec) == []


def test_changed_input_makes_figure_stale(repo):
    _, rec = _published(repo)
    (repo / "raw_data/study/proj/bundle/inputs/data.csv").write_text("x,y\n0,1\n1,4\n")
    assert check_freshness(repo, rec) == ["input changed: raw_data/study/proj/bundle/inputs/data.csv"]


def test_touched_but_unchanged_input_stays_fresh(repo):
    _, rec = _published(repo)
    f = repo / "raw_data/study/proj/bundle/inputs/data.csv"
    os.utime(f, (f.stat().st_atime + 100, f.stat().st_mtime + 100))
    assert check_freshness(repo, rec) == []


def test_changed_config_and_script_make_figure_stale(repo):
    _, rec = _published(repo)
    cfg = repo / "configs/lab/paper/config_proj.yaml"
    cfg.write_text(cfg.read_text() + "# tuned\n")
    script = repo / "analysis/lab/paper/proj_analysis.py"
    script.write_text(script.read_text() + "\n# edited\n")
    reasons = check_freshness(repo, rec)
    assert "config changed: configs/lab/paper/config_proj.yaml" in reasons
    assert "code changed: analysis/lab/paper/proj_analysis.py" in reasons


def test_impact_finds_figures_reading_a_file_or_folder(repo):
    _published(repo)
    by_file = impacted_by(repo, repo / "raw_data/study/proj/bundle/inputs/data.csv")
    by_folder = impacted_by(repo, repo / "raw_data/study/proj/bundle")
    assert [h["figure"] for h in by_file] == [h["figure"] for h in by_folder] == [
        "outputs/lab/paper/proj/figures/figure_01_demo"]
    assert impacted_by(repo, repo / "styles/house.yaml") == []          # never opened


def test_verify_warns_on_stale_figures(repo):
    config, _ = _published(repo)
    assert not [r for r in verify_atlas(config) if r["kind"] == "provenance"]
    (repo / "raw_data/study/proj/bundle/inputs/data.csv").write_text("x,y\n9,9\n")
    rows = [r for r in verify_atlas(config) if r["kind"] == "provenance"]
    assert [r["status"] for r in rows] == ["WARN"] and "data.csv" in rows[0]["detail"]


# ------------------------------------------------ index, lineage, diff (P.3) --
from fig_atlas.provenance import build_index, diff_records, lineage  # noqa: E402


def test_index_lineage_and_record_diff(repo):
    _, rec = _published(repo)
    index = build_index(repo)["figures"]
    (entry,) = index.values()
    assert entry["bundles"] == ["raw_data/study/proj/bundle"] and entry["stale_reasons"] == []
    assert (repo / "outputs" / "provenance_index.json").is_file()

    text = "\n".join(lineage(rec))
    assert "<- config configs/lab/paper/config_proj.yaml" in text and "styles: house" in text
    assert "raw_data/study/proj/bundle  [upstream-exporter-2, line]" in text and "data.csv  sha256" in text

    # Rebuild after an input and a config value change: the diff names exactly those.
    old = json.loads(json.dumps(rec))
    (repo / "raw_data/study/proj/bundle/inputs/data.csv").write_text("x,y\n0,1\n1,9\n")
    cfg = repo / "configs/lab/paper/config_proj.yaml"
    cfg.write_text(cfg.read_text().replace('formats: ["png", "pdf"]', 'formats: ["png", "pdf"]\n  dpi: 300'))
    _, new = _published(repo)
    d = diff_records(old, new)
    assert d["inputs"] == ([], [], ["configs/lab/paper/config_proj.yaml",          # the config is read too
                                   "raw_data/study/proj/bundle/inputs/data.csv"])
    assert ("figures.dpi", None, 300) in d["config_keys"] and d["config_file_changed"]
    assert d["code"] == ([], [], []) and d["packages"] == []
    # Tooling modules (pipeline plumbing) never count as a code difference.
    old["code"].append({"path": "fig_atlas/publish.py", "sha256": "x"})
    assert diff_records(old, new)["code"] == ([], [], [])


def test_cli_lineage_and_diff_figure(repo, capsys):
    from fig_atlas.cli import main
    _, rec = _published(repo)
    saved = repo / "old_record.json"
    saved.write_text(json.dumps(rec))
    assert main(["--root", str(repo), "lineage", "proj"]) == 0
    assert "proj figure 1" in capsys.readouterr().out
    assert main(["--root", str(repo), "diff-figure", "proj", "--against", str(saved)]) == 0
    assert "outputs changed: none (identical files)" in capsys.readouterr().out
    assert main(["--root", str(repo), "diff-figure", "proj"]) == 2      # no storyline snapshot holds it
    assert main(["--root", str(repo), "lineage", "proj", "--figure", "4"]) == 2


def test_live_numbers_recorded_published_and_verified(repo):
    script = repo / "analysis/lab/paper/proj_analysis.py"
    script.write_text(script.read_text() + "\nfrom fig_atlas import claims\n"
                      "claims.record('n_points', int(len(df)), source='rows of data.csv')\n")
    assert _run(repo).returncode == 0
    assert _record(repo)["claims"]["n_points"] == {"value": 2, "source": "rows of data.csv"}
    config = ProjectConfig(repo / "configs/lab/paper/config_proj.yaml")
    spec = FigureSpec(number=1, slug="demo", title="Demo of {n_points} points",
                      source_stem="lab/paper/proj/figures/figure1_demo", primary_code="analysis/lab/paper/proj_analysis.py",
                      panel_notes=["Panel a: {n_points:,} points; {n_missing} unrecorded."])
    publish(spec, config)
    readme = (repo / "outputs/lab/paper/proj/figures/figure_01_demo/README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Figure 1: Demo of 2 points") and "Panel a: 2 points; {n_missing} unrecorded." in readme
    rows = [r for r in verify_atlas(config) if r["kind"] == "live_number"]
    assert [(r["id"], r["status"]) for r in rows] == [("figure_01:n_missing", "FAIL")]


def test_cli_claims_baseline_check(repo, capsys):
    from fig_atlas.cli import main
    spec = repo / "figure_specs/lab/paper/figure_01_proj.py"
    spec.parent.mkdir(parents=True)
    body = ('from fig_atlas import FigureSpec\nSPEC = FigureSpec(number=1, slug="demo", title="Demo", '
            'source_stem="s", primary_code="a.py", panel_notes=[{notes!r}])\n')
    spec.write_text(body.format(notes="4,321 anchors open (padj < 0.05) at day 1; {n_live:,} live."))
    assert main(["--root", str(repo), "claims", "--write"]) == 0
    out = capsys.readouterr().out
    assert "1 hand-typed number(s)" in out and "1 live placeholder(s)" in out
    assert main(["--root", str(repo), "claims", "--check"]) == 0
    spec.write_text(body.format(notes="4,321 anchors open, 1,212 concordant (padj < 0.05)."))
    assert main(["--root", str(repo), "claims", "--check"]) == 1
    assert "INCREASED  proj figure 1: 1 -> 2" in capsys.readouterr().out


def test_use_from_takes_another_figures_recorded_numbers(repo):
    from fig_atlas import claims
    script = repo / "analysis/lab/paper/proj_analysis.py"
    script.write_text(script.read_text() + "\nfrom fig_atlas import claims\nclaims.record('n_points', int(len(df)))\n")
    _published(repo)
    claims.REGISTRY.clear()
    try:
        assert claims.use_from("proj", root=repo) == {"n_points": 2}
        assert claims.REGISTRY["n_points"]["source"].startswith("proj figure 1")
        with pytest.raises(KeyError):
            claims.use_from("proj", names=["n_points", "n_other"], root=repo)
        with pytest.raises(FileNotFoundError):
            claims.use_from("proj", figure=2, root=repo)
    finally:
        claims.REGISTRY.clear()


# ---------------------------------------------------- source data, export (P.5) --
SOURCE_DATA = """
from fig_atlas import source_data
source_data.add(df, panel="a", title="the plotted line")
source_data.add(df.describe().reset_index(), panel="a", name="summary", title="summary")
"""


def _with_source_data(repo):
    script = repo / "analysis/lab/paper/proj_analysis.py"
    text = script.read_text()
    # register before the figure is saved, as scripts must
    script.write_text(text.replace("for fmt in (\"png\", \"pdf\"):", SOURCE_DATA.strip() + "\nfor fmt in (\"png\", \"pdf\"):"))
    return _published(repo)


def test_source_data_recorded_published_and_verified(repo):
    config, rec = _with_source_data(repo)
    assert [(e["panel"], e["name"], e["rows"]) for e in rec["source_data"]] == [("a", "", 2), ("a", "summary", 8)]
    out = repo / "outputs/lab/paper/proj/figures/figure_01_demo"
    sd = out / "figure_01_source_data"
    assert sorted(p.name for p in sd.iterdir()) == ["README.md", "panel_a.csv", "panel_a_summary.csv"]
    assert (sd / "panel_a.csv").read_text() == "x,y\n0,1\n1,3\n"
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "## Source data" in readme and "- Panel a: `panel_a.csv` (2 rows) the plotted line" in readme
    rows = [r for r in verify_atlas(config) if r["kind"] == "source_data"]
    assert [r["status"] for r in rows] == ["PASS", "PASS"]
    (sd / "panel_a.csv").write_text("x,y\n0,1\n1,99\n")
    assert [r["status"] for r in verify_atlas(config) if r["kind"] == "source_data"] == ["FAIL", "PASS"]


STATS = """
from fig_atlas import stats
t = stats.compare_to_control({"ctrl": [1, 2, 3], "trt": [4, 5, 7]}, control="ctrl")
t["p_adj"] = stats.adjust(t["p"], "bh")
stats.record(t, name="trt_vs_ctrl", title="treatment vs control")
"""


def test_stats_tables_recorded_published_and_verified(repo):
    script = repo / "analysis/lab/paper/proj_analysis.py"
    script.write_text(script.read_text().replace("for fmt in (\"png\", \"pdf\"):",
                                                 STATS.strip() + "\nfor fmt in (\"png\", \"pdf\"):"))
    config, rec = _published(repo)
    assert [(e["name"], e["rows"]) for e in rec["statistics"]] == [("trt_vs_ctrl", 1)]
    out = repo / "outputs/lab/paper/proj/figures/figure_01_demo"
    table = out / "figure_01_statistics" / "trt_vs_ctrl.csv"
    assert table.read_text().splitlines()[0].startswith("group,control,test,n,")
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "figure_01_statistics/trt_vs_ctrl.csv`  (tests run by the build: treatment vs control)" in readme
    published = json.loads((out / "figure_01.provenance.json").read_text())
    assert [t["source"] for t in published["statistics_tables"]] == ["stats_layer"]
    rows = [r for r in verify_atlas(config) if r["kind"] == "statistics_table"]
    assert [r["status"] for r in rows] == ["PASS"]
    table.unlink()
    assert [r["status"] for r in verify_atlas(config) if r["kind"] == "statistics_table"] == ["FAIL"]


IMAGE = """
from fig_atlas.renderers import render_image_panel
fig2, ax2 = plt.subplots()
render_image_panel(ax2, root / "raw_data/study/proj/blot.png",
                   {"panel": "b", "gamma": 0.8, "crop": [0, 0, 8, 6], "pixel_size": 0.5, "scale_bar": 2})
ax = ax2
"""


def test_image_adjustments_recorded_published_and_verified(repo):
    import numpy as np
    from PIL import Image
    Image.fromarray((np.arange(120).reshape(10, 12) * 2).astype(np.uint8)).save(repo / "raw_data/study/proj/blot.png")
    script = repo / "analysis/lab/paper/proj_analysis.py"
    script.write_text(script.read_text().replace("for fmt in (\"png\", \"pdf\"):",
                                                 IMAGE.strip() + "\nfor fmt in (\"png\", \"pdf\"):"))
    config, rec = _published(repo)
    (img,) = rec["images"]
    assert img["panel"] == "b" and img["gamma"] == 0.8 and img["nonlinear"] is True
    assert img["crop"] == [0, 0, 8, 6] and img["scale_bar_px"] == 4.0
    (ch,) = img["channels"]
    assert ch["path"] == "raw_data/study/proj/blot.png" and len(ch["sha256"]) == 64
    readme = (repo / "outputs/lab/paper/proj/figures/figure_01_demo/README.md").read_text(encoding="utf-8")
    assert "## Images" in readme and "gamma 0.8 (nonlinear)" in readme and "`raw_data/study/proj/blot.png`" in readme
    rows = [r for r in verify_atlas(config) if r["kind"] == "image"]
    assert sorted(r["status"] for r in rows) == ["PASS", "WARN"]
    Image.fromarray(np.zeros((10, 12), np.uint8)).save(repo / "raw_data/study/proj/blot.png")
    assert "FAIL" in [r["status"] for r in verify_atlas(config) if r["kind"] == "image"]


def test_export_writes_an_ro_crate(repo):
    from fig_atlas.export import export_figure
    _with_source_data(repo)
    folder = repo / "outputs/lab/paper/proj/figures/figure_01_demo"
    crate = export_figure(repo, folder, repo / "crate")
    meta = json.loads((crate / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    by_id = {e["@id"]: e for e in meta["@graph"]}
    assert by_id["ro-crate-metadata.json"]["conformsTo"]["@id"] == "https://w3id.org/ro/crate/1.1"
    parts = {p["@id"] for p in by_id["./"]["hasPart"]}
    assert {"figure_01.png", "figure_01.pdf", "figure_01.provenance.json", "README.md", "figure_01_source_data/"} <= parts
    for p in parts - {"figure_01_source_data/"}:
        assert (crate / p).is_file() and by_id[p]["sha256"] == _sha(crate / p)
    build = by_id["#build"]
    assert build["@type"] == "CreateAction" and build["instrument"]["@id"] == "#code:analysis/lab/paper/proj_analysis.py"
    inputs = {o["@id"] for o in build["object"]}
    assert "#input:raw_data/study/proj/bundle/inputs/data.csv" in inputs and not (crate / "inputs").exists()
    assert "upstream-exporter-2" in by_id["#input:raw_data/study/proj/bundle/inputs/data.csv"]["description"]
    full = export_figure(repo, folder, repo / "crate2", include_inputs=True)
    assert (full / "inputs/raw_data/study/proj/bundle/inputs/data.csv").is_file()


def test_build_records_config_usage_and_lint_finds_a_typo(repo, capsys):
    from fig_atlas.cli import main
    cfg = repo / "configs/lab/paper/config_proj.yaml"
    cfg.write_text(cfg.read_text() + "plots:\n  line:\n    line_width: 2\n    colour: red\n    unused_knob: 3\n")
    script = repo / "analysis/lab/paper/proj_analysis.py"
    script.write_text(script.read_text() + (
        "\nfrom fig_atlas import get_config\n"
        "pc = get_config(root / 'configs/lab/paper/config_proj.yaml')._raw['plots']['line']\n"
        "pc.get('line_width', 1); pc.get('color', 'black')\n"))
    _, rec = _published(repo)
    usage = rec["config"]["usage"]
    assert "plots.line.line_width" in usage["read"] and "plots.line.color" in usage["missed"]
    assert main(["--root", str(repo), "lint", "proj", "--defaults"]) == 0        # reports only
    assert main(["--root", str(repo), "lint", "proj", "--check"]) == 1           # a likely typo -> exit 1
    out = capsys.readouterr().out
    assert "TYPO?   plots.line.colour  -- not read; the code reads plots.line.color, which is absent" in out
    assert "plots.line.unused_knob" in out
