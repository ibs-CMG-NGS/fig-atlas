# 0003. Renderers are shapes, in the core; a field's knowledge goes into packs

- Status: accepted
- Date: 2026-10-07

## Context

fig-atlas started with an NGS paper, but it must also manage figures in other fields (imaging, electrophysiology, clinical). The first idea was to split renderers into "generic / NGS". But bars, lines, scatter plots and heatmaps are the same shape in every field; what changes from field to field are column names, vocabulary, defaults and how data are read. Leaving this split to users would duplicate the same shape in every field.

## Decision

- **A renderer is a shape.** Bars, lines, scatter plots, heatmaps and dot matrices go in the core (`fig_atlas/renderers/`) even if the first data they drew were omics.
- **A domain pack** (e.g. `fig_atlas_omics`) holds only what is specific to its field:
  - data readers and ingest adapters
  - bundle contracts
  - recipes: a core shape + the field's column roles, vocabulary and defaults
  - analysis helpers
- Only shapes that mean nothing outside their field (a sequence logo, genome tracks) are pack renderers.
- The core never imports a pack. A pack registers its renderers, recipes, contracts, ingest mappings and CLI commands through entry points.
- Scripts draw with `fig_atlas.render("<name>", ...)`. They need not know which package a renderer is in, so moving a renderer does not break them.

## Consequences

- A new field starts by adding a pack, without changing the core (`docs/howto/new_domain_pack.md`; the tests actually build the example pack).
- The existing omics renderers move, one at a time, to core shapes + recipes (roadmap 6a.3). volcano and ma_plot are the first.
- What keeps it:
  - `tests/test_core_boundary.py`: the core does not import a pack
  - `fa renderers`: lists what is where
  - `fa new renderer`: the core is the default place, and choosing a pack explains this principle
