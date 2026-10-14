# Data bundle contracts (for secondary analysis pipelines)

The documents in this folder are the exact folder, file and column specifications of data bundles that fig-atlas can **use as they are to draw figures**. If a secondary analysis pipeline (e.g. CMG-SeqViewer, or an automated export step after it) writes files to this specification under `raw_data/<study>/<project>/<bundle_name>/`, fig-atlas can render them straight away by writing only a config — **no searching, re-aggregating or reorganising folders**.

The top three rows of the table below are the column specifications of omics plot types, kept in the omics pack (`fig_atlas_omics/contracts/`). Below them are documents independent of any field: the image bundle contract, the table bundle contract, and the general procedure for submitting a bundle for a new plot type.

| Contract | Applies to | Example projects |
|---|---|---|
| [`de_go_bundle_contract.md`](../../fig_atlas_omics/contracts/de_go_bundle_contract.md) | A single dataset (one comparison): DE + GO/KEGG enrichment | `fig1-acute-1d-de`, `fig11-human-chronic-24h-de-go`, ... |
| [`integrated_bundle_contract.md`](../../fig_atlas_omics/contracts/integrated_bundle_contract.md) | Integration of several datasets (time-series clusters / co-expression modules) | `fig3-acute-1d-3d-integrated`, `fig7-acute-1d-chronic-24h-integrated`, `fig10-human-acute-1d-3d-integrated` |
| [`cross_condition_bundle_contract.md`](../../fig_atlas_omics/contracts/cross_condition_bundle_contract.md) | GO/KEGG enrichment compared across several comparisons | `fig14-mouse-go-cross-comparison`, `fig15-human-go-cross-comparison` |
| [`new_plot_type_contract.md`](new_plot_type_contract.md) | **A new plot type (anything the three above do not cover)** — the general bundle submission structure | `feature_enrichment_bundle`, `ma_plot_bundle`, ATAC-only bundles, ... |
| [`image_bundle_contract.md`](image_bundle_contract.md) | Microscope images, blots, gels (any field): original files per channel + `pixel_size` and `channels` metadata | `pilot-imaging` (public BBBC013; [tutorial](../tutorials/imaging_figure.md)) |
| [`table_bundle_contract.md`](table_bundle_contract.md) | Generic tables (any field): line with error band (`line_band`), effect versus significance scatter (`threshold_scatter`). Column names are given in `plot_params` | `examples/` ([first figure tutorial](../tutorials/first_figure.md)) |

> **Where they are, and automatic checks (2026-10-08, roadmap 6a.2)**: the three omics contracts (DE+GO, integrated, cross-condition) and the ATAC extension plan moved to the omics pack, `fig_atlas_omics/contracts/`. Only documents independent of any field stay in this folder.
> Each contract also has a machine-checkable form (`fig_atlas_omics/contracts/__init__.py`; core contracts in `fig_atlas/contracts.py`).
> - `fa bundle check <bundle folder>` (or `--all` for the whole of `raw_data/`): checks a bundle's structure, the contract for its `plot_type`, and the renderer that draws it. A column the renderer cannot do without is an **error**; any other column the contract requires is a **warning**.
> - `fa bundle contracts`: shows the registered contracts and the `plot_type` → renderer mapping.
> - A new contract is added as code and document together. `tests/test_plugins.py` fails if a contract points to a missing document or a `plot_type` has no renderer.

## Common principles (for every contract)

1. **Folder structure**: a project (one final figure) has several **bundle** subfolders under `raw_data/<study>/<project_name>/`. One panel = one bundle.
2. **What every bundle must have**: at least
   ```
   <bundle_name>/
     inputs/data.csv          # the table the figure reads directly (column specification: see each contract)
     metadata/metadata.yaml   # plot_type + plot_params (a snapshot of the renderer parameters: "drawn like this, roughly")
   ```
   `manifest.json`, `outputs/*.{png,svg,pdf}` and `scripts/figure.py` are welcome but not needed for rendering in fig-atlas (they are for reference and reproduction).
3. **Columns are matched by name**: pandas reads columns by name, so **their order does not matter, but their names must match exactly, case included** (as written in the contract).
4. **Original values are never processed, rounded or renamed**: shortening for display (`D1_vs_Control` → `D1` and the like) is the job of the `*_rename_map` in the fig-atlas config, so export the bundle's raw values exactly as the statistics produced them.
5. **"Absent" means no row at all**: if a term/condition combination is missing because it is not significant, do not make a placeholder row (filled with NaN or the like) — just leave the row out. The fig-atlas renderer treats it as "absent".
6. **`plot_params` in `metadata.yaml` is only a snapshot of starting values, not the final source of style**: in fig-atlas the project's `configs/config_<project>.yaml` is the final source, so the colours, font sizes, thresholds and so on written here only need to be right as a record of "how this data was drawn once". But **which fields exist (the schema) must match the contract exactly** for automatic integration to work.

## The work these contracts remove

Until now, the results of exploring the same parameters again and again in CMG-SeqViewer (or a similar secondary tool) had to be looked through by a person, given folder names, moved into place as `inputs/data.csv`, and checked for missing columns. When the export step follows these contracts automatically, all that is left on the fig-atlas side is **writing the config + (if needed) reusing an existing renderer** — a new renderer or contract is added only when a new layout is really needed.
