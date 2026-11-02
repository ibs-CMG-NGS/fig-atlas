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

## `plot_type: raincloud` — raincloud (half violin, box and points)

Draws per category a half violin (the cloud), a box with the quartiles and whiskers, and every value as a point (the rain) (`render_raincloud`). `orientation: horizontal` puts the categories on the y axis, first at the top; `vertical` puts them on the x axis. Brackets compare each category with `control_category`.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `category_col` | `group` | Yes | The category of each value |
| `value_col` | `value` | Yes | The values |
| `pvalue_col` | — | No | On each category's rows, its P value against `control_category`, from a test run in the analysis script ([analysis recipes](../howto/analysis_recipes.md), section 3). If given, the column must exist |

```yaml
plot_type: raincloud
plot_params:
  category_col: treatment
  value_col: latency
  control_category: vehicle
  pvalue_col: p_vs_vehicle
  orientation: horizontal
```

## `plot_type: column_scatter` — column scatter (points, mean or median, error)

Draws the values of each category as points with a mean or median line and error bars (`render_column_scatter`; Prism's scatter dot plot). `point_layout: swarm` spreads the points sideways without overlap at their true values, `jitter` scatters them at random, `aligned` puts them on one vertical line. Brackets compare each category with `control_category`.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `category_col` | `group` | Yes | The category of each value |
| `value_col` | `value` | Yes | The values |
| `pvalue_col` | — | No | On each category's rows, its P value against `control_category`, from a test run in the analysis script ([analysis recipes](../howto/analysis_recipes.md), section 3). If given, the column must exist |

```yaml
plot_type: column_scatter
plot_params:
  category_col: treatment
  value_col: il6
  control_category: vehicle
  pvalue_col: p_vs_vehicle
  summary: mean
  error: sd
```

## `plot_type: roc_curve` — ROC curve (AUC and its interval)

Draws one receiver operating characteristic curve per marker, the chance line, and each curve's AUC with its confidence interval in the legend (`render_roc_curve`). The curve and the numbers come from the analysis script ([analysis recipes](../howto/analysis_recipes.md), section 5).

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `fpr_col` | `fpr` | Yes | False positive rate (1 − specificity) of each curve point, from 0 to 1 |
| `tpr_col` | `tpr` | Yes | True positive rate (sensitivity) of each curve point |
| `group_col` | — | No | The marker (classifier) a curve point belongs to: one curve each |
| `auc_col`, `auc_low_col`, `auc_high_col` | — | No | Each curve's AUC and its confidence interval (bootstrap or DeLong), repeated on its rows |
| `operating_point_col` | — | No | True on the point to mark (a threshold the analysis picked, e.g. Youden's) |

If a column is named, it must exist.

```yaml
plot_type: roc_curve
plot_params:
  group_col: marker
  auc_col: auc
  auc_low_col: auc_ci_low
  auc_high_col: auc_ci_high
  operating_point_col: youden
```

## `plot_type: bland_altman` — Bland–Altman plot (agreement of two methods)

Draws each sample's difference between two methods against their mean, the line of no difference, the bias and the limits of agreement, with their values at the right edge (`render_bland_altman`). The point coordinates are worked out from the two measurements; the bias and the limits come from the analysis script as columns.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `a_col` | `method_a` | Yes | The first method's measurement of each sample |
| `b_col` | `method_b` | Yes | The second method's measurement |
| `group_col` | — | No | Colours the points by group |
| `bias_col` | — | No | The bias (mean difference), repeated on every row |
| `loa_low_col`, `loa_high_col` | — | No | The limits of agreement (e.g. bias ± 1.96 SD), repeated on every row |

`difference: percent` plots 100 × (a − b) / mean; compute the bias and limits the same way. If a column is named, it must exist.

```yaml
plot_type: bland_altman
plot_params:
  a_col: hba1c_lab
  b_col: hba1c_device
  bias_col: bias
  loa_low_col: loa_low
  loa_high_col: loa_high
```

## `plot_type: correlation_matrix` — correlation matrix (triangle, values, stars)

Draws the correlations among a set of variables as a lower, upper or full triangle of cells coloured by r -- squares, or circles whose area follows |r| -- with r and significance stars in the cells and a colourbar (`render_correlation_matrix`). The r and P of every pair come from the analysis script ([analysis recipes](../howto/analysis_recipes.md), section 4) as a long table: one row per pair.

| Role (plot_params key) | Default column name | Required | Content |
|---|---|---|---|
| `row_col` | `var1` | Yes | The first variable of the pair |
| `col_col` | `var2` | Yes | The second variable (a pair given once is drawn on both sides of the diagonal) |
| `r_col` | `r` | Yes | The pair's correlation |
| `p_col` | — | No | The pair's P value: stars in the cells, and blank cells with `hide_above_p`. If given, the column must exist |

```yaml
plot_type: correlation_matrix
plot_params:
  p_col: p_value
  triangle: lower
  mark: square        # or circle
```

## Checks

`fa bundle check <bundle>` reports as errors:
- a required role whose column name is not in `plot_params` and has no default name
- a named (or default) column that is not in `data.csv`

The example bundles are in `examples/` ([first figure tutorial](../tutorials/first_figure.md)).
