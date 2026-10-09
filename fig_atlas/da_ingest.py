"""Moved to ``fig_atlas_omics.da_ingest`` (roadmap 6a.1, omics domain pack).

This alias keeps ``fig_atlas.da_ingest`` imports working for one minor version;
import from ``fig_atlas_omics.da_ingest`` instead.
"""
import sys
import warnings

from fig_atlas_omics import da_ingest as _moved

warnings.warn("fig_atlas.da_ingest moved to fig_atlas_omics.da_ingest; update the import "
              "(this alias will be removed)", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _moved
