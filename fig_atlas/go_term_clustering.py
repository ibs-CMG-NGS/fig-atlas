"""Moved to ``fig_atlas_omics.go_term_clustering`` (roadmap 6a.1, omics domain pack).

This alias keeps ``fig_atlas.go_term_clustering`` imports working for one minor version;
import from ``fig_atlas_omics.go_term_clustering`` instead.
"""
import sys
import warnings

from fig_atlas_omics import go_term_clustering as _moved

warnings.warn("fig_atlas.go_term_clustering moved to fig_atlas_omics.go_term_clustering; update the import "
              "(this alias will be removed)", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _moved
