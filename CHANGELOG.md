# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

Between releases the package reports `0.3.0.dev0` (`fa --version`), so a figure built from an
unreleased commit is not recorded as built with the last release.

### Added

- **`layouts.mm_axes(cell, left, top, width, height)`**: axes set out in millimetres from a cell's
  top-left corner. `layouts.finish` keeps a cell drawn this way at its drawn size and only moves it to
  the cell's corner, so a panel whose size comes from what it shows (an image at printed size, a
  table or a set of examples laid out in mm) states its sizes once, where it is drawn; `size_mm` on
  the same cell is an error.
- **Fixed-size panels in layouts** (`figures.cells.<letter>.size_mm: [width, height]`): `layouts.finish`
  places that panel at its cell's top-left corner and keeps its printed size instead of scaling it to
  the cell -- for a diagram drawn in millimetres, a matrix of square cells, or a panel shown at printed
  size. `fa layouts fixed_size` (and the `fa_layouts` MCP tool) describes it; example in
  `examples/layouts/fixed_size/`; `fit_in_cells` takes `(cell, axes, (w_mm, h_mm))` for it.
- **Tutorial: arrange the panels with a layout** (`docs/tutorials/layouts.md`, English and Korean;
  run by CI as written): a three-panel project moved from the even grid to `wide_bottom`, then to a
  `stack` whose second row is split by a `row`; the checks go from 1 error to none.
- **`fig_atlas.bundle_figure.draw_plot(cell, name, block, root, load=None)`**: draws one `plots:`
  block into one cell (of a layout); `draw_plots` now uses it, unchanged.
- **`layouts.panel_cells(lay)`**: every panel's cell by letter, the cells of split cells included,
  so a composed figure is drawn with one loop; `layouts.LAYOUTS` names the five layouts.

## [0.2.1] — 2026-11-03

### Fixed

- **`fa layouts`, `fa renderers` and `fa bundle contracts` run outside a project repository.**
  They only describe the installed package, so right after installing -- before `fa init` --
  they now show what fig-atlas can draw and arrange instead of asking for a repository.
  Every other command still needs one.

## [0.2.0] — 2026-11-02

The first release. Install it with
`pip install "git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.0"` (no PyPI package yet; see
[docs/howto/install.md](docs/howto/install.md)). It contains the first public tree (0.1.0.dev0, below),
the plot catalog's phase 2 (eight plot types), the layout catalog with composition, and:

- **Install guide** (`docs/howto/install.md`, English and Korean) and a rewritten README install
  section: install a tagged release with pip (with or without Git), pin it in a project
  repository, upgrade, or develop fig-atlas itself.
- **`fa --version`**: the installed version and where the package is imported from.

fig-atlas was developed in a private research repository from July 2026 and used for the figures
of one manuscript before being published as a package. This first public tree contains:

- **Projects and builds**: commented YAML configs as the single source of every visual value
  (parameter schemas for all renderers, `fa param scaffold / explain / sync`, `fa lint`),
  final-size rendering on page presets, figures sized by the journal columns they span
  (`figures.page_columns`, column widths named in the journal presets), `fa build` (analysis → publish → pre-print checks →
  verify), byte-identical rebuilds.
- **Pre-print checks** (`fa build --preflight`, `fa preflight`): 24 checks for overlaps, clipping,
  panel intrusion, print sizes, fonts, resolution, panel tags and colour (colour-vision deficiency,
  colormaps, contrast), with overlays and report / enforce modes.
- **Provenance**: automatic records of the files each figure read, its code, configuration and
  environment; `fa status`, `fa impact`, `fa lineage`, `fa diff-figure`; live numbers in legends
  (`fig_atlas.claims`), statistics tables (`fig_atlas.stats`), Source Data, image adjustment
  records, RO-Crate export (`fa export`).
- **Storyline ledger**: `storyline.yaml`, a generated figure–project registry, numbered revision
  records, compile-time snapshots, diffs and evidence tracing (`fa storyline ...`).
- **Commands for every procedure**: `fa init`, `fa new project | renderer`, `fa bundle check`,
  `fa ingest bundle` (Case B), `fa promote`, `fa retire`; dry-run diffs, JSON output, idempotent.
- **AI agents**: `fa mcp` serves the commands as MCP tools; checked with the CLI, opencode and
  Antigravity giving identical files.
- **Domain-neutral core and packs**: plug-in entry points for renderers, contracts, ingest maps,
  recipes and commands; an omics pack; an image panel; generic line-with-band and
  effect-vs-significance shapes.
- **Plot families**: every renderer declares the family its shape belongs to (`FAMILY` next to its
  `SCHEMA`; `fig_atlas/family.py` -- column, xy, grouped, survival, parts of a whole, multiple
  variables, diagnostic, image, schematic, field), a plot type inherits the family of the renderer
  that draws it, the gallery groups its examples and renderer pictures by family, and
  `fa renderers` / `fa new renderer --family` show and set it.
- **Results are data, not renderer code** (`docs/decisions/0007`): a renderer draws the numbers a
  figure prints and does not compute them. `group_scatter` prints its Pearson r and P from the
  `r_col` / `p_col` columns the analysis script writes (the gallery example carries them); the old
  in-renderer calculation runs with a deprecation warning until card E-04 removes it, and
  `tests/test_renderer_purity.py` fails when a renderer starts computing a printed result. The
  how-to page `docs/howto/analysis_recipes.md` gives the six recipes a catalog panel needs (paired
  test, post-hoc, correlation/regression, ROC/AUC, curve fit, contingency), and the project analysis
  template carries a commented case.

### Added — plot types (plans/PLAN_PLOT_CATALOG.md; 0.2.0.dev1)

- **PC-01 `paired_plot`** (column): before and after -- one line per subject across conditions,
  optional mean or median -- a line joining the conditions or a bar per condition behind the subjects,
  with SD, SEM or 95% CI error bars --, groups side by side, lines coloured by group or by direction, and a
  bracket per group from a P value column the analysis writes (`pvalue_col`).
- **PC-02 `grouped_bar`** (grouped): two factors -- a bar per group within each category (mean or
  median, SD, SEM or 95% CI error bar, replicates on top), interleaved or separated, and brackets
  against `control_group` from the P values a post-hoc test in the analysis writes (`pvalue_col`).
- **PC-03 `correlation_scatter`** (xy): two variables -- points by group, a regression line and its
  band from fit rows the analysis writes (`fit_x_col`, `fit_y_col`, `band_lower_col`,
  `band_upper_col`), and r and P per group from columns (`r_col`, `p_col`).
- **PC-04 `raincloud`** (column): per category a half violin, a box and every value as a point,
  horizontal or vertical, and brackets against `control_category` from a P value column (`pvalue_col`).
- **PC-05 `column_scatter`** (column): the values of each category as points -- swarm (no overlap),
  jitter or aligned -- with a mean or median line and SD, SEM, 95% CI or IQR error bars, and brackets
  against `control_category` from `pvalue_col`.
- **PC-06 `roc_curve`** (diagnostic): one ROC curve per marker from fpr/tpr columns, the chance line,
  each curve's AUC and its interval in the legend (`auc_col`, `auc_low_col`, `auc_high_col`) and an
  operating point the analysis picked (`operating_point_col`).
- **PC-07 `bland_altman`** (diagnostic): agreement of two methods -- each sample's difference (or
  percent difference) against its mean, the bias and the limits of agreement from columns the
  analysis writes (`bias_col`, `loa_low_col`, `loa_high_col`), labelled at the right edge.
- **PC-08 `correlation_matrix`** (multivariate): a lower, upper or full triangle of cells coloured by r
  -- squares, or circles with area following |r| -- from a long table of pairs the analysis writes,
  r and stars in the cells, blank cells above a P cut-off (`hide_above_p`), and a colourbar.

### Added — layouts (plans/PLAN_LAYOUT_CATALOG.md)

- **`fig_atlas.layouts`**: tested arrangements of panels for figures a layout script draws --
  `wide_bottom` (panels over one full-width panel), `stack`, `grid` (the cells `draw_plots` makes),
  `matrix` (a wall of small panels) and `row` -- each turning the `figures:` block into named cells,
  and `layouts.finish` to fit the panels into their cells and place the panel letters. Gaps
  (`wspace`, `hspace`) are real separators here; a SubFigure ignores them in a GridSpec.
- **Layout examples and catalog page**: `examples/layouts/<name>/` (commented `config.yaml` and a
  short `script.py`), pictures and `docs/reference/layouts.md` generated by `fa reference`.
- **Guide**: chapters 07-13 renumbered to 08-14 to make room for the layouts chapter.
- **Guide chapter 7, "Arranging panels: layouts"** (English and Korean), linked from chapters 6, 8 and 12.
- **`fa layouts [NAME]` and the `fa_layouts` MCP tool**: the layouts, one line each, or one in full (ASCII
  shape, call, usage, `figures:` keys); `fa layouts composition` for a layout inside a cell. Read from
  the layout docstrings (`fig_atlas.layouts._catalog`), which a test holds to the example configs.
- **`width_ratios` / `height_ratios` on `layouts.grid` and `layouts.matrix`**, as arguments or from
  `figures.grid` / `figures.matrix`; equal by default, so the cells `draw_plots` makes are unchanged.
- **Composition: a layout inside a cell of another.** Call a layout on a cell instead of the figure
  (`layouts.row(lay.cells["b"], fcfg, letters=("b", "c", "d"))`) to split that cell; `layouts.finish`,
  called once on the outer layout, fits the inner panels and lines their letters up with the rest.
  The inner layout's values sit under the cell's letter (`figures.cells.<letter>`); two levels at
  most. Example `examples/layouts/compose/` and a "Composition" section on the layout catalog page.
  Cells split alike in one column (or row) share their inner tag lines, so letters stay aligned
  when a panel cannot fill its cell (found redrawing a real figure with layouts).
- **`scripts/layout_coverage.py --repo <project repository>`**: reads the projects' analysis scripts
  without running them and names the layout that draws each one's arrangement, or why none does
  (manual placement, a grid laid over another, a shape computed at run time, ...), with the lines
  of layout code before and with the layout, and how many more a layout inside a cell of another
  (composition), `ratios` on `grid`/`matrix`, or an align/overlay helper would reach; `--csv` writes
  one row per script.
- **Documentation**: a guide for researchers, tutorials run as tests (Case A, B and C worked
  examples among them), how-to guides, generated reference pages and a renderer gallery, design
  decision records, a documentation site (MkDocs) in English with a Korean version of every page
  (`/ko/`; docs/decisions/0006, kept in step by tests/test_docs_i18n.py).
