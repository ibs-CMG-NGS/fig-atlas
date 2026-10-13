"""Run a tutorial as written (roadmap 8.2, "documents are tests").

A tutorial marks what is run with HTML comments, invisible on the page:

    <!-- run -->                      the next ```bash block: each `fa ...` line is run
    <!-- replace: <file> | <text> --> the next code block replaces the line of <file>
                                      that contains <text>

tests/test_tutorials.py runs every tutorial this way in a fresh project, and
scripts/make_reference.py does it to draw the pictures a tutorial shows, so
the pictures are what the commands on the page produce.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEP = re.compile(r"<!-- (run|replace: (?P<file>[^|]+?) \| (?P<anchor>.+?)) -->\s*```\w*\n(?P<body>.*?)```", re.S)


def steps(doc: Path) -> list[dict]:
    """The marked steps of a tutorial, in order."""
    return [{"kind": m.group(1).split(":")[0], "file": (m.group("file") or "").strip(),
             "anchor": m.group("anchor"), "body": m.group("body")}
            for m in STEP.finditer(doc.read_text(encoding="utf-8"))]


def new_project_repo(dest: Path) -> None:
    """A new project repository as `fa init` makes it, plus the example bundles --
    nothing else from this repository: no scripts/, styles/, matplotlibrc or
    .vscode/. The installed package must bring everything a build needs."""
    from fig_atlas.repo_commands import plan_init
    dest.mkdir(parents=True, exist_ok=True)
    plan_init(dest).apply()
    shutil.copytree(ROOT / "examples", dest / "examples", ignore=shutil.ignore_patterns("__pycache__"))


def replace_line(path: Path, anchor: str, body: str) -> None:
    lines = path.read_text(encoding="utf-8").split("\n")
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    assert len(hits) == 1, f"{path.name}: {len(hits)} lines contain {anchor!r}"
    lines[hits[0]:hits[0] + 1] = body.rstrip("\n").split("\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def run(doc: Path, repo: Path, after_step=None) -> list[str]:
    """Run a tutorial's marked steps in ``repo``; returns each command's output.
    Besides `fa` commands, a step may make folders and copy example data
    (`mkdir -p <dir>`, `cp -r <src> <dir>/`), done here without a shell.
    ``after_step(i, step, repo)`` is called after each step (0-based)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    outputs = []
    for i, s in enumerate(steps(doc)):
        if s["kind"] == "replace":
            replace_line(repo / s["file"], s["anchor"], s["body"])
        else:
            for line in s["body"].splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                words = shlex.split(line)
                if words[:2] == ["mkdir", "-p"]:
                    (repo / words[2]).mkdir(parents=True, exist_ok=True)
                    continue
                if words[:2] == ["cp", "-r"]:
                    src = repo / words[2]
                    shutil.copytree(src, repo / words[3] / src.name)
                    continue
                assert words[0] == "fa", f"tutorial command is not an fa, mkdir -p or cp -r command: {line}"
                res = subprocess.run([sys.executable, "-m", "fig_atlas", *words[1:]], cwd=repo, env=env,
                                     capture_output=True, text=True, encoding="utf-8", errors="replace",
                                     timeout=600)
                assert res.returncode == 0, f"$ {line}\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}"
                outputs.append(res.stdout)
        if after_step:
            after_step(i, s, repo)
    return outputs
