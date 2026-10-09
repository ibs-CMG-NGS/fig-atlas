"""Renderer regression tests: each case's structural snapshot must match the
committed one in tests/renderers/snapshots/.

Update after an intended visual change:
    FA_UPDATE_SNAPSHOTS=1 python -m pytest tests/renderers
and review the snapshot diff in git. A PNG of every case is written to
outputs/renderer_snapshots/ for eyeballing (git-ignored).
"""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.testing import set_font_settings_for_testing, set_reproducibility_for_testing  # noqa: E402

from cases import CASES  # noqa: E402
from snapshot import compare, figure_snapshot, load, save  # noqa: E402

HERE = Path(__file__).resolve().parent
SNAPSHOTS = HERE / "snapshots"
PNG_DIR = HERE.parents[1] / "outputs" / "renderer_snapshots"
UPDATE = os.environ.get("FA_UPDATE_SNAPSHOTS") == "1"


@pytest.fixture(autouse=True)
def _clean_rc():
    # Matplotlib defaults (not the repo matplotlibrc or a previous test's
    # rcParams), DejaVu Sans with hinting off as in matplotlib's own tests.
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        set_font_settings_for_testing()
        set_reproducibility_for_testing()
        yield
    plt.close("all")


@pytest.mark.parametrize("name", sorted(CASES))
def test_renderer_snapshot(name):
    fig = CASES[name]()
    fig.set_dpi(100)
    snap = figure_snapshot(fig)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_DIR / f"{name}.png", dpi=150)

    path = SNAPSHOTS / f"{name}.json"
    if UPDATE or not path.exists():
        save(path, snap)
        if not UPDATE:
            pytest.fail(f"no snapshot for {name}; wrote {path.name} -- review and commit it")
        return
    diffs = compare(load(path), snap)
    assert not diffs, f"{name} rendering changed:\n  " + "\n  ".join(diffs)
