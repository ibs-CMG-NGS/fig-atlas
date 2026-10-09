"""Find and build projects: the logic behind ``fa build`` / ``fa list``.

A project is one ``configs/**/config_<name>.yaml``. Building it runs the
analysis script named in ``project.analysis_script``, then publish
(``fig_atlas.tools.build_atlas``) and verify (``fig_atlas.tools.verify_atlas``),
each in a child process with ``CONFIG_PATH`` pointing at the config.

A *project repository* is the folder holding ``configs/`` (and analysis/,
figure_specs/, raw_data/, outputs/); `fa init` makes one. It is marked by a
``.fig-atlas`` file, or -- in repositories from before the package was split
out -- by ``scripts/build_atlas.py``.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml


MARKER = ".fig-atlas"                    # marks a project repository (written by `fa init`)
# The tool steps of a build, run as `python <step...>` in the project repository.
PUBLISH_STEP = ("-m", "fig_atlas.tools.build_atlas")
PREFLIGHT_STEP = ("-m", "fig_atlas.tools.preflight")
VERIFY_STEP = ("-m", "fig_atlas.tools.verify_atlas")
MANIFEST_STEP = ("-m", "fig_atlas.tools.consolidate_manifest")


class ProjectError(Exception):
    """A project can't be found or its config is unusable."""


def find_root(start: Path | None = None) -> Path:
    """The repository holding the projects: the nearest ancestor of ``start``
    (default: the working directory) with a ``configs/`` folder and a
    ``.fig-atlas`` marker (or, in older repositories, ``scripts/build_atlas.py``)."""
    here = (start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "configs").is_dir() and ((p / MARKER).is_file() or (p / "scripts" / "build_atlas.py").is_file()):
            return p
    raise ProjectError(f"no fig-atlas project repository (configs/ + {MARKER}) at or above {here}; "
                       "`fa init` makes one")


@dataclass(frozen=True)
class Project:
    name: str
    config: Path              # absolute
    namespace: str            # e.g. "lab/paper"; "" for flat/sandbox configs
    analysis_script: str | None
    archived: bool

    def config_rel(self, root: Path) -> str:
        return self.config.relative_to(root).as_posix()


def _load(root: Path, cfg: Path) -> Project:
    try:
        raw = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ProjectError(f"{cfg.relative_to(root)}: invalid YAML ({exc})") from exc
    parts = cfg.relative_to(root / "configs").parts[:-1]
    stem = cfg.stem
    name = stem[len("config_"):] if stem.startswith("config_") else "default"
    return Project(name=name, config=cfg, namespace="/".join(parts),
                   analysis_script=(raw.get("project") or {}).get("analysis_script"),
                   archived="archive" in parts)


def list_projects(root: Path) -> list[Project]:
    """Every project config under configs/, sorted by name."""
    return sorted((_load(root, c) for c in (root / "configs").rglob("config_*.yaml")),
                  key=lambda p: p.name)


def find_project(root: Path, name: str) -> Project:
    """Look a project up by its bare name, at any namespace depth."""
    found = sorted((root / "configs").rglob(f"config_{name}.yaml"))
    if not found:
        raise ProjectError(f"no config for project '{name}' (searched configs/**/config_{name}.yaml)")
    if len(found) > 1:
        where = ", ".join(p.relative_to(root).as_posix() for p in found)
        raise ProjectError(f"project name '{name}' is ambiguous: {where}")
    return _load(root, found[0])


def build_env(base: dict | None = None) -> dict:
    """Environment for child build steps.

    - On Windows conda envs, matplotlib's freetype/png/zlib DLLs live in
      <env>/Library/bin, which must be on PATH when python.exe is called
      without ``conda activate``; use the env of the running interpreter.
    - SOURCE_DATE_EPOCH=0 keeps PDF/SVG creation dates fixed, so unchanged
      inputs rebuild to byte-identical files (see matplotlibrc).
    - MATPLOTLIBRC points at the package's matplotlibrc (Type 42 PDF fonts,
      fixed SVG hash salt), used when the project repository has none of its
      own -- matplotlib reads ./matplotlibrc in the working directory first.
    """
    env = dict(os.environ if base is None else base)
    lib_bin = Path(sys.executable).resolve().parent / "Library" / "bin"
    if lib_bin.is_dir() and str(lib_bin) not in env.get("PATH", ""):
        env["PATH"] = str(lib_bin) + os.pathsep + env.get("PATH", "")
    env.setdefault("SOURCE_DATE_EPOCH", "0")
    env.setdefault("MATPLOTLIBRC", str(Path(__file__).with_name("matplotlibrc")))
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def build_steps(root: Path, project: Project, preflight: bool = False) -> list[list[str]]:
    """The commands ``build_project`` runs, in order (argv lists). With
    ``preflight``, ``fa preflight`` runs after publishing and before verify,
    so verify reports on fresh results (it never fails the build itself;
    verify does, under ``preflight.mode: enforce``)."""
    if not project.analysis_script:
        raise ProjectError(f"{project.config_rel(root)}: project.analysis_script is missing")
    if not (root / project.analysis_script).is_file():
        raise ProjectError(f"{project.config_rel(root)}: analysis_script {project.analysis_script} does not exist")
    py = sys.executable
    # The analysis script runs under the provenance recorder (no script
    # changes): every figure it saves gets a <stem>.provenance.json, which
    # publish copies beside the published figure.
    steps = [[py, "-m", "fig_atlas.provenance", project.analysis_script], [py, *PUBLISH_STEP]]
    if preflight:
        steps.append([py, *PREFLIGHT_STEP, "--projects", project.name, "--report-only"])
    return steps + [[py, *VERIFY_STEP]]


@dataclass
class BuildResult:
    project: str
    ok: bool
    seconds: float
    failed_step: str | None = None
    output_tail: str = ""
    steps: list[str] = field(default_factory=list)


def step_name(argv: list[str]) -> str:
    """What a build step runs: the analysis script for ``-m fig_atlas.provenance
    <script>``, the module for ``-m <module>``, else the script path."""
    if argv[1:3] == ["-m", "fig_atlas.provenance"]:
        return argv[3]
    return argv[2] if argv[1] == "-m" else argv[1]


def build_project(root: Path, project: Project, capture: bool = False, preflight: bool = False) -> BuildResult:
    """Run analysis -> publish -> verify; stop at the first failing step.

    With ``capture`` the children's output is collected (its tail is kept for
    the report) instead of streamed to this process's stdout.
    """
    env = build_env()
    env["CONFIG_PATH"] = project.config_rel(root)
    start = time.monotonic()
    steps = build_steps(root, project, preflight=preflight)
    done: list[str] = []
    for argv in steps:
        proc = subprocess.run(argv, cwd=root, env=env, text=True, encoding="utf-8", errors="replace",
                              stdout=subprocess.PIPE if capture else None,
                              stderr=subprocess.STDOUT if capture else None)
        done.append(step_name(argv))
        if proc.returncode != 0:
            tail = (proc.stdout or "")[-2000:] if capture else ""
            return BuildResult(project.name, False, time.monotonic() - start, step_name(argv), tail, done)
    return BuildResult(project.name, True, time.monotonic() - start, steps=done)
