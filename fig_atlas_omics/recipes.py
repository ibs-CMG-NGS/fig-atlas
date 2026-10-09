"""The omics pack's recipes (fig_atlas.recipes entry point, roadmap 6a.3): domain
plots drawn by a generic core renderer. Each recipe lives next to the domain
renderer function that keeps its name and config keys."""
from __future__ import annotations

from .renderers import ma_plot, volcano

RECIPES = [volcano.RECIPE, ma_plot.RECIPE]
