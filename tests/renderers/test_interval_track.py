"""render_interval_track draws boxes, brackets and points, coloured by kind."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas_omics.renderers import render_interval_track  # noqa: E402

IV = pd.DataFrame({"start": [100, 150, 5000], "end": [900, 400, 5000],
                   "kind": ["del", "sv", "junction"], "label": ["Δ800 bp", "", "J1"]})


def test_overlaps_go_to_separate_rows_and_points_are_markers():
    fig, ax = plt.subplots()
    out = render_interval_track(ax, IV, {"x_min": 0, "x_max": 10000, "bracket_kinds": ["del"]})
    rows = out.set_index("kind")["row"]
    assert rows["del"] != rows["sv"]
    assert len(ax.patches) == 1                       # sv box; del is a bracket, junction a triangle
    assert ax.get_legend() is not None
    plt.close(fig)
