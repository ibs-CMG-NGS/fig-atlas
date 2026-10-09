from .config import ProjectConfig, get_config, repo_root
from .page import PageSpec, save_page_figure
from .params import load_bundle_params, text_param
from .print_check import audit_figure
from .publish import publish
from .spec import FigureSpec
from .verify import verify_atlas, write_report

__all__ = [
    "FigureSpec",
    "PageSpec",
    "save_page_figure",
    "audit_figure",
    "ProjectConfig",
    "get_config",
    "load_bundle_params",
    "publish",
    "repo_root",
    "text_param",
    "verify_atlas",
    "write_report",
    "render",
]

# Note: figure renderers live in ``fig_atlas.renderers`` and are imported
# explicitly (e.g. ``from fig_atlas.renderers import render_volcano``) so that
# matplotlib/seaborn are only loaded by scripts that actually draw figures.

# The DA ingest helpers moved to the omics domain pack (roadmap 6a.1). These
# names still resolve for one minor version, with a DeprecationWarning; the
# core itself never imports fig_atlas_omics.
_MOVED = {"prep_da_go_cluster_df", "prep_da_kegg_df", "prep_da_volcano_df"}


def __getattr__(name):
    if name in _MOVED:
        import warnings
        warnings.warn(f"fig_atlas.{name} moved to fig_atlas_omics.da_ingest.{name}; update the import "
                      "(this alias will be removed)", DeprecationWarning, stacklevel=2)
        from importlib import import_module
        return getattr(import_module("fig_atlas_omics.da_ingest"), name)
    raise AttributeError(f"module 'fig_atlas' has no attribute {name!r}")


def render(name: str, *args, **kwargs):
    """Draw a plot by name -- ``fig_atlas.render("volcano", ax, df, params)`` --
    wherever its renderer lives: the core, an installed domain pack, or a
    recipe (fig_atlas.renderer_registry.find). Scripts need not know which;
    `fa renderers` lists the names."""
    from .renderer_registry import render as _render
    return _render(name, *args, **kwargs)
