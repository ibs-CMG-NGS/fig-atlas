"""Repository procedures as commands (roadmap Phase 7): fa new project."""
from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fig_atlas.changeset import ChangeConflict, tasks_with
from fig_atlas.cli import main
from fig_atlas.param_tools import hardcoded
from fig_atlas.projects import ProjectError
from fig_atlas.repo_commands import plan_new_project

ROOT = Path(__file__).resolve().parents[1]
TASKS = ('{\n  "inputs": [\n    {\n      "id": "projectSelector",\n      "type": "pickString",\n'
         '      "options": [\n        "ALL",\n        "b-proj"\n      ],\n      "default": "ALL"\n    }\n  ]\n}\n')


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "configs").mkdir()
    (tmp_path / "fig_atlas").mkdir()                       # find_root() looks for these
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "build_atlas.py").write_text("")  # marks a project repository
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode" / "tasks.json").write_text(TASKS, encoding="utf-8")
    return tmp_path


def test_new_project_files_and_registration(repo):
    cs = plan_new_project(repo, "lab-demo", "lab", "exploratory", today="2026-10-08")
    assert [c.path for c in cs.changes] == ["configs/lab/exploratory/config_lab-demo.yaml",
                                            "analysis/lab/exploratory/lab-demo_analysis.py",
                                            "figure_specs/lab/exploratory/figure_01_lab-demo.py", ".vscode/tasks.json"]
    cs.apply()
    opts = json.loads((repo / ".vscode/tasks.json").read_text())["inputs"][0]["options"]
    assert opts == ["ALL", "b-proj", "lab-demo"]
    for f in ("analysis/lab/exploratory/lab-demo_analysis.py", "figure_specs/lab/exploratory/figure_01_lab-demo.py"):
        py_compile.compile(str(repo / f), doraise=True)
    assert hardcoded([repo / "analysis/lab/exploratory/lab-demo_analysis.py"]) == []   # no style literals
    spec = (repo / "figure_specs/lab/exploratory/figure_01_lab-demo.py").read_text()
    assert 'source_stem="lab/exploratory/lab-demo/figures/figure1_main"' in spec
    # idempotent: a second run plans nothing
    assert plan_new_project(repo, "lab-demo", "lab", "exploratory", today="2026-10-08").empty


def test_conflicts_and_bad_names(repo):
    (repo / "configs/sandbox-x").parent.mkdir(exist_ok=True)
    (repo / "configs" / "config_sandbox-x.yaml").write_text("project: {name: other}\n")
    with pytest.raises(ChangeConflict):
        plan_new_project(repo, "sandbox-x")                # same path, other content
    with pytest.raises(ProjectError, match="already exists"):
        plan_new_project(repo, "sandbox-x", "lab", "exploratory")
    for bad in ("Lab_Demo", "-x", "x"):
        with pytest.raises(ProjectError):
            plan_new_project(repo, bad)
    with pytest.raises(ProjectError, match="both"):
        plan_new_project(repo, "lab-z", domain="lab")
    note = " ".join(plan_new_project(repo, "lab-results", "lab", "paper").notes)
    assert "lab-paper-main-fig<N>-<slug>" in note


def test_tasks_list_keeps_formatting():
    tasks = ROOT / ".vscode" / "tasks.json"
    if not tasks.is_file():
        pytest.skip("this repository keeps no VS Code build list")
    text = tasks.read_text(encoding="utf-8")
    assert tasks_with(text) == text
    assert tasks_with(tasks_with(text, add=("zz-new",)), remove=("zz-new",)) == text


def test_cli_dry_run_writes_nothing(repo, capsys):
    assert main(["--root", str(repo), "new", "project", "demo-x", "--dry-run", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["applied"] is False and len(out["changes"]) == 4
    assert not (repo / "configs" / "config_demo-x.yaml").exists()


def _run_script(repo, name):
    env = dict(os.environ, CONFIG_PATH=f"configs/config_{name}.yaml",
               PYTHONPATH=os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")]))
    return subprocess.run([sys.executable, str(repo / "analysis" / f"{name}_analysis.py")], cwd=repo, env=env,
                          capture_output=True, text=True)


def _venn_bundle(repo, title="Shared genes"):
    b = repo / "raw_data" / "demo" / "venn_diagram_bundle"
    (b / "inputs").mkdir(parents=True)
    (b / "metadata").mkdir()
    (b / "inputs" / "data.csv").write_text("dataset,item\nA,g1\nA,g2\nB,g2\nB,g3\n")
    (b / "metadata" / "metadata.yaml").write_text(
        f"plot_type: venn\nplot_params:\n  set_labels: \"['A', 'B']\"\n  filter_name: \"{title}\"\n  bogus_key: 3\n")
    return b


def test_new_project_plus_ingested_bundle_draws(repo):
    """fa new project, then fa ingest bundle: the skeleton draws the bundle with no code written."""
    from fig_atlas.repo_commands import plan_ingest_bundle
    import yaml
    plan_new_project(repo, "demo-run").apply()
    assert _run_script(repo, "demo-run").returncode != 0           # no plots yet: a clear error
    b = _venn_bundle(repo)
    plan_ingest_bundle(repo, b, "demo-run").apply()
    cfg_text = (repo / "configs/config_demo-run.yaml").read_text()
    block = yaml.safe_load(cfg_text)["plots"]["venn_diagram"]
    assert block["renderer"] == "fig_atlas.renderers:render_venn"
    assert block["bundle"] == "raw_data/demo/venn_diagram_bundle" and block["filter_name"] == "Shared genes"
    assert block["set_labels"] == ["A", "B"]                         # Python-literal string from metadata, parsed
    assert "bogus_key" not in block and "# bogus_key: 3" in cfg_text  # not a renderer parameter: kept as a comment
    assert "(from the bundle)" in cfg_text and "# One block per panel" in cfg_text   # comments written and kept
    assert plan_ingest_bundle(repo, b, "demo-run").empty                              # idempotent
    res = _run_script(repo, "demo-run")
    assert res.returncode == 0, res.stderr[-1500:]
    assert (repo / "outputs" / "demo-run" / "figures" / "figure1_main.png").is_file()


def test_new_project_plus_bundle_passes_the_full_build(repo, monkeypatch):
    """Analysis -> publish -> verify, as `fa build` runs it: the skeleton's
    figure spec must not trip verify (its guide text once held a {placeholder})."""
    from fig_atlas.projects import build_project, find_project
    from fig_atlas.repo_commands import plan_ingest_bundle
    monkeypatch.setenv("PYTHONPATH", str(ROOT))           # the fixture's empty fig_atlas/ must not shadow it
    plan_new_project(repo, "demo-full", "lab", "exploratory").apply()
    plan_ingest_bundle(repo, _venn_bundle(repo), "demo-full").apply()
    result = build_project(repo, find_project(repo, "demo-full"), capture=True)
    assert result.ok, (result.failed_step, result.output_tail)


def test_ingest_refuses_a_bad_bundle_and_a_taken_name(repo):
    from fig_atlas.repo_commands import plan_ingest_bundle
    plan_new_project(repo, "demo-run").apply()
    b = _venn_bundle(repo)
    (b / "inputs" / "data.csv").write_text("dataset\nA\n")                       # no item column
    with pytest.raises(ChangeConflict, match="fails its contract"):
        plan_ingest_bundle(repo, b, "demo-run")
    (b / "inputs" / "data.csv").write_text("dataset,item\nA,g\n")
    plan_ingest_bundle(repo, b, "demo-run").apply()
    other = repo / "raw_data" / "demo" / "other"
    shutil.copytree(b, other)
    with pytest.raises(ChangeConflict, match="already exists"):
        plan_ingest_bundle(repo, other, "demo-run", name="venn_diagram")


def test_image_bundle_ingest_carries_pixel_size_and_channels(repo):
    import numpy as np
    import yaml
    from PIL import Image
    from fig_atlas.repo_commands import plan_ingest_bundle
    plan_new_project(repo, "demo-img").apply()
    b = repo / "raw_data" / "demo" / "cells_bundle"
    (b / "inputs").mkdir(parents=True)
    (b / "metadata").mkdir()
    for f in ("dna.png", "gfp.png"):
        Image.fromarray((np.arange(400).reshape(20, 20) % 255).astype(np.uint8)).save(b / "inputs" / f)
    (b / "metadata" / "metadata.yaml").write_text(
        "plot_type: image_panel\npixel_size: 0.5\npixel_unit: um\nchannels:\n"
        "  - {file: dna.png, label: DNA, color: \"#3b82f6\"}\n  - {file: gfp.png, label: GFP, color: \"#22c55e\"}\n")
    plan_ingest_bundle(repo, b, "demo-img").apply()
    block = yaml.safe_load((repo / "configs/config_demo-img.yaml").read_text())["plots"]["cells"]
    assert block["pixel_size"] == 0.5 and block["channel_labels"] == ["DNA", "GFP"]
    assert block["channel_colors"] == ["#3b82f6", "#22c55e"]
    res = _run_script(repo, "demo-img")
    assert res.returncode == 0, res.stderr[-1500:]


def test_a_block_without_bundle_uses_load(repo):
    plan_new_project(repo, "demo-load").apply()
    cfg = repo / "configs/config_demo-load.yaml"
    cfg.write_text(cfg.read_text().replace("plots: {}", "plots:\n  trend:\n    renderer: line_band\n"))
    script = repo / "analysis" / "demo-load_analysis.py"
    script.write_text(script.read_text().replace(
        '    raise NotImplementedError(f"load the data for plots.{name}")',
        '    import pandas as pd\n    return pd.DataFrame({"x": [0, 0, 1, 1], "y": [1.0, 1.2, 2.0, 2.2]})'))
    res = _run_script(repo, "demo-load")
    assert res.returncode == 0, res.stderr[-1500:]


def test_bundle_values_take_the_schema_type():
    from fig_atlas.repo_commands import _value_from_bundle
    from fig_atlas.schema import Param
    assert _value_from_bundle(Param("top_n", int, 10), 30.0) == 30
    assert isinstance(_value_from_bundle(Param("top_n", int, 10), 30.0), int)
    assert _value_from_bundle(Param("size", float, 1.0), 2.5) == 2.5
    assert _value_from_bundle(Param("labels", list, []), "['a', 'b']") == ["a", "b"]


# ------------------------------------------------------------- new renderer --
def _renderer_package(repo):
    (repo / "fig_atlas" / "renderers").mkdir(parents=True)
    shutil.copy(ROOT / "fig_atlas" / "renderers" / "__init__.py", repo / "fig_atlas" / "renderers" / "__init__.py")
    shutil.copy(ROOT / "fig_atlas" / "contracts.py", repo / "fig_atlas" / "contracts.py")


def test_new_renderer_skeleton_passes_the_renderer_checks(repo):
    """The skeleton draws, its SCHEMA agrees with its code, it has no style
    literals, and it is exported and registered for its plot_type."""
    import importlib.util
    import matplotlib.pyplot as plt
    import pandas as pd
    from fig_atlas.repo_commands import plan_new_renderer
    from fig_atlas.schema import CODE_DEFAULT
    from fig_atlas.schema_tools import by_key, extract_defaults
    _renderer_package(repo)
    cs = plan_new_renderer(repo, "dose_curve", plot_type="dose_curve", today="2026-10-08")
    assert {c.path for c in cs.changes} == {"fig_atlas/renderers/dose_curve.py", "tests/renderers/test_dose_curve.py",
                                            "fig_atlas/renderers/__init__.py", "fig_atlas/contracts.py"}
    cs.apply()
    src = repo / "fig_atlas" / "renderers" / "dose_curve.py"
    init = (repo / "fig_atlas" / "renderers" / "__init__.py").read_text()
    assert "from .dose_curve import render_dose_curve\nfrom .dumbbell import" in init
    assert '    "render_dose_curve",\n    "render_effect_dots",' in init
    assert '"dose_curve": "fig_atlas.renderers:render_dose_curve",\n}' in (repo / "fig_atlas" / "contracts.py").read_text()
    for f in (src, repo / "tests" / "renderers" / "test_dose_curve.py", repo / "fig_atlas" / "contracts.py"):
        py_compile.compile(str(f), doraise=True)

    spec = importlib.util.spec_from_file_location("dose_curve_skeleton", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fig, ax = plt.subplots()
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [0.1, 0.4, 0.8, 0.9], "g": ["a", "a", "b", "b"]})
    assert len(mod.render_dose_curve(ax, df, {"group_col": "g"})) == 4 and ax.get_legend() is not None
    plt.close(fig)
    params = mod.SCHEMA.all()
    for key, reads in by_key(extract_defaults(src)).items():          # as tests/test_renderer_schemas.py
        assert key in params, key
        literal = {repr(r.default) for r in reads if r.literal}
        if any(not r.literal for r in reads) or len(literal) > 1:
            assert params[key].default is CODE_DEFAULT, key
        else:
            assert params[key].default == next(r.default for r in reads if r.literal), key
    assert all(p.role for p in params.values())
    assert hardcoded([src]) == []

    assert plan_new_renderer(repo, "dose_curve", plot_type="dose_curve", today="2026-10-08").empty   # idempotent


def test_new_renderer_refuses_taken_and_bad_names(repo):
    from fig_atlas.repo_commands import plan_new_renderer
    _renderer_package(repo)
    with pytest.raises(ChangeConflict, match="already exists"):
        plan_new_renderer(repo, "volcano")                         # a pack renderer and a recipe
    with pytest.raises(ProjectError):
        plan_new_renderer(repo, "Dose-Curve")
    with pytest.raises(ChangeConflict, match="already drawn by"):
        plan_new_renderer(repo, "my_venn", plot_type="venn")
    with pytest.raises(ChangeConflict, match="not a folder"):
        plan_new_renderer(repo, "x_plot", package="no_such_pack.renderers")



def test_new_renderer_in_a_project_repository(tmp_path, monkeypatch):
    """Outside the fig-atlas source, the renderer goes in the repository's own
    renderers/ folder, which fig-atlas then finds without installing anything."""
    from fig_atlas import plugins
    from fig_atlas.contracts import ingest_map
    from fig_atlas.repo_commands import plan_new_renderer
    (tmp_path / ".fig-atlas").write_text("# marker", encoding="utf-8")
    cs = plan_new_renderer(tmp_path, "dot_strip", plot_type="dot_strip", today="2026-10-13")
    assert {c.path for c in cs.changes} == {"renderers/dot_strip.py", "renderers/__init__.py",
                                            "tests/renderers/test_dot_strip.py"}
    cs.apply()
    init = (tmp_path / "renderers" / "__init__.py").read_text(encoding="utf-8")
    assert '"dot_strip": "renderers.dot_strip:render_dot_strip",' in init
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    for m in [m for m in sys.modules if m == "renderers" or m.startswith("renderers.")]:
        monkeypatch.delitem(sys.modules, m)
    assert any(p.name == "project" for p in plugins.entry_points("renderers"))
    assert ingest_map()["dot_strip"] == "renderers.dot_strip:render_dot_strip"
    second = plan_new_renderer(tmp_path, "ring", today="2026-10-13")          # the folder exists now: an edit
    assert {c.path: c.kind for c in second.changes}["renderers/__init__.py"] == "edit"
    for m in [m for m in sys.modules if m == "renderers" or m.startswith("renderers.")]:
        monkeypatch.delitem(sys.modules, m)

# ------------------------------------------------------------ retire, promote --
def _exploratory(repo, name="lab-trial"):
    plan_new_project(repo, name, "lab", "exploratory", slug="trial", today="2026-10-08").apply()
    return name


def test_promote_moves_renames_and_updates(repo):
    from fig_atlas.repo_commands import plan_promote
    old = _exploratory(repo)
    (repo / "configs" / "lab" / "exploratory" / "config_lab-other.yaml").write_text(
        f"project:\n  name: lab-other\n# reads outputs of {old}\n")
    cs = plan_promote(repo, old, 4, "atlas")
    assert any("lab-other" in n for n in cs.notes)                 # cross-reference reported
    cs.apply()
    new = "lab-paper-main-fig4-atlas"
    import yaml
    cfg = yaml.safe_load((repo / f"configs/lab/paper/config_{new}.yaml").read_text())
    assert cfg["project"]["name"] == new and cfg["project"]["spec_pattern"] == f"figure_*_{new}.py"
    assert cfg["project"]["analysis_script"] == f"analysis/lab/paper/{new}_analysis.py"
    assert (repo / f"analysis/lab/paper/{new}_analysis.py").is_file()
    spec = (repo / f"figure_specs/lab/paper/figure_01_{new}.py").read_text()
    assert f'source_stem="lab/paper/{new}/figures/figure1_trial"' in spec
    assert f'primary_code="analysis/lab/paper/{new}_analysis.py"' in spec
    assert not (repo / "configs/lab/exploratory/config_lab-trial.yaml").exists()
    opts = json.loads((repo / ".vscode/tasks.json").read_text())["inputs"][0]["options"]
    assert new in opts and old not in opts
    assert "# Created by" in (repo / f"configs/lab/paper/config_{new}.yaml").read_text()   # comments kept
    assert plan_promote(repo, old, 4, "atlas").empty                                    # idempotent


def test_retire_moves_to_archive(repo):
    from fig_atlas.repo_commands import plan_retire
    name = _exploratory(repo)
    plan_retire(repo, name).apply()
    import yaml
    cfg = yaml.safe_load((repo / f"configs/lab/archive/config_{name}.yaml").read_text())
    assert cfg["project"]["analysis_script"] == f"analysis/lab/archive/{name}_analysis.py"
    spec = (repo / f"figure_specs/lab/archive/figure_01_{name}.py").read_text()
    assert f'source_stem="lab/archive/{name}/figures/figure1_trial"' in spec
    assert name not in json.loads((repo / ".vscode/tasks.json").read_text())["inputs"][0]["options"]
    assert plan_retire(repo, name).empty                                                 # idempotent


def test_promote_refuses_non_exploratory_and_sandbox(repo):
    from fig_atlas.repo_commands import plan_promote, plan_retire
    plan_new_project(repo, "sandbox-y").apply()
    with pytest.raises(ProjectError, match="sandbox"):
        plan_retire(repo, "sandbox-y")
    plan_new_project(repo, "lab-paper-main-fig1-done", "lab", "paper").apply()
    with pytest.raises(ProjectError, match="only exploratory"):
        plan_promote(repo, "lab-paper-main-fig1-done", 2, "again")
