"""`fa` CLI (fig_atlas/cli.py) and project discovery/build (fig_atlas/projects.py).

Builds run against a throwaway repository whose analysis/publish/verify
scripts are stubs that log their call, so the orchestration (order, stop on
failure, keep going with --all, exit codes, CONFIG_PATH) is tested without
rendering anything.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fig_atlas.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main
from fig_atlas.projects import ProjectError, find_project, find_root, list_projects

STUB = """import os, sys
from pathlib import Path
Path("calls.log").open("a").write(f"{{Path(sys.argv[0]).name}} {{os.environ.get('CONFIG_PATH')}}\\n")
sys.exit({code})
"""


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    import fig_atlas.projects as projects
    (tmp_path / ".fig-atlas").write_text("")              # marks a project repository
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for step, name in (("PUBLISH_STEP", "build_atlas"), ("VERIFY_STEP", "verify_atlas"),
                       ("MANIFEST_STEP", "consolidate_manifest")):
        (stubs / f"{name}.py").write_text(STUB.format(code=0))
        monkeypatch.setattr(projects, step, (str(stubs / f"{name}.py"),))
    for ns, name, code in [("lab/paper", "good", 0), ("lab/exploratory", "broken", 3),
                           ("lab/archive", "old", 0)]:
        cfg = tmp_path / "configs" / ns / f"config_{name}.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        script = f"analysis/{ns}/{name}_analysis.py"
        cfg.write_text(f'project:\n  name: "{name}"\n  analysis_script: "{script}"\n')
        (tmp_path / script).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / script).write_text(STUB.format(code=code))
    return tmp_path


def calls(repo: Path) -> list[str]:
    log = repo / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def test_find_root_walks_up(repo):
    deep = repo / "analysis" / "lab" / "paper"
    assert find_root(deep) == repo.resolve()


def test_find_root_outside_repo_fails(tmp_path):
    with pytest.raises(ProjectError):
        find_root(tmp_path)


def test_list_and_find(repo):
    names = {p.name: p for p in list_projects(repo)}
    assert set(names) == {"good", "broken", "old"}
    assert names["old"].archived and not names["good"].archived
    assert find_project(repo, "good").namespace == "lab/paper"
    with pytest.raises(ProjectError, match="no config"):
        find_project(repo, "missing")


def test_ambiguous_name(repo):
    dup = repo / "configs" / "other" / "config_good.yaml"
    dup.parent.mkdir(parents=True)
    dup.write_text("project: {}\n")
    with pytest.raises(ProjectError, match="ambiguous"):
        find_project(repo, "good")


def test_list_json_hides_archived_by_default(repo, capsys):
    assert main(["--root", str(repo), "list", "--json"]) == EXIT_OK
    out = json.loads(capsys.readouterr().out)
    assert [p["name"] for p in out] == ["broken", "good"]


def test_build_dry_run_runs_nothing(repo, capsys):
    assert main(["--root", str(repo), "build", "good", "--dry-run", "--json"]) == EXIT_OK
    plan = json.loads(capsys.readouterr().out)["plan"][0]
    assert plan["config"] == "configs/lab/paper/config_good.yaml"
    assert [Path(s.split()[-1]).name for s in plan["steps"]] == [
        "good_analysis.py", "build_atlas.py", "verify_atlas.py"]
    assert calls(repo) == []


def test_build_runs_steps_in_order_with_config_path(repo, capsys):
    assert main(["--root", str(repo), "build", "good", "--json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert calls(repo) == [f"{s} configs/lab/paper/config_good.yaml"
                           for s in ("good_analysis.py", "build_atlas.py", "verify_atlas.py")]


def test_build_stops_at_failing_step(repo, capsys):
    assert main(["--root", str(repo), "build", "broken", "--json"]) == EXIT_FAILED
    result = json.loads(capsys.readouterr().out)["results"][0]
    assert result["failed_step"] == "analysis/lab/exploratory/broken_analysis.py"
    assert [c.split()[0] for c in calls(repo)] == ["broken_analysis.py"]   # publish/verify not run


def test_build_all_keeps_going_and_skips_manifest_on_failure(repo, capsys):
    assert main(["--root", str(repo), "build", "--all", "--json"]) == EXIT_FAILED
    ran = [c.split()[0] for c in calls(repo)]
    assert "good_analysis.py" in ran and "old_analysis.py" in ran    # continued past 'broken'
    assert "consolidate_manifest.py" not in ran                       # only after a clean ALL


def test_usage_errors_exit_2(repo, capsys):
    assert main(["--root", str(repo), "build"]) == EXIT_USAGE
    assert main(["--root", str(repo), "build", "missing"]) == EXIT_USAGE
    assert main(["--root", str(repo), "build", "good", "--all"]) == EXIT_USAGE
