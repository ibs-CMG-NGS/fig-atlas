"""Omics bundle contracts and plot types (roadmap 6a.2).

The human documents sit next to this file (``*_bundle_contract.md``); the
objects below are their machine-checkable form, registered through the
``fig_atlas.contracts`` and ``fig_atlas.ingest`` entry points so that
``fa bundle check`` applies them. ``required`` lists the columns the renderer
needs; ``expected`` the further columns the document marks as required.
"""
from __future__ import annotations

from fig_atlas.contracts import Contract

_DOC = "fig_atlas_omics/contracts"

# GO / KEGG enrichment term tables (de_go_bundle_contract.md 2-3, integrated 4)
_TERMS = ("gene_set", "ontology", "term_id", "gene_ratio", "bg_ratio", "pvalue", "fdr", "qvalue",
          "gene_count", "gene_symbols", "fold_enrichment", "direction")

CONTRACTS = [
    Contract("de_go.volcano", ("volcano",),
             required=("log2FC", "padj"),
             expected=("gene_id", "symbol", "base_mean", "pvalue"),
             optional=("lfcse", "stat"), min_numeric=2,
             doc=f"{_DOC}/de_go_bundle_contract.md",
             title="One row per tested gene: log2FC, padj, ids, normalised counts per sample"),
    Contract("de_go.go_cluster_dot", ("go_cluster_dot",),
             required=("description",),
             expected=("cluster_id", *_TERMS, "_cluster_size", "_fe_median"),
             doc=f"{_DOC}/de_go_bundle_contract.md",
             title="One row per GO cluster representative, with cluster size and median fold enrichment"),
    Contract("de_go.go_bar", ("go_bar",),
             required=("description",),
             expected=_TERMS,
             doc=f"{_DOC}/de_go_bundle_contract.md",
             title="One row per enriched GO / KEGG term"),
    Contract("integrated.multi_group_heatmap", ("multi_group_heatmap",),
             required=("gene_label",), min_numeric=2,
             doc=f"{_DOC}/integrated_bundle_contract.md",
             title="One row per gene: label plus normalised expression for every sample of every condition"),
    Contract("integrated.count_summary", ("count_summary",),
             required=("dataset", "log2fc", "adj_pvalue"),
             doc=f"{_DOC}/integrated_bundle_contract.md",
             title="One row per (dataset, gene): log2FC and adjusted P"),
    Contract("cross_condition.enrichment", ("cross_condition_heatmap", "cross_condition_dotplot"),
             required=("GO Term", "Condition", "Signed -log10(FDR)"),
             expected=("GO ID", "Direction", "Gene Ratio", "Adjusted P-value"),
             optional=("Direction Flip",),
             doc=f"{_DOC}/cross_condition_bundle_contract.md",
             title="Long format: one row per significant (term, condition)"),
    Contract("de_go.ma_plot", ("ma_plot",),
             role_columns=(("x_col", "baseMean"), ("y_col", "log2FoldChange"), ("sig_col", "padj")),
             doc=f"{_DOC}/de_go_bundle_contract.md",
             title="One row per tested gene or peak: mean signal, log2FC and adjusted P"),
    Contract("atac_feature.motif_enrichment", ("motif_dotplot",),
             role_columns=(("term_col", "motif"), ("class_col", "pattern_class"), ("value_col", "log2fc"),
                           ("p_col", "neg_log10_p")),
             doc=f"{_DOC}/atac_feature_bundle_contract.md",
             title="Long format: one row per (motif, condition); empty value and P where not significant"),
    Contract("atac_feature.peak_features", ("peak_feature_enrichment",),
             role_columns=(("geneset_col", "GeneSet"), ("feature_col", "Feature"), ("odds_ratio_col", "OddsRatio"),
                           ("fdr_col", "p_adjust")),
             optional=("DA_Count", "DA_Pct", "Background_Count", "Background_Pct", "p_value"),
             doc=f"{_DOC}/atac_feature_bundle_contract.md",
             title="One row per (peak set, genomic feature): odds ratio against background and adjusted P"),
]

# plot_type -> renderer that draws it ("module:function").
INGEST = {
    "volcano": "fig_atlas_omics.renderers:render_volcano",
    "go_cluster_dot": "fig_atlas_omics.renderers:render_go_cluster_dot",
    "go_bar": "fig_atlas_omics.renderers:render_go_bar",
    "count_summary": "fig_atlas_omics.renderers:render_count_summary",
    "motif_dotplot": "fig_atlas_omics.renderers:render_motif_dotplot",
    "cross_condition_heatmap": "fig_atlas_omics.renderers:render_cross_condition_heatmap",
    "cross_condition_dotplot": "fig_atlas_omics.renderers:render_cross_condition_dotplot",
    "ma_plot": "fig_atlas_omics.renderers:render_ma_plot",
    "peak_feature_enrichment": "fig_atlas_omics.renderers:render_peak_feature_enrichment",
}
