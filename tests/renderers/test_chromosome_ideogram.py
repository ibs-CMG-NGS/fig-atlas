"""render_chromosome_ideogram draws bands, markers and a zoomed ruler."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas_omics.renderers import render_chromosome_ideogram  # noqa: E402

BANDS = pd.DataFrame({"start": [1, 1001, 3001], "end": [1000, 3000, 5000],
                      "band": ["qA1", "qA2", "qA3"], "gie_stain": ["gpos100", "gneg", "gpos50"]})


def test_whole_chromosome_with_a_marker():
    fig, ax = plt.subplots()
    out = render_chromosome_ideogram(ax, BANDS, {"labels_title": "Chromosome 2"},
                                     markers=pd.DataFrame({"pos": [2500], "label": ["Tg"]}))
    assert ax.get_xlim() == (0.0, 5000.0)
    assert list(out["pos"]) == [2500.0] and out["y_top"].iloc[0] > 0.4
    assert {"qA1", "qA2", "qA3", "Chromosome 2", "Tg"} <= {t.get_text() for t in ax.texts}
    plt.close(fig)


def test_zoomed_window_shows_only_its_bands():
    fig, ax = plt.subplots()
    render_chromosome_ideogram(ax, BANDS, {"x_min": 1200, "x_max": 2800, "show_ruler": True,
                                           "band_label_position": "inside", "ruler_unit_bp": 1e3,
                                           "ruler_suffix": " kb"})
    assert {t.get_text() for t in ax.texts} == {"qA2"}
    assert ax.get_xlim() == (1200.0, 2800.0)
    plt.close(fig)
