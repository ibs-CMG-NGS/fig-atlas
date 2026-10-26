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


# ----------------------------------------------------------------------------
# Every other registered renderer, so the gallery shows each one
# (tests/test_gallery_coverage.py fails on a renderer with no picture).
# ----------------------------------------------------------------------------
def paired_dumbbell_4x1():
    """Counts stacked for one journal column (facet_layout 4x1)."""
    rng = _rng()
    counts = {s: {c: (int(10 ** rng.uniform(0.7, 3.2)), int(10 ** rng.uniform(0.7, 3.2))) for c in CONDS}
              for s in ("human_rna", "mouse_rna", "human_atac", "mouse_atac")}
    fig = plt.figure(figsize=(3.0, 5.4))
    render_paired_dumbbell(fig=fig, gs_target=fig.add_gridspec(1, 1)[0, 0], counts=counts, conditions=CONDS,
                           params={"facet_layout": "4x1", "mouse_annot_below": True, "y_margin": 0.6, "header_fontsize": 7.0, "ylabel_fontsize": 6.5,
                                   "xlabel_fontsize": 6.0, "ytick_fontsize": 6.0, "xtick_fontsize": 6.0,
                                   "annot_fontsize": 5.5, "legend_fontsize": 6.0, "marker_size": 20,
                                   "hspace": 0.6, "legend_row_ratio": 0.4},
                           cond_rename={"Acute_1D": "Acute D1", "Acute_3D": "Acute D3",
                                        "Chronic_24H": "Chronic 24h", "Chronic_48H": "Chronic 48h"})
    return fig


def flow_diagram():
    """Boxes, a dashed group and labelled arrows, laid out in mm."""
    from fig_atlas.renderers import render_flow_diagram
    nodes = pd.DataFrame([
        {"id": "inputs", "x": 2, "y": 2, "w": 22, "h": 14, "title": "Inputs", "body": "data, config"},
        {"id": "build", "x": 30, "y": 0, "w": 34, "h": 34, "title": "fa build", "kind": "group"},
        {"id": "run", "x": 34, "y": 7, "w": 26, "h": 10, "title": "Run", "body": "script"},
        {"id": "check", "x": 34, "y": 21, "w": 26, "h": 10, "title": "Check", "body": "preflight"},
        {"id": "out", "x": 70, "y": 2, "w": 22, "h": 14, "title": "Figure", "body": "with its record",
         "fill": "#E0F2FE"},
    ])
    fig, ax = plt.subplots(figsize=(3.8, 1.6))
    render_flow_diagram(ax, nodes, {"xlim": [0, 94], "ylim": [0, 36], "y_down": True, "units_per_mm": 1.0,
                                    "title_size": 7.0, "body_size": 6.0, "edge_label_size": 6.0,
                                    "edges": [{"from": "inputs", "to": "run", "label": "read"},
                                              {"from": "run", "to": "check"},
                                              {"from": "check", "to": "out", "from_side": "r", "to_side": "b",
                                               "route": "elbow"}]})
    return fig


def dot_matrix():
    """Genes x features: dot area from a count, colour from where the variants come from."""
    from fig_atlas.renderers import render_dot_matrix
    rng = _rng()
    genes, feats = [f"Gene{i}" for i in range(6)], ["5'UTR", "CDS", "intron", "3'UTR"]
    rows = [{"gene": g, "feature": f, "n": int(rng.integers(1, 8)), "origin": str(rng.choice(["germline", "somatic"])),
             "sample": "S1" if i < 3 else "S2"}
            for i, g in enumerate(genes) for f in feats if rng.random() < 0.55]
    fig, ax = plt.subplots(figsize=(2.8, 2.4))
    render_dot_matrix(ax, pd.DataFrame(rows), {**TYPO, "row_col": "gene", "col_col": "feature", "size_col": "n",
                                               "color_col": "origin", "row_group_col": "sample",
                                               "color_map": {"germline": "#2563eb", "somatic": "#dc2626"}})
    return fig


def funnel():
    """A filtering cascade, largest step first."""
    from fig_atlas.renderers import render_funnel
    fig, ax = plt.subplots(figsize=(2.8, 2.0))
    render_funnel(ax, [("All peaks", 48210), ("DA (FDR < 0.05)", 9120), ("Near a TSS", 3104), ("Linked gene", 812)],
                  {**TYPO, "bar_color": "#2563eb", "value_fontsize": 6.0, "labels_title": "Peaks kept per step"})
    return fig


def jaccard_heatmap():
    """Overlap between two classifications: Jaccard index (shared count) per cell."""
    from fig_atlas.renderers import render_jaccard_heatmap
    rng = _rng()
    rows, cols = ["sustained", "transient", "late"], ["concordant", "RNA only", "ATAC only"]
    df = pd.DataFrame([{"pattern_class": r, "concordance_class": c, "jaccard": float(rng.uniform(0, 0.6)),
                        "n_shared_terms": int(rng.integers(0, 40))} for r in rows for c in cols])
    df.loc[4, "n_shared_terms"] = 0
    fig, ax = plt.subplots(figsize=(2.8, 2.2))
    render_jaccard_heatmap(ax, df, {**TYPO, "row_order": rows, "col_order": cols, "cell_text_size": 5.5,
                                    "colorbar_label": "Jaccard index", "labels_title": "Shared GO terms"})
    return fig


def sample_metric_bars():
    """One bar per sample, grouped, with a reference line."""
    from fig_atlas.renderers import render_sample_metric_bars
    rng = _rng()
    df = pd.DataFrame({"sample": [f"{g}{i}" for g in ("C", "T") for i in (1, 2, 3)],
                       "group": ["control"] * 3 + ["treated"] * 3, "value": rng.uniform(0.18, 0.42, 6)})
    fig, ax = plt.subplots(figsize=(2.6, 1.9))
    render_sample_metric_bars(ax, df, {**TYPO, "group_order": ["control", "treated"],
                                       "group_colors": {"control": "#9ca3af", "treated": "#2563eb"},
                                       "ref_lines": [{"y": 0.2, "label": "ENCODE minimum", "color": "#dc2626",
                                                      "style": "--", "width": 0.8}],
                                       "ylabel": "FRiP", "title": "Fraction of reads in peaks"})
    return fig


def ts_profile():
    """Per-gene z-score trajectories over samples, with the mean and group dividers."""
    from fig_atlas.renderers import render_ts_profile
    rng = _rng()
    samples = [f"{g}_{i}" for g in ("0h", "6h", "24h") for i in (1, 2)]
    base = np.array([0, 0, 1.2, 1.0, 0.4, 0.3])
    z = pd.DataFrame(base + rng.normal(0, 0.35, (12, 6)), index=[f"g{i}" for i in range(12)], columns=samples)
    z = (z.T - z.mean(axis=1)).T / z.std(axis=1).to_numpy()[:, None]
    fig, ax = plt.subplots(figsize=(2.8, 2.0))
    render_ts_profile(ax, z, {**TYPO, "sample_groups": {g: [s for s in samples if s.startswith(g + "_")]
                                                       for g in ("0h", "6h", "24h")},
                              "z_min": -2.5, "z_max": 2.5, "profile_labels_title": "Cluster 1 (12 genes)",
                              "profile_labels_ylabel": "z-score"})
    return fig


def chromosome_ideogram():
    """One chromosome from its cytobands, with a marked insertion site."""
    from fig_atlas_omics.renderers import render_chromosome_ideogram
    stains = ["gneg", "gpos50", "gneg", "gpos100", "acen", "acen", "gneg", "gpos75", "gneg", "gpos25"]
    bands = pd.DataFrame({"start": [i * 10_000_000 + 1 for i in range(10)], "end": [(i + 1) * 10_000_000 for i in range(10)],
                          "band": [f"{'p' if i < 5 else 'q'}{i % 5 + 1}" for i in range(10)], "gie_stain": stains})
    fig, ax = plt.subplots(figsize=(3.4, 1.0))
    render_chromosome_ideogram(ax, bands, {**TYPO, "labels_title": "Chromosome 2"},
                               markers=pd.DataFrame({"pos": [72_500_000], "label": ["Tg insertion"]}))
    return fig


def cis_linkage_panel():
    """RNA-ATAC correlation against distance to the TSS, and linked pairs per distance bin."""
    from fig_atlas_omics.renderers import render_cis_linkage_panel
    rng = _rng()
    n = 300
    dist = rng.uniform(0, 100_000, n)
    r = np.clip(rng.normal(0.15, 0.35, n) + 0.4 * np.exp(-dist / 15_000), -1, 1)
    bins = pd.cut(dist, [0, 2_000, 10_000, 50_000, 100_000], labels=["<2kb", "2-10kb", "10-50kb", "50-100kb"],
                  include_lowest=True).astype(str)
    df = pd.DataFrame({"distance_to_tss": dist, "pearson_r": r, "is_cis_linked": r > 0.5, "distance_bin": bins,
                       "human_symbol": [f"G{i}" for i in range(n)]})
    fig = plt.figure(figsize=(5.0, 2.2))
    render_cis_linkage_panel(fig, df, {**TYPO, "callouts": [], "legend_size": 6.0, "bar_label_size": 5.5,
                                       "badge_size": 6.0, "callout_size": 6.0, "wspace": 0.45})
    return fig


def count_summary():
    """UP above zero, DOWN below it, one bar per comparison."""
    from fig_atlas_omics.renderers import render_count_summary
    rng = _rng()
    rows = []
    for ds in ("Acute D1", "Acute D3", "Chronic 24h"):
        lfc = rng.normal(0, 1.4, 400)
        rows.append(pd.DataFrame({"dataset": ds, "log2fc": lfc,
                                  "adj_pvalue": np.where(np.abs(lfc) > 1.2, 0.001, 0.5)}))
    fig, ax = plt.subplots(figsize=(2.6, 2.0))
    render_count_summary(ax, pd.concat(rows), {**TYPO, "fdr_max": 0.05, "lfc_min": 1.0, "unit": "genes",
                                               "show_legend": False,
                                               "labels_title": "Differentially expressed genes"})
    return fig


def _go_table(n=8, clusters=False):
    rng = _rng()
    df = pd.DataFrame({"description": TERMS[:n], "fdr": 10 ** -rng.uniform(1.5, 8, n),
                       "gene_count": rng.integers(5, 60, n), "fold_enrichment": rng.uniform(1.5, 6, n)})
    df["gene_ratio"] = [f"{c}/400" for c in df["gene_count"]]
    if clusters:
        df["cluster_id"] = range(n)
        df["ontology"] = ["BP"] * n
    return df


def go_bar():
    from fig_atlas_omics.renderers import render_go_bar
    fig, ax = plt.subplots(figsize=(3.0, 2.2))
    render_go_bar(ax, _go_table(), {**TYPO, "top_n": 8, "x_axis": "-log10(FDR)", "bar_color": "#2563eb",
                                    "horizontal": True, "show_threshold_line": True, "labels_title": "GO BP"})
    return fig


def go_dot():
    from fig_atlas_omics.renderers import render_go_dot
    fig = plt.figure(figsize=(3.2, 2.4))
    render_go_dot(fig, _go_table(), {**TYPO, "top_n": 8, "x_axis": "Gene Ratio", "size_mode": "Gene Count",
                                     "labels_title": "GO BP"})
    return fig


def go_cluster_dot():
    from fig_atlas_omics.renderers import render_go_cluster_dot
    df = _go_table(clusters=True)
    df["_cluster_size"] = [3, 5, 2, 8, 1, 4, 6, 2]
    fig = plt.figure(figsize=(3.2, 2.4))
    render_go_cluster_dot(fig, df, {**TYPO, "x_axis": "-log10(FDR)", "color_by": "Fold Enrichment",
                                    "size_by": "Cluster size", "top_n": 8, "labels_title": "GO BP clusters"})
    return fig


def go_rrvgo_treemap():
    """Clusters of GO terms (rrvgo reduceSimMatrix shape), each split into its terms."""
    from fig_atlas_omics.renderers import render_go_rrvgo_treemap
    rng = _rng()
    parents = ["response to oxidative stress", "cell cycle", "synapse organization"]
    rows = []
    for k, p in enumerate(parents):
        for j in range(2 + k):
            rows.append({"go": f"GO:{k}{j:05d}", "cluster": k, "parent": f"GO:{k}00000", "parentTerm": p,
                         "score": 5.0 - k, "term": p if j == 0 else f"term {k}.{j}",
                         "size": int(rng.integers(20, 400)), "termDispensability": 0.0 if j == 0 else 0.4})
    fig, ax = plt.subplots(figsize=(3.8, 2.4))
    render_go_rrvgo_treemap(ax, pd.DataFrame(rows), {"hub_label_size": 6.5, "member_label_size": 5.5,
                                                     "title_size": 8.0, "labels_title": "Reduced GO BP"})
    return fig


def gene_model_track():
    from fig_atlas_omics.renderers import render_gene_model_track
    exons = pd.DataFrame({
        "gene_name": ["Abc1"] * 4 + ["Def2"] * 3 + ["Gm123"],
        "transcript_id": ["a1"] * 4 + ["d1"] * 3 + ["g1"],
        "strand": ["+"] * 4 + ["-"] * 3 + ["+"],
        "exon_start": [1000, 3000, 5200, 8000, 6500, 9000, 12000, 15000],
        "exon_end": [1600, 3400, 5600, 9500, 7000, 9400, 13000, 15400],
    })
    fig, ax = plt.subplots(figsize=(3.4, 1.2))
    render_gene_model_track(ax, exons, {**TYPO, "x_min": 0, "x_max": 17000})
    return fig


def interval_track():
    from fig_atlas_omics.renderers import render_interval_track
    iv = pd.DataFrame({"start": [1000, 2500, 6000, 9000, 9100], "end": [4000, 3200, 7500, 9000, 12000],
                       "kind": ["deletion", "SV call", "deletion", "junction", "SV call"],
                       "label": ["del 3 kb", "", "del 1.5 kb", "J1", ""]})
    fig, ax = plt.subplots(figsize=(3.4, 1.2))
    render_interval_track(ax, iv, {**TYPO, "x_min": 0, "x_max": 13000, "bracket_kinds": ["deletion"]})
    return fig


def segment_array():
    from fig_atlas_omics.renderers import render_segment_array
    df = pd.DataFrame({"kind": ["host", "tg", "copy_gap", "tg", "tg", "host"],
                       "label": [None, "Tg copy 1", None, "Tg copy 2", "Tg copy 3", None],
                       "coords": ["chr2:72.4 Mb", None, None, None, None, "chr2:72.5 Mb"],
                       "length_bp": [0, 9000, 300, 9000, 6000, 0], "strand": ["NA", "+", "NA", "+", "-", "NA"]})
    fig, ax = plt.subplots(figsize=(4.2, 1.1))
    render_segment_array(ax, df, {**TYPO, "flank_frac": 0.1, "sublabel_col": "coords"})
    return fig


def motif_architecture_table():
    from fig_atlas_omics.renderers import render_motif_architecture_table
    motifs = [{"rank": i + 1, "name": n, "family": f, "consensus": c, "pvalue": p, "pct_target": t, "pct_bg": b,
               "similar": s}
              for i, (n, f, c, p, t, b, s) in enumerate([
                  ("AP-1", "bZIP", "TGASTCA", "1e-42", "18.2%", "6.1%", "FOS, JUN"),
                  ("NRF2", "bZIP", "TGCTGASTCA", "1e-25", "9.4%", "2.8%", "NFE2L2, MAFK"),
                  ("KLF", "Zf", "GCCMCACCC", "1e-12", "21.0%", "13.5%", "KLF4, SP1")])]
    fig, ax = plt.subplots(figsize=(6.4, 1.6))
    render_motif_architecture_table(ax, motifs, {"title_size": 7.0, "header_size": 6.0, "text_size": 6.0,
                                                 "table_title": "De novo motifs"})
    return fig


def motif_dotplot():
    from fig_atlas_omics.renderers import render_motif_dotplot
    rng = _rng()
    rows = []
    for m in ("AP-1", "NRF2", "KLF", "CTCF", "TEAD"):
        for c in CONDS:
            sig = rng.random() < 0.6
            rows.append({"motif": m, "pattern_class": c, "log2fc": float(rng.normal(0, 1.2)) if sig else np.nan,
                         "neg_log10_p": float(rng.uniform(2, 20)) if sig else np.nan})
    fig, ax = plt.subplots(figsize=(3.0, 2.2))
    render_motif_dotplot(ax, pd.DataFrame(rows), {**TYPO, "class_order": CONDS, "fc_min": -2, "fc_max": 2,
                                                  "size_legend_loc": "upper left", "size_scale": 4.0,
                                                  "labels_title": "Motif enrichment"})
    return fig


def pathway_evidence_dotplot():
    from fig_atlas_omics.renderers import render_pathway_evidence_dotplot
    rng = _rng()
    terms = pd.DataFrame({"Description": [f"pathway {chr(65 + i)}" for i in range(6)],
                          "p.adjust": 10 ** -rng.uniform(1.4, 6, 6),
                          "evidence": ["ORA", "GSEA", "both", "ORA", "GSEA", "both"],
                          "Count": rng.integers(8, 80, 6)})
    fig, ax = plt.subplots(figsize=(3.2, 2.0))
    render_pathway_evidence_dotplot(ax, terms, {**TYPO, "evidence_colors": {"ORA": "#2563eb", "GSEA": "#d97706",
                                                                            "both": "#7c3aed"},
                                                "xlabel": "-log10 adjusted P", "labels_title": "KEGG"})
    return fig


def _feature_table():
    rng = _rng()
    rows = []
    for gs in ("total", "up", "down"):
        da = rng.dirichlet(np.ones(4)) * 100
        bg = rng.dirichlet(np.ones(4)) * 100
        for f, d, b in zip(("Promoter", "Intron", "Intergenic", "Exon"), da, bg):
            rows.append({"GeneSet": gs, "Feature": f, "DA_Pct": d, "Background_Pct": b,
                         "OddsRatio": float(d / b), "p_adjust": float(10 ** -rng.uniform(0, 5))})
    return pd.DataFrame(rows)


def peak_feature_enrichment():
    from fig_atlas_omics.renderers import render_peak_feature_enrichment
    fig = plt.figure(figsize=(3.6, 1.8))
    render_peak_feature_enrichment(fig, _feature_table(), {**TYPO, "labels_title": "DA peaks vs background"})
    return fig


def peak_feature_composition():
    from fig_atlas_omics.renderers import render_peak_feature_composition
    fig = plt.figure(figsize=(3.0, 2.2))
    render_peak_feature_composition(fig, _feature_table(), {**TYPO, "labels_title": "Peak locations"})
    return fig


def single_tf_expression_scatter_bar():
    from fig_atlas_omics.renderers import render_single_tf_expression_scatter_bar
    rng = _rng()
    conds = ["Control", "Acute 1D", "Acute 3D"]
    fig, ax = plt.subplots(figsize=(2.0, 2.0))
    render_single_tf_expression_scatter_bar(ax, "KLF10", conds, [list(rng.normal(m, 0.3, 3)) for m in (5.0, 6.4, 5.5)],
                                            params={**TYPO, "ylabel": "log2 normalized counts"})
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
    "paired_dumbbell_4x1": paired_dumbbell_4x1,
    "flow_diagram": flow_diagram,
    "dot_matrix": dot_matrix,
    "funnel": funnel,
    "jaccard_heatmap": jaccard_heatmap,
    "sample_metric_bars": sample_metric_bars,
    "ts_profile": ts_profile,
    "chromosome_ideogram": chromosome_ideogram,
    "cis_linkage_panel": cis_linkage_panel,
    "count_summary": count_summary,
    "go_bar": go_bar,
    "go_dot": go_dot,
    "go_cluster_dot": go_cluster_dot,
    "go_rrvgo_treemap": go_rrvgo_treemap,
    "gene_model_track": gene_model_track,
    "interval_track": interval_track,
    "segment_array": segment_array,
    "motif_architecture_table": motif_architecture_table,
    "motif_dotplot": motif_dotplot,
    "pathway_evidence_dotplot": pathway_evidence_dotplot,
    "peak_feature_enrichment": peak_feature_enrichment,
    "peak_feature_composition": peak_feature_composition,
    "single_tf_expression_scatter_bar": single_tf_expression_scatter_bar,
}

# Gallery families (fig_atlas.family) for pictures that are not a renderer
# themselves: every other case resolves through its renderer or plot type.
# A layout helper (panel tags) sits with the schematics.
EXTRA_FAMILIES = {
    "panel_tags": "schematic",
}
