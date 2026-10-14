# 0002. The project config is the source of truth: it holds every parameter a renderer reads, with comments

- Status: accepted (to be reviewed: roadmap gate G0)
- Date: 2026-08-13 (tidied 2026-10-08)

## Context

A bundle's `metadata/metadata.yaml` often already has `plot_params`. So it is tempting to write in the config only the keys you want to change (e.g. the title) and leave the rest to the bundle's values. But then adjusting a figure means looking at an easily forgotten file under `raw_data/`, and reading the config alone does not tell you which values the figure is drawn with. The user corrected this in a Case B ingest (a DE + GO bundle project): a researcher must understand and adjust a figure from its config alone, without reading Python (the config is the researcher's interface).

## Decision

- Every ingested figure's `plots.<name>` block holds **every key the renderer reads** (colours, thresholds, axis ranges, colormaps, sizes, top_n, sorting and annotation modes, ...), even when equal to the bundle's value.
- Each key has a comment with its role, unit and which way to adjust it (AGENTS.md §1.6).
- The merge order `bundle < style preset < config` stays, but no value a user might want to adjust is left to the bundle.

## Consequences

- One config shows and changes every value of a figure. The price is longer configs (paper configs of 158–737 lines).
- Tools do the copying instead of people:
  - `fa ingest bundle`: writes the whole block, with comments, from the bundle's values and the schema defaults.
  - `fa param scaffold`: prints a renderer's whole block.
  - `fa param sync --apply`: fills in keys the build took from defaults.
  - `fa lint`: finds missing keys, keys never read and typos.
- A renderer's `SCHEMA` keeps its keys' defaults and descriptions in one place. `tests/test_renderer_schemas.py` checks that schema and code agree.
- Gate G0: once the tools are stable, decide again whether to switch to "only keys that differ from the defaults in the config" (policy A). If so, a new record replaces this one.
