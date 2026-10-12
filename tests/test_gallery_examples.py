"""Every example bundle in examples/gallery/ meets its contract and builds
clean at single-column size, as the gallery page shows it."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from fig_atlas.bundle_figure import draw_bundle  # noqa: E402
from fig_atlas.contracts import check_bundle  # noqa: E402
from fig_atlas.preflight import preflight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted(p for p in (ROOT / "examples" / "gallery").iterdir() if p.is_dir())
RC = {"font.size": 7, "axes.titlesize": 8, "axes.labelsize": 7, "xtick.labelsize": 6, "ytick.labelsize": 6,
      "legend.fontsize": 6}


def test_there_are_examples():
    assert len(EXAMPLES) >= 10


@pytest.mark.parametrize("bundle", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_builds_clean(bundle):
    report = check_bundle(bundle)
    assert report.contract is not None and not [f for f in report.findings if f.level == "error"]
    with plt.rc_context(RC):
        fig = draw_bundle(bundle, root=ROOT)
        bad = [f"{f.check}: {f.message}" for f in preflight(fig, saved_bbox_in=None)
               if f.severity in ("error", "warn")]
        plt.close(fig)
    assert not bad, bad
