"""Synthetic-data render cases for renderer snapshot tests.

One case per renderer (or per renderer mode). Each builds a small figure from
fixed synthetic data -- raw_data/ is private and git-ignored, so CI can't use
real bundles -- and returns it for snapshotting. Cases cover the tier-1
renderers of docs/reference/renderer_inventory.md (used by the compendium)
first. Parameters stay close to how the paper figures call each renderer.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fig_atlas.renderers import (
    place_panel_tags,
    render_grouped_hbar,
    render_image_panel,
    render_line_band,
    render_paired_dumbbell,
    render_signed_heatmap,
    render_stacked_share_hbar,
    render_threshold_scatter,
    render_tier_hbar,
    render_treatment_schematic,
    render_two_set_euler,
)
from fig_atlas_omics.renderers import (
    count_cluster_row_groups,
    render_binary_motif_heatmap,
    render_clustered_go_heatmap,
    render_cross_condition_dotplot,
    render_cross_condition_heatmap,
    render_ma_plot,
    render_pathway_test_matrix,
    render_species_response_scatter,
    render_tf_expression_scatter_grid,
    render_volcano,
)

CONDS = ["Acute_1D", "Acute_3D", "Chronic_24H", "Chronic_48H"]
TERMS = [f"term {chr(65 + i)} process" for i in range(8)]
TYPO = {"title_size": 8.0, "axes_label_size": 7.0, "tick_label_size": 6.0}


def _rng():
    return np.random.default_rng(20261006)


def _cross_condition_df():
    rng = _rng()
    rows = []
    for t in TERMS:
        for c in CONDS:
            if rng.random() < 0.8:
                v = float(rng.choice([-1, 1]) * rng.uniform(1.4, 6.0))
                rows.append({"GO Term": t, "Condition": c, "Signed -log10(FDR)": v,
                             "Gene Ratio": float(rng.uniform(0.02, 0.3))})
    return pd.DataFrame(rows)


def cross_condition_dotplot():
    fig, ax = plt.subplots(figsize=(3.2, 2.6))
    render_cross_condition_dotplot(ax, _cross_condition_df(), {**TYPO, "condition_order": CONDS})
    return fig


def cross_condition_heatmap():
    df = _cross_condition_df()
    params = {**TYPO, "condition_order": CONDS}
    fig = plt.figure(figsize=(3.4, 2.8))
    count_cluster_row_groups(df, params)
    render_cross_condition_heatmap(fig, df, params)
    return fig


def tf_expression_scatter_grid():
    rng = _rng()
    conds = ["Control", "Acute 1D", "Acute 3D"]
    genes = [{"symbol": s, "family": f,
              "replicates": [list(rng.normal(m, 0.4, 3)) for m in (5.0, 6.2, 5.6)]}
             for s, f in [("JUN", "bZIP"), ("KLF10", "Zf"), ("NFE2L2", "bZIP"), ("TP53", "p53")]]
    fig = plt.figure(figsize=(3.4, 2.4))
    render_tf_expression_scatter_grid(fig, genes, conds, params={
        **TYPO, "condition_colors": ["#3b73b9", "#d73027", "#f46d43"], "ylabel": "log2 normalized counts"})
    return fig


def panel_tags():
    fig = plt.figure(figsize=(3.4, 2.6))
    ax_a = fig.add_axes([0.18, 0.58, 0.30, 0.32])
    ax_b = fig.add_axes([0.65, 0.58, 0.30, 0.32])
    ax_c = fig.add_axes([0.18, 0.12, 0.77, 0.30])
    for ax, lab in [(ax_a, "a long y label"), (ax_b, "y"), (ax_c, "another y label")]:
        ax.plot([0, 1, 2], [1, 3, 2])
        ax.set_ylabel(lab, fontsize=7)
        ax.tick_params(labelsize=6)
    place_panel_tags(fig, [[("a", [ax_a]), ("c", [ax_c])], [("b", [ax_b])]], label_size=10)
    return fig


def binary_motif_heatmap():
    rng = _rng()
    genes = [f"G{i}" for i in range(10)]
    cols = ["has_AP1", "has_NRF2", "has_KLF", "has_SP1"]
    df = pd.DataFrame({"gene": genes, "tier": ["Tier 1"] * 4 + ["Tier 2"] * 6,
                       **{c: rng.random(len(genes)) < 0.5 for c in cols}})
    fig = plt.figure(figsize=(3.0, 2.6))
    render_binary_motif_heatmap(fig, df, {**TYPO, "cols": cols, "col_strip_prefix": "has_",
                                          "tier_colors": {"Tier 1": "#1d4ed8", "Tier 2": "#93c5fd"},
                                          "labels_title": "Driver motifs"})
    return fig


def tier_hbar():
    fig, ax = plt.subplots(figsize=(2.8, 1.6))
    df = pd.DataFrame({"category": ["Tier 1", "Tier 2", "Tier 3"], "count": [41, 118, 302]})
    render_tier_hbar(ax, df, {**TYPO, "order": ["Tier 1", "Tier 2", "Tier 3"],
                              "bar_colors": {"Tier 1": "#1d4ed8"}, "xlabel": "Genes"})
    return fig


def signed_heatmap():
    rng = _rng()
    vals = pd.DataFrame(rng.normal(0, 4, (6, 4)), index=[f"gene{i}" for i in range(6)], columns=CONDS)
    vals.iloc[1, 2] = np.nan
    fig, ax = plt.subplots(figsize=(2.4, 2.2))
    render_signed_heatmap(ax, vals, {**TYPO, "show_values": True, "col_labels": ["D1", "D3", "24h", "48h"]})
    return fig


def grouped_hbar():
    fig, ax = plt.subplots(figsize=(3.0, 2.0))
    df = pd.DataFrame({"category": ["promoter", "intron", "distal"],
                       "human": [52.0, 30.5, 17.5], "mouse": [21.0, 44.0, 35.0]})
    render_grouped_hbar(ax, df, {**TYPO, "series": ["human", "mouse"],
                                 "series_colors": {"human": "#2563eb", "mouse": "#dc2626"},
                                 "xlabel": "Share of peaks (%)"})
    return fig


def pathway_test_matrix():
    rng = _rng()
    cells = pd.DataFrame([{"term": t, "test": test, "value": float(rng.uniform(0.5, 6.0)),
                           "share": float(rng.uniform(0.05, 0.6)), "sig": bool(rng.random() < 0.6)}
                          for t in TERMS[:5] for test in ("ORA", "GSEA")])
    fig, (ax, cax) = plt.subplots(1, 2, figsize=(3.0, 2.2), gridspec_kw={"width_ratios": [8, 1]})
    render_pathway_test_matrix(ax, cells, {**TYPO, "term_order": TERMS[:5], "test_order": ["ORA", "GSEA"],
                                           "vmin": 1.3}, cax=cax)
    return fig


def two_set_euler():
    fig, ax = plt.subplots(figsize=(2.4, 2.0))
    render_two_set_euler(ax, n_total=1200, n_a_only=180, n_b_only=760, n_both=140,
                         params={**TYPO, "a_label": "In pathway", "b_label": "Driver motif",
                                 "both_note": "core 68"})
    return fig


def stacked_share_hbar():
    counts = pd.DataFrame({"up": [120, 40, 12], "flat": [300, 410, 150], "down": [80, 50, 238]},
                          index=["Acute 1D", "Acute 3D", "Chronic 24h"])
    fig, ax = plt.subplots(figsize=(3.0, 1.6))
    render_stacked_share_hbar(ax, counts, {**TYPO, "group_order": list(counts.index),
                                           "category_order": ["up", "flat", "down"],
                                           "colors": {"up": "#d73027", "flat": "#e5e7eb", "down": "#4575b4"},
                                           "dark_categories": ["up", "down"]})
    return fig


def clustered_go_heatmap():
    rng = _rng()
    mat = rng.normal(0, 3, (6, 8))
    fig, ax = plt.subplots(figsize=(3.2, 2.2))
    render_clustered_go_heatmap(ax, mat, TERMS[:6], {**TYPO}, cond_names=["D1", "D3", "24h", "48h"])
    return fig


def paired_dumbbell():
    rng = _rng()
    counts = {s: {c: (int(rng.integers(5, 900)), int(rng.integers(5, 900))) for c in CONDS}
              for s in ("human_rna", "mouse_rna", "human_atac", "mouse_atac")}
    fig = plt.figure(figsize=(3.6, 2.8))
    gs = fig.add_gridspec(1, 1)
    render_paired_dumbbell(fig=fig, gs_target=gs[0, 0], counts=counts, conditions=CONDS,
                           params={"header_fontsize": 7.0, "ylabel_fontsize": 6.5, "xlabel_fontsize": 6.0,
                                   "ytick_fontsize": 6.0, "xtick_fontsize": 6.0, "annot_fontsize": 5.5,
                                   "legend_fontsize": 6.0, "marker_size": 20},
                           cond_rename={"Acute_1D": "Acute D1", "Acute_3D": "Acute D3",
                                        "Chronic_24H": "Chronic 24h", "Chronic_48H": "Chronic 48h"})
    return fig


def species_response_scatter():
    rng = _rng()
    n = 120
    df = pd.DataFrame({"x": rng.normal(0, 1.5, n), "y": rng.normal(0, 1.5, n),
                       "category": rng.choice(["neither", "human_only", "both_same"], n, p=[0.7, 0.2, 0.1])})
    fig, ax = plt.subplots(figsize=(2.4, 2.4))
    render_species_response_scatter(ax, df, {**TYPO, "category_order": ["neither", "human_only", "both_same"],
                                             "colors": {"neither": "#d1d5db", "human_only": "#2563eb",
                                                        "both_same": "#16a34a"},
                                             "xlabel": "Human log2FC", "ylabel": "Mouse log2FC",
                                             "rasterized": False})
    return fig


def treatment_schematic():
    fig, (ax_l, ax_b) = plt.subplots(1, 2, figsize=(3.6, 1.6), gridspec_kw={"width_ratios": [1, 4]})
    render_treatment_schematic(ax_l, ax_b, {"tick_fontsize": 6.0, "label_fontsize": 6.0,
                                            "legend_fontsize": 6.0, "circle_size": 60})
    return fig


def _de_table(n=240):
    rng = _rng()
    lfc = rng.normal(0, 1.4, n)
    padj = np.clip(10 ** (-np.abs(lfc) * rng.uniform(0.5, 6, n)), 1e-280, 1)
    return pd.DataFrame({"log2FC": lfc, "padj": padj, "symbol": [f"G{i}" for i in range(n)],
                         "baseMean": 10 ** rng.uniform(-1, 5, n), "log2FoldChange": lfc})


def volcano():
    """The volcano recipe (threshold scatter), with adjustText labels."""
    fig, ax = plt.subplots(figsize=(3.0, 2.6))
    render_volcano(ax, _de_table(), {"annotation_mode": "top_n", "annotation_top_n": 6, "dot_size": 6})
    return fig


def ma_plot():
    """The MA recipe (threshold scatter)."""
    fig, ax = plt.subplots(figsize=(3.0, 2.6))
    render_ma_plot(ax, _de_table(), {"dot_size": 4})
    return fig


def threshold_scatter():
    """The generic renderer outside omics: effect size vs P of any test."""
    rng = _rng()
    d = rng.normal(0, 0.6, 150)
    df = pd.DataFrame({"cohen_d": d, "p": np.clip(10 ** (-np.abs(d) * rng.uniform(1, 4, 150)), 1e-12, 1),
                       "marker": [f"m{i}" for i in range(150)]})
    fig, ax = plt.subplots(figsize=(3.0, 2.6))
    render_threshold_scatter(ax, df, {**TYPO, "x_col": "cohen_d", "y_col": "p", "y_transform": "neg_log10",
                                      "effect_col": "cohen_d", "sig_col": "p", "effect_threshold": 0.5,
                                      "sig_threshold": 0.01, "dot_size": 8,
                                      "cutoff_lines": [{"axis": "v", "at": "effect"}, {"axis": "v", "at": "-effect"},
                                                       {"axis": "h", "at": "sig"}],
                                      "labels_xlabel": "Cohen's d", "labels_ylabel": "-log10 P"})
    return fig


def line_band():
    """Replicate time course, two groups: mean +/- SEM bands with the replicates."""
    rng = _rng()
    t = np.repeat([0, 1, 2, 4, 8], 3)
    df = pd.concat([pd.DataFrame({"hours": t, "signal": 1 + k * np.log1p(t) + rng.normal(0, 0.25, t.size),
                                  "arm": arm}) for k, arm in ((0.2, "vehicle"), (0.8, "treated"))])
    fig, ax = plt.subplots(figsize=(2.8, 2.2))
    render_line_band(ax, df, {**TYPO, "x_col": "hours", "y_col": "signal", "group_col": "arm",
                              "show_points": True, "point_jitter": 0.08,
                              "group_colors": {"vehicle": "#6b7280", "treated": "#dc2626"},
                              "labels_xlabel": "Time (h)", "labels_ylabel": "Signal (a.u.)"})
    return fig


def image_panel():
    """Two synthetic channels (nuclei, cytoplasm) tinted and combined, with a scale bar."""
    import tempfile
    from pathlib import Path

    from PIL import Image
    rng = _rng()
    yy, xx = np.mgrid[0:120, 0:160]
    nuc = np.zeros((120, 160))
    cyto = np.zeros((120, 160))
    for cx, cy in rng.uniform([20, 20], [140, 100], size=(6, 2)):
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2
        nuc += 3000 * np.exp(-r2 / 60)
        cyto += 1500 * np.exp(-r2 / 400)
    tmp = Path(tempfile.mkdtemp())
    for name, arr in (("nuc", nuc), ("cyto", cyto)):
        Image.fromarray((arr + rng.normal(100, 20, arr.shape)).clip(0, 65535).astype(np.uint16)).save(tmp / f"{name}.tif")
    fig, ax = plt.subplots(figsize=(2.4, 1.9))
    render_image_panel(ax, [tmp / "nuc.tif", tmp / "cyto.tif"],
                       {"channel_colors": ["#3b82f6", "#22c55e"], "channel_labels": ["DAPI", "tubulin"],
                        "display_ranges": [[100, 3000], [100, 1600]], "show_channel_labels": True,
                        "pixel_size": 0.25, "scale_bar": 10, "panel": "a"})
    return fig


CASES = {
    "cross_condition_dotplot": cross_condition_dotplot,
    "cross_condition_heatmap": cross_condition_heatmap,
    "tf_expression_scatter_grid": tf_expression_scatter_grid,
    "panel_tags": panel_tags,
    "binary_motif_heatmap": binary_motif_heatmap,
    "tier_hbar": tier_hbar,
    "signed_heatmap": signed_heatmap,
    "grouped_hbar": grouped_hbar,
    "pathway_test_matrix": pathway_test_matrix,
    "two_set_euler": two_set_euler,
    "stacked_share_hbar": stacked_share_hbar,
    "clustered_go_heatmap": clustered_go_heatmap,
    "paired_dumbbell": paired_dumbbell,
    "species_response_scatter": species_response_scatter,
    "treatment_schematic": treatment_schematic,
    "volcano": volcano,
    "ma_plot": ma_plot,
    "threshold_scatter": threshold_scatter,
    "line_band": line_band,
    "image_panel": image_panel,
}
