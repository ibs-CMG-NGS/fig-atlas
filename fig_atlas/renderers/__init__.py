"""Reusable, config-driven figure renderers.

Each ``render_*`` function reads all visual attributes from a ``params`` dict
via ``.get()`` so the same renderer works across projects with no code changes.
Analysis scripts import from here and only handle data loading and layout.

These are the domain-neutral renderers. Omics renderers (GO, motifs, peaks,
DE tables, ...) live in the omics pack, ``fig_atlas_omics.renderers``
(roadmap 6a.1b); tools find every installed renderer package through
``fig_atlas.renderer_registry``.
"""

import importlib
import importlib.abc
import importlib.util
import sys
import warnings

from .bar_scatter import render_bar_scatter
from .boxplot import render_boxplot
from .dumbbell import render_paired_dumbbell
from .effect_dots import render_effect_dots
from .funnel import render_funnel
from .group_scatter import render_group_scatter
from .grouped_hbar import render_grouped_hbar
from .heatmap import render_heatmap
from .image_panel import render_image_panel
from .jaccard_heatmap import render_jaccard_heatmap
from .line_band import render_line_band
from .multi_group_heatmap import render_multi_group_heatmap
from .panels import panel_label, place_panel_tags
from .pca import render_pca
from .sample_metric_bars import render_sample_metric_bars
from .signed_heatmap import render_signed_heatmap
from .stacked_share_hbar import render_stacked_share_hbar
from .threshold_scatter import render_threshold_scatter
from .tier_hbar import render_tier_hbar
from .treatment_schematic import render_treatment_schematic
from .ts_profile import render_ts_profile
from .two_set_euler import render_two_set_euler
from .venn import render_venn

__all__ = [
    "panel_label",
    "place_panel_tags",
    "render_bar_scatter",
    "render_boxplot",
    "render_effect_dots",
    "render_funnel",
    "render_group_scatter",
    "render_grouped_hbar",
    "render_heatmap",
    "render_image_panel",
    "render_jaccard_heatmap",
    "render_line_band",
    "render_multi_group_heatmap",
    "render_paired_dumbbell",
    "render_pca",
    "render_sample_metric_bars",
    "render_signed_heatmap",
    "render_stacked_share_hbar",
    "render_threshold_scatter",
    "render_tier_hbar",
    "render_treatment_schematic",
    "render_ts_profile",
    "render_two_set_euler",
    "render_venn",
]


# -------------------------------------------------- deprecation aliases --
# The omics renderers moved to fig_atlas_omics.renderers (roadmap 6a.1b). For
# one minor version the old names keep working, with a DeprecationWarning:
#   from fig_atlas.renderers import render_volcano       (__getattr__ below)
#   from fig_atlas.renderers.volcano import render_volcano  (_MovedFinder)
# Remove this block, and these names, when the aliases are retired.
_PACK = "fig_atlas_omics.renderers"
_MOVED_MODULES = {
    "binary_motif_heatmap", "cis_linkage", "clustered_go_heatmap", "count_summary",
    "cross_condition_dotplot", "cross_condition_heatmap", "go_bar", "go_cluster_dot", "go_dot",
    "go_rrvgo_treemap", "ma_plot", "motif_dotplot", "motif_table", "pathway_evidence_dotplot",
    "pathway_test_matrix", "peak_feature_enrichment", "species_response_scatter",
    "tf_expression_bars", "volcano",
}
_MOVED_NAMES = {
    "count_cluster_row_groups", "describe_stars", "render_binary_motif_heatmap",
    "render_cis_linkage_panel", "render_clustered_go_heatmap", "render_count_summary",
    "render_cross_condition_dotplot", "render_cross_condition_heatmap", "render_go_bar",
    "render_go_cluster_dot", "render_go_dot", "render_go_rrvgo_treemap", "render_ma_plot",
    "render_motif_architecture_table", "render_motif_dotplot", "render_pathway_evidence_dotplot",
    "render_pathway_test_matrix", "render_peak_feature_composition", "render_peak_feature_enrichment",
    "render_single_tf_expression_scatter_bar",
    "render_species_response_scatter", "render_tf_expression_scatter_grid", "render_volcano",
}


def _warn(old: str, new: str) -> None:
    warnings.warn(f"{old} moved to {new}; update the import (this alias will be removed)",
                  DeprecationWarning, stacklevel=3)


def __getattr__(name):
    if name in _MOVED_NAMES:
        _warn(f"fig_atlas.renderers.{name}", f"{_PACK}.{name}")
        return getattr(importlib.import_module(_PACK), name)
    if name in _MOVED_MODULES:
        _warn(f"fig_atlas.renderers.{name}", f"{_PACK}.{name}")
        return importlib.import_module(f"{_PACK}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class _MovedFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolves ``fig_atlas.renderers.<moved module>`` to the pack's module."""

    def find_spec(self, fullname, path=None, target=None):
        prefix, _, leaf = fullname.rpartition(".")
        if prefix == __name__ and leaf in _MOVED_MODULES:
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        leaf = spec.name.rpartition(".")[2]
        _warn(spec.name, f"{_PACK}.{leaf}")
        return importlib.import_module(f"{_PACK}.{leaf}")

    def exec_module(self, module):
        pass


if not any(isinstance(f, _MovedFinder) for f in sys.meta_path):
    sys.meta_path.append(_MovedFinder())
