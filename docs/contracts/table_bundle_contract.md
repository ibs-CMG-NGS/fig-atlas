# Contract: table bundles (generic shapes — line with error band, effect versus significance scatter)

The specification of tabular data bundles for any field. The core's generic renderers do not fix column names: which column is x and which is y is written in `plot_params` of `metadata.yaml` (as in `x_col: dose`). `fa bundle check` checks that the columns named exist, and `fa ingest bundle` copies those names into the config. The folder structure and common principles follow [`README.md`](README.md).

## Folder structure

```
<bundle_name>/
  inputs/data.csv          # one table (one row = one observation or one item)
  metadata/metadata.yaml   # plot_type + plot_params (including the column names)
```

## `plot_type: line_band` — line with error band

Draws repeated measurements over time, dose or position as one line per group with an error band (SEM, SD, 95% CI) (`render_line_band`).

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `x_col` | `x` | Yes | x values (numbers, or categories ordered by `x_order`) |
| `y_col` | `y` | Yes | Repeated measurements (or the centre value with `aggregate: none`) |
| `group_col` | — | No | The column that splits the lines. If given, the column must exist |
| `lower_col`, `upper_col` | — | No | The band's lower and upper bounds in an already summarised table (`aggregate: none`) |

```yaml
plot_type: line_band
plot_params:
  x_col: dose_uM
  y_col: viability
  group_col: compound
  x_log: true
  error: sem
```

## `plot_type: threshold_scatter` — effect versus significance

Draws a table with an effect size (whose sign is the direction) and a significance (smaller is stronger) per item as points, split by thresholds into up / down / ns (`render_threshold_scatter`). A volcano plot is one example of this shape.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `x_col` | — | Yes | The column drawn on x |
| `y_col` | — | Yes | The column drawn on y |
| `effect_col` | — | Yes | The signed effect column (decides up / down) |
| `sig_col` | — | Yes | The significance column (e.g. adjusted P) |

There are no default column names, so all four roles must be given in `plot_params`. Transforms are given with `x_transform` / `y_transform` (`none`, `log10`, `neg_log10`).

```yaml
plot_type: threshold_scatter
plot_params:
  x_col: effect
  y_col: p_adj
  effect_col: effect
  sig_col: p_adj
  y_transform: neg_log10
  effect_threshold: 0.5
  sig_threshold: 0.05
```

## `plot_type: paired_plot` — before and after

Draws each subject's values joined across conditions (before → after, or more time points), with an optional mean or median line and a significance bracket (`render_paired_plot`). With a group column the groups sit side by side, each with its own conditions.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `subject_col` | `subject` | Yes | The subject a value belongs to (one line per subject) |
| `condition_col` | `condition` | Yes | The condition, ordered by `condition_order` |
| `value_col` | `value` | Yes | The measured value |
| `group_col` | — | No | A second factor; its groups sit side by side. If given, the column must exist |
| `pvalue_col` | — | No | Each group's P value from a paired test run in the analysis script ([analysis recipes](../howto/analysis_recipes.md), section 2); draws the bracket. If given, the column must exist |

```yaml
plot_type: paired_plot
plot_params:
  subject_col: mouse
  condition_col: timepoint
  value_col: glucose
  condition_order: ["baseline", "week 4"]
  pvalue_col: p_value
  summary: mean
```

## `plot_type: grouped_bar` — grouped bars (two factors)

Draws a bar per group within each category: the mean (or median) with an SD, SEM or 95% CI error bar and the replicates on top (`render_grouped_bar`). `arrangement: interleaved` puts the groups side by side in each category; `separated` gives each group its own block. Brackets compare each group with `control_group` within a category.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `category_col` | `category` | Yes | The first factor (x categories) |
| `group_col` | `group` | Yes | The second factor (bar colour) |
| `value_col` | `value` | Yes | The replicate values |
| `pvalue_col` | — | No | On each (category, group) row, that group's P value against `control_group`, from a post-hoc test run in the analysis script ([analysis recipes](../howto/analysis_recipes.md), section 3). If given, the column must exist |

```yaml
plot_type: grouped_bar
plot_params:
  category_col: genotype
  group_col: treatment
  value_col: expression
  control_group: vehicle
  pvalue_col: p_vs_vehicle
  error: sem
```

## `plot_type: correlation_scatter` — correlation scatter (two variables)

Draws one point per item, a regression line with its band, and r and P per group (`render_correlation_scatter`). The line, the band and the numbers come from the analysis script ([analysis recipes](../howto/analysis_recipes.md), section 4): the line and band as coordinates on extra rows of the same table, r and P as columns.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `x_col` | `x` | Yes | The first variable |
| `y_col` | `y` | Yes | The second variable |
| `group_col` | — | No | Splits the points (and fit rows) into coloured groups |
| `fit_x_col`, `fit_y_col` | — | No | On fit rows: a grid of x values and the fitted y. A fit row with an empty group is a line over all points |
| `band_lower_col`, `band_upper_col` | — | No | On fit rows: the band's edges (a confidence or a prediction band; say which in the legend) |
| `r_col`, `p_col` | — | No | Each group's r and P, repeated on its rows. If given, the columns must exist |

```yaml
plot_type: correlation_scatter
plot_params:
  x_col: body_weight
  y_col: fat_mass
  group_col: diet
  fit_x_col: fit_x
  fit_y_col: fit_y
  band_lower_col: ci_low
  band_upper_col: ci_high
  r_col: r
  p_col: p_value
```

## Checks

`fa bundle check <bundle>` reports as errors:
- a required role whose column name is not in `plot_params` and has no default name
- a named (or default) column that is not in `data.csv`

The example bundles are in `examples/` ([first figure tutorial](../tutorials/first_figure.md)).
