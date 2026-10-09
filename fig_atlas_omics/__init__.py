"""Omics domain pack for fig-atlas (roadmap Phase 6a, step 6a.1).

NGS-specific helpers that used to live inside ``fig_atlas``: DA / DE ingest
adapters and GO-term clustering, plus the omics renderers, bundle contracts
and recipes. The core (``fig_atlas``)
never imports this package, so it stays usable for any kind of project; a
project that needs these helpers imports them from here::

    from fig_atlas_omics.da_ingest import prep_da_volcano_df
    from fig_atlas_omics import go_term_clustering

The old paths (``fig_atlas.da_ingest``, ``from fig_atlas import
prep_da_volcano_df``, ...) still work for one minor version and warn.
"""
from __future__ import annotations

from .da_ingest import prep_da_go_cluster_df, prep_da_kegg_df, prep_da_volcano_df

MODULES = ("da_ingest", "go_term_clustering")

__all__ = ["MODULES", "prep_da_go_cluster_df", "prep_da_kegg_df", "prep_da_volcano_df"]
