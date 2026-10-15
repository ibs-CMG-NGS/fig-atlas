"""Omics renderers (roadmap 6a.1b): plots whose data contract is NGS-specific --
GO terms, motifs, peaks, DE tables (log2FC / padj), cross-species orthologs,
TF regulons. Same conventions as the core renderers (``fig_atlas.renderers``):
every visual attribute comes from ``params`` and each module declares a SCHEMA.

The core finds this package through the ``fig_atlas.renderers`` entry point
(pyproject.toml), never by importing it.
"""

from .binary_motif_heatmap import render_binary_motif_heatmap
from .chromosome_ideogram import render_chromosome_ideogram
from .cis_linkage import render_cis_linkage_panel
from .clustered_go_heatmap import render_clustered_go_heatmap
from .count_summary import render_count_summary
from .cross_condition_dotplot import render_cross_condition_dotplot
from .cross_condition_heatmap import count_cluster_row_groups, render_cross_condition_heatmap
from .gene_model_track import render_gene_model_track
from .go_bar import render_go_bar
from .go_cluster_dot import render_go_cluster_dot
from .go_dot import render_go_dot
from .go_rrvgo_treemap import render_go_rrvgo_treemap
from .interval_track import render_interval_track
from .ma_plot import render_ma_plot
from .motif_dotplot import render_motif_dotplot
from .motif_table import render_motif_architecture_table
from .pathway_evidence_dotplot import render_pathway_evidence_dotplot
from .pathway_test_matrix import render_pathway_test_matrix
from .peak_feature_enrichment import render_peak_feature_composition, render_peak_feature_enrichment
from .segment_array import render_segment_array
from .species_response_scatter import render_species_response_scatter
from .tf_expression_bars import (
    describe_stars,
    render_single_tf_expression_scatter_bar,
    render_tf_expression_scatter_grid,
)
from .volcano import render_volcano

__all__ = [
    "count_cluster_row_groups",
    "describe_stars",
    "render_binary_motif_heatmap",
    "render_chromosome_ideogram",
    "render_cis_linkage_panel",
    "render_clustered_go_heatmap",
    "render_count_summary",
    "render_cross_condition_dotplot",
    "render_cross_condition_heatmap",
    "render_gene_model_track",
    "render_go_bar",
    "render_go_cluster_dot",
    "render_go_dot",
    "render_go_rrvgo_treemap",
    "render_interval_track",
    "render_ma_plot",
    "render_motif_architecture_table",
    "render_motif_dotplot",
    "render_pathway_evidence_dotplot",
    "render_pathway_test_matrix",
    "render_peak_feature_composition",
    "render_peak_feature_enrichment",
    "render_segment_array",
    "render_single_tf_expression_scatter_bar",
    "render_species_response_scatter",
    "render_tf_expression_scatter_grid",
    "render_volcano",
]
