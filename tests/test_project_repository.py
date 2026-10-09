"""The package works in any project repository (roadmap 6b, step 1): `fa init`
makes one; style presets, the matplotlibrc and the build tools come from the
installed package, not from files of this repository."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from fig_atlas.changeset import ChangeConflict
from fig_atlas.config import ProjectConfig, style_path
from fig_atlas.projects import MARKER, build_env, build_steps, find_root
from fig_atlas.repo_commands import plan_init, plan_new_project

ROOT = Path(__file__).resolve().parents[1]


def test_init_makes_a_project_repository(tmp_path):
    cs = plan_init(tmp_path)
    paths = {c.path for c in cs.changes}
    assert {MARKER, ".gitignore", "README.md", "AGENTS.md", "CLAUDE.md", ".gemini/settings.json",
            "configs/.gitkeep", "raw_data/.gitkeep"} <= paths
    cs.apply()
    assert find_root(tmp_path / "configs") == tmp_path.resolve()
    assert plan_init(tmp_path).empty                                   # a second run changes nothing
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "raw_data/" in gitignore and "outputs/" in gitignore      # whole-line patterns
    (tmp_path / "AGENTS.md").write_text("our own rules\n", encoding="utf-8")
    with pytest.raises(ChangeConflict):                               # never overwrites
        plan_init(tmp_path)


def test_styles_come_from_the_package_unless_the_project_has_its_own(tmp_path):
    plan_init(tmp_path).apply()
    plan_new_project(tmp_path, "demo").apply()
    cfg = ProjectConfig(tmp_path / "configs" / "config_demo.yaml")       # style: default, print, page_a4...
    assert cfg.page is not None and cfg._raw["figures"]
    assert style_path(tmp_path, "print") == ROOT / "fig_atlas" / "styles" / "print.yaml"
    own = tmp_path / "styles" / "print.yaml"
    own.write_text((ROOT / "fig_atlas" / "styles" / "print.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    assert style_path(tmp_path, "print") == own                       # the project's preset wins


def test_package_presets_match_this_repository():
    """While this repository still has styles/, they must equal the package's
    (line endings aside: git may check either out with CRLF on Windows)."""
    same = lambda a, b: a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")  # noqa: E731
    for f in (ROOT / "styles").glob("*.yaml"):
        assert same(f, ROOT / "fig_atlas" / "styles" / f.name), f.name
    if (ROOT / "matplotlibrc").is_file():
        assert same(ROOT / "matplotlibrc", ROOT / "fig_atlas" / "matplotlibrc")


def test_builds_use_the_package_matplotlibrc_and_tools(tmp_path):
    env = build_env({})
    rc = Path(env["MATPLOTLIBRC"])
    assert rc.is_file() and "pdf.fonttype: 42" in rc.read_text(encoding="utf-8")
    plan_init(tmp_path).apply()
    plan_new_project(tmp_path, "demo").apply()
    from fig_atlas.projects import find_project
    steps = build_steps(tmp_path, find_project(tmp_path, "demo"), preflight=True)
    assert [s[2] for s in steps[1:]] == ["fig_atlas.tools.build_atlas", "fig_atlas.tools.preflight",
                                         "fig_atlas.tools.verify_atlas"]


def test_tools_find_the_project_repository(tmp_path, monkeypatch):
    from fig_atlas.tools import project_root
    monkeypatch.setenv("FA_ROOT", str(tmp_path))
    assert project_root() == tmp_path.resolve()


def test_storyline_draft_comes_from_paper_project_names(tmp_path, monkeypatch):
    plan_init(tmp_path).apply()
    for name in ("lab-paper-main-fig2-b", "lab-paper-supp-fig1-s", "lab-paper-main-fig1-a", "lab-explore"):
        cfg = tmp_path / "configs" / f"config_{name}.yaml"
        cfg.write_text(f'project:\n  name: "{name}"\n', encoding="utf-8")
    monkeypatch.setenv("FA_ROOT", str(tmp_path))
    spec = importlib.util.spec_from_file_location("csp", ROOT / "fig_atlas" / "tools" / "compile_storyline_pdf.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text = "Figures: lab-paper-supp-fig1-s, lab-paper-main-fig2-b and lab-paper-main-fig1-a; not lab-paper-main-fig9-gone."
    slots = [(s["role"], s["project"]) for s in mod.paper_slots(text)]
    assert slots == [("Main Figure 1", "lab-paper-main-fig1-a"), ("Main Figure 2", "lab-paper-main-fig2-b"),
                     ("Supplementary Figure S1", "lab-paper-supp-fig1-s")]


def test_repo_root_finds_an_init_repository(tmp_path):
    """Scripts in a project repository (no fig_atlas/ folder) find it by the marker."""
    from fig_atlas.config import repo_root
    plan_init(tmp_path).apply()
    script = tmp_path / "analysis" / "lab" / "exploratory" / "x_analysis.py"
    script.parent.mkdir(parents=True)
    script.write_text("")
    assert repo_root(script) == tmp_path.resolve()
