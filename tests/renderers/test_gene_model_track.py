"""render_gene_model_track keeps one transcript per gene and packs rows."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fig_atlas_omics.renderers import render_gene_model_track  # noqa: E402

EXONS = pd.DataFrame({
    "gene_name": ["A", "A", "A", "B", "Gm1"],
    "transcript_id": ["a1", "a1", "a2", "b1", "g1"],
    "strand": ["+", "+", "+", "-", "+"],
    "exon_start": [100, 800, 100, 300, 5000],
    "exon_end": [200, 1000, 150, 600, 5100],
})


def test_longest_transcript_and_overlap_rows():
    fig, ax = plt.subplots()
    tx = render_gene_model_track(ax, EXONS, {"x_min": 0, "x_max": 6000})
    assert set(tx["transcript_id"]) == {"a1", "b1", "g1"}
    rows = tx.set_index("gene")["row"]
    assert rows["A"] != rows["B"]                     # A and B overlap
    plt.close(fig)


def test_hide_pattern_drops_genes():
    fig, ax = plt.subplots()
    tx = render_gene_model_track(ax, EXONS, {"hide_pattern": "^Gm"})
    assert "Gm1" not in set(tx["gene"])
    plt.close(fig)
