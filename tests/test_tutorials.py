"""The tutorials work as written: their commands and config edits run in a
fresh copy of the repository (roadmap 8.2, "documents are tests"). How steps
are marked and run: fig_atlas.tools.tutorial.
"""
from __future__ import annotations

import re
import shutil
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


FILE_BLOCK = re.compile(r"<!-- file: (?P<path>\S+) -->\s*```\w*\n(?P<body>.*?)```", re.S)


@pytest.mark.parametrize("doc", sorted((ROOT / "docs" / "tutorials").glob("*.md")), ids=lambda p: p.name)
def test_quoted_files_are_current(doc):
    """A code block marked <!-- file: path --> shows that file exactly, so the page
    cannot drift from the example it explains."""
    for m in FILE_BLOCK.finditer(doc.read_text(encoding="utf-8")):
        real = (ROOT / m.group("path")).read_text(encoding="utf-8").replace("\r\n", "\n")
        assert m.group("body") == real, f"{doc.name}: the block for {m.group('path')} differs from the file"


def _content(ax) -> dict:
    """What a bar chart shows, without its size: bars (height, colour) left to
    right, error bar spans, dots, axis range and texts."""
    from matplotlib.colors import to_hex
    from matplotlib.container import BarContainer
    bars = sorted((r.get_x() + r.get_width() / 2, round(r.get_height(), 6), to_hex(r.get_facecolor()))
                  for c in ax.containers if isinstance(c, BarContainer) for r in c)
    spans = sorted(round(float(s[1][1] - s[0][1]), 6) for c in ax.containers
                   if getattr(c, "errorbar", None) is not None
                   for s in c.errorbar.lines[2][0].get_segments())
    dots = sorted(round(float(y), 6) for coll in ax.collections for _, y in coll.get_offsets())
    leg = ax.get_legend()
    return {"bars": [(h, col) for _, h, col in bars], "error_spans": spans, "dots": dots,
            "ylim": tuple(round(v, 6) for v in ax.get_ylim()),
            "xticks": [t.get_text() for t in ax.get_xticklabels()],
            "title": (ax.get_title(), ax.title.get_fontweight()), "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(),
            "legend": [t.get_text() for t in leg.get_texts()] if leg else []}


def test_case_a_tutorial(tmp_path, monkeypatch):
    """The ported figure shows what the student's script showed: same bars,
    error bars, dots, colours, order, axis range and texts (AGENTS.md 3, Case A);
    and the bundle's data is the script's CSV, byte for byte."""
    import runpy

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    import fig_atlas
    from fig_atlas import ProjectConfig

    _copy_repo(tmp_path)
    out = "\n".join(_run_tutorial(ROOT / "docs" / "tutorials" / "case_a_port_script.md", tmp_path))
    assert "0 error(s), 0 warning(s)" in out and "PASS: 5/5" in out
    bundle = tmp_path / "raw_data" / "qpcr-antioxidant" / "qpcr_bundle"
    original = ROOT / "examples" / "case_a" / "original"
    assert (bundle / "inputs" / "data.csv").read_bytes() == (original / "qpcr_results.csv").read_bytes()

    script_dir = tmp_path / "original"
    shutil.copytree(original, script_dir)
    monkeypatch.chdir(script_dir)
    monkeypatch.setattr(plt, "savefig", lambda *a, **k: None)
    plt.close("all")
    runpy.run_path(str(script_dir / "plot_qpcr.py"), run_name="__main__")
    before = _content(plt.gcf().axes[0])
    plt.close("all")

    block = dict(ProjectConfig(tmp_path / "configs" / "config_qpcr-antioxidant.yaml").settings["plots"]["qpcr"])
    block.pop("renderer"), block.pop("bundle")
    fig, ax = plt.subplots()
    fig_atlas.render("bar_scatter", ax, pd.read_csv(bundle / "inputs" / "data.csv"), block)
    after = _content(ax)
    plt.close(fig)
    assert after == before

