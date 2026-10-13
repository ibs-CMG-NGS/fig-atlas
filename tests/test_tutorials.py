"""The tutorials work as written: their commands and config edits run in a
fresh copy of the repository (roadmap 8.2, "documents are tests"). How steps
are marked and run: fig_atlas.tools.tutorial.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from fig_atlas.tools.tutorial import new_project_repo as _copy_repo
from fig_atlas.tools.tutorial import run as _run_tutorial
from fig_atlas.tools.tutorial import steps

ROOT = Path(__file__).resolve().parents[1]


def test_first_figure_tutorial(tmp_path):
    doc = ROOT / "docs" / "tutorials" / "first_figure.md"
    todo = steps(doc)
    assert sum(s["kind"] == "run" for s in todo) >= 5 and any(s["kind"] == "replace" for s in todo)
    _copy_repo(tmp_path)
    outputs = _run_tutorial(doc, tmp_path)

    figure = tmp_path / "outputs" / "first-figure" / "figures" / "figure_01_main"
    assert (figure / "figure_01.png").is_file() and (figure / "figure_01.pdf").is_file()
    # What the page promises: the first preflight warns about colours, the config fix clears it.
    preflights = [o for o in outputs if "error(s)," in o]
    assert "cvd_indistinct" in preflights[0]
    assert "0 error(s), 1 warning(s)" in preflights[0]                 # the output step 4 shows, and nothing else:
    assert "title_misaligned" not in preflights[0]                    # panel titles from one preset size
    assert "text_on_frame" not in preflights[0]                       # point labels inside the frame
    assert "old matplotlib" not in "".join(outputs)                   # adjustText's message is quieted
    assert "0 error(s), 0 warning(s)" in preflights[-1]
    assert "PASS: 5/5" in preflights[-1]                              # step 6 ends with no warning left
    assert "Two compounds lower viability" in (figure / "README.md").read_text(encoding="utf-8")


def test_data_change_tutorial(tmp_path):
    """Promotion, a storyline, a changed delivery found by status and impact,
    a rebuild and a revision: two compendium snapshots, the diff names the input."""
    _copy_repo(tmp_path)
    out = "\n".join(_run_tutorial(ROOT / "docs" / "tutorials" / "data_change.md", tmp_path))
    assert out.count("STALE  outputs/lab/") == 2                     # the paper figure and the QC figure
    assert "2 figure(s) affected" in out and "old output folder(s)" in out
    assert "Revision (1)" in out                                     # the suggested entry
    snaps = tmp_path / "outputs" / "storylines" / "figure_plan_dose"
    assert (snaps / "R000").is_dir() and (snaps / "R001").is_dir()
    assert (tmp_path / "docs" / "storylines" / "dose" / "revisions" / "R001.md").is_file()
    assert "input changed: `raw_data/dose-study/dose_response/inputs/data.csv`" in out


@pytest.mark.parametrize("doc", sorted((ROOT / "docs" / "tutorials").glob("*.md")), ids=lambda p: p.name)
def test_marked_steps_parse(doc):
    """A malformed marker would silently skip a step."""
    text = doc.read_text(encoding="utf-8")
    assert text.count("<!-- run -->") + text.count("<!-- replace:") == len(steps(doc))
