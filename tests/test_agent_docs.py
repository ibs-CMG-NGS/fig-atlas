"""The rules have one source, AGENTS.md, and it names things that exist
(docs/decisions/0005).

Agents act on what this file and the skill documents say, so a path that no
longer exists or a command that was renamed sends them the wrong way silently.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest

from fig_atlas.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
DOCS = [ROOT / "AGENTS.md", *sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md"))]
TOP = ("configs", "analysis", "figure_specs", "fig_atlas", "fig_atlas_omics", "scripts", "docs", "styles", "tests",
       ".agents", ".vscode", ".gemini")
PATH = re.compile(r"`((?:%s)/[^`\s]*)`" % "|".join(re.escape(t) for t in TOP))
FA = re.compile(r"`fa ([a-z][a-z-]*)(?: ([a-z][a-z-]*))?")
INSIDE_A_BUNDLE = {"scripts/figure.py"}      # a file inside data bundles, not this repository
# Standard places of a project repository, named by the rules whether or not this
# repository has them (the package repository keeps no storyline or VS Code list).
PROJECT_LAYOUT = ("docs/storylines", "docs/storyline", "docs/data_contracts", ".vscode/")


def _ids(paths):
    return [p.relative_to(ROOT).as_posix() for p in paths]


def test_claude_md_only_imports_agents_md():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@AGENTS.md" in text.split()
    assert len(text.splitlines()) < 15, "rules belong in AGENTS.md; CLAUDE.md only imports it"
    assert not (ROOT / ".agents" / "AGENTS.md").exists(), "a second copy of the rules"


def test_gemini_reads_agents_md():
    settings = json.loads((ROOT / ".gemini" / "settings.json").read_text(encoding="utf-8"))
    assert "AGENTS.md" in settings["context"]["fileName"]


@pytest.mark.parametrize("doc", DOCS, ids=_ids(DOCS))
def test_named_paths_exist(doc):
    text = doc.read_text(encoding="utf-8")
    missing = []
    for m in PATH.finditer(text):
        p = m.group(1).rstrip(".,:;)")
        if any(c in p for c in "<>*{}[]") or p in INSIDE_A_BUNDLE or p.startswith(PROJECT_LAYOUT):
            continue                                  # a pattern, not a file
        if not (ROOT / p).exists():
            missing.append(p)
    assert not missing, f"{doc.name} names paths that do not exist: {missing}"


@pytest.mark.parametrize("doc", DOCS, ids=_ids(DOCS))
def test_named_fa_commands_exist(doc):
    sub = next(a for a in build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    bad = []
    for m in FA.finditer(doc.read_text(encoding="utf-8")):
        cmd, word = m.groups()
        if cmd not in sub.choices:
            bad.append(f"fa {cmd}")
            continue
        first = next((a for a in sub.choices[cmd]._actions if not a.option_strings and a.choices), None)
        if word and first is not None and word not in first.choices:
            bad.append(f"fa {cmd} {word}")
    assert not bad, f"{doc.name} names commands the CLI does not have: {bad}"
