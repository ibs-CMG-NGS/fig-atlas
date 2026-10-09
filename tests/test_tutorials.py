"""The tutorials work as written: their commands and config edits run in a
fresh copy of the repository (roadmap 8.2, "documents are tests").

A tutorial marks what the test runs with HTML comments, invisible on the page:

    <!-- run -->                      the next ```bash block: each `fa ...` line is run
    <!-- replace: <file> | <text> --> the next code block replaces the line of <file>
                                      that contains <text>
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STEP = re.compile(r"<!-- (run|replace: (?P<file>[^|]+?) \| (?P<anchor>.+?)) -->\s*```\w*\n(?P<body>.*?)```", re.S)


def steps(doc: Path) -> list[dict]:
    return [{"kind": m.group(1).split(":")[0], "file": (m.group("file") or "").strip(),
             "anchor": m.group("anchor"), "body": m.group("body")}
            for m in STEP.finditer(doc.read_text(encoding="utf-8"))]


def _copy_repo(dest: Path) -> None:
    """A new project repository as `fa init` makes it, plus the example bundles --
    nothing else from this repository: no scripts/, styles/, matplotlibrc or
    .vscode/. The installed package must bring everything a build needs."""
    from fig_atlas.repo_commands import plan_init
    dest.mkdir(parents=True, exist_ok=True)
    plan_init(dest).apply()
    shutil.copytree(ROOT / "examples", dest / "examples", ignore=shutil.ignore_patterns("__pycache__"))


def _replace(path: Path, anchor: str, body: str) -> None:
    lines = path.read_text(encoding="utf-8").split("\n")
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    assert len(hits) == 1, f"{path.name}: {len(hits)} lines contain {anchor!r}"
    lines[hits[0]:hits[0] + 1] = body.rstrip("\n").split("\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_first_figure_tutorial(tmp_path):
    doc = ROOT / "docs" / "tutorials" / "first_figure.md"
    todo = steps(doc)
    assert sum(s["kind"] == "run" for s in todo) >= 5 and any(s["kind"] == "replace" for s in todo)
    _copy_repo(tmp_path)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    outputs = []
    for s in todo:
        if s["kind"] == "replace":
            _replace(tmp_path / s["file"], s["anchor"], s["body"])
            continue
        for line in s["body"].splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            assert line.startswith("fa "), f"tutorial command is not an fa command: {line}"
            res = subprocess.run([sys.executable, "-m", "fig_atlas", *line.split()[1:]], cwd=tmp_path, env=env,
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            assert res.returncode == 0, f"$ {line}\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}"
            outputs.append(res.stdout)

    figure = tmp_path / "outputs" / "first-figure" / "figures" / "figure_01_main"
    assert (figure / "figure_01.png").is_file() and (figure / "figure_01.pdf").is_file()
    # What the page promises: the first preflight warns about colours, the config fix clears it.
    preflights = [o for o in outputs if "error(s)," in o]
    assert "cvd_indistinct" in preflights[0]
    assert "0 error(s), 0 warning(s)" in preflights[-1]
    assert "Two compounds lower viability" in (figure / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("doc", sorted((ROOT / "docs" / "tutorials").glob("*.md")), ids=lambda p: p.name)
def test_marked_steps_parse(doc):
    """A malformed marker would silently skip a step."""
    text = doc.read_text(encoding="utf-8")
    assert text.count("<!-- run -->") + text.count("<!-- replace:") == len(steps(doc))
