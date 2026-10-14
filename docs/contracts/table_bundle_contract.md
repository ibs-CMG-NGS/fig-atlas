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

## Checks

`fa bundle check <bundle>` reports as errors:
- a required role whose column name is not in `plot_params` and has no default name
- a named (or default) column that is not in `data.csv`

The example bundles are in `examples/` ([first figure tutorial](../tutorials/first_figure.md)).
