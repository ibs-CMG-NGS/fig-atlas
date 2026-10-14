# Contract 0: requesting a new plot type — the general bundle specification

**Purpose**: defines the **general structure and required parts** of the bundle an upstream pipeline submits when it first asks for a kind of visualisation that does not yet exist in fig-atlas.

Figures covered by the three existing contracts (`de_go`, `integrated`, `cross_condition`) follow those contracts. This document applies to **a new plot type covered by none of them**.

---

## Bundle folder structure (minimum)

```
raw_data/<study>/<project_name>/<bundle_name>/
  inputs/
    data.csv            # required — the table the renderer reads directly (rules below)
  metadata/
    metadata.yaml       # required — plot_type + a snapshot of plot_params
  example/
    plot.png            # strongly recommended — an output image for reference (else a description instead)
    script.R            # optional — the original script that first drew this data (helps synthesise the renderer)
```

One project (one final figure) = a set of bundles.
One panel = one bundle.

---

## 1. Rules for `inputs/data.csv`

| Rule | Description |
|---|---|
| **Column names match, case included** | pandas matches columns by name, so names are exactly as written in the contract or metadata.yaml |
| **Original values kept** | No log transforms, no rounding, no rounding for display — shortened names are handled in the fig-atlas config |
| **All rows included** | As a rule, include the full results with no statistical filter (padj < 0.05 or the like) — thresholds are the config's job |
| **Absent = no row** | If a combination is not significant or has no result, do not make a NaN row; just leave the row out |
| **Column order does not matter** | The order is free, but names must match exactly |
| **Encoding** | UTF-8; LF line endings recommended |

---

## 2. Rules for `metadata/metadata.yaml`

```yaml
figure_id: <bundle_name>                  # e.g. feature_enrichment_cluster1
plot_type: <renderer_slug>                # e.g. peak_feature_enrichment
                                          #   (if no renderer exists, propose a new name)
data_source: <upstream_tool_and_version>  # e.g. "cmg-seqviewer 3.2 / masigpro 1.4"

# A snapshot of the visualisation parameters used when this data was first drawn.
# On the fig-atlas side configs/config_<project>.yaml becomes the final source,
# so these values only need to be "values that came out well when drawn once".
# Describe exactly which fields exist (the schema) — the values are adjusted later.
plot_params:
  # e.g.:
  # fdr_max: 0.05
  # geneset_col: "cluster_id"
  # feature_col: "Feature"
  # odds_ratio_col: "OddsRatio"
  # sig_color: "#e57373"
  # list every parameter that means something for this plot_type

# The column/panel position this bundle belongs to (only if known)
panel_position:
  col: 2          # 0-indexed
  row: 3          # 0-indexed, row 0 = summary row
```

**When a new renderer is needed**: write a new name in `plot_type` and submit `example/plot.png` and `example/script.R` with it; fig-atlas then synthesises the renderer (the Case C procedure of `SKILL.md`). The existing renderers are listed in `docs/reference/renderer_inventory.md` (generic ones in `fig_atlas/renderers/`, omics ones in `fig_atlas_omics/renderers/`). A newly synthesised renderer comes with its parameter schema (`SCHEMA`, enforced by the tests), and from then on `fa param scaffold <renderer>` shows every adjustable parameter with its explanation.

---

## 3. `example/plot.png` — why it is recommended

When fig-atlas first takes in a bundle outside the three existing contracts, it runs a loop of **synthesising a renderer → rendering → visually comparing with the submitted figure**. With only a column specification and no example image, this loop cannot run, and checking the layout takes extra rounds. Please include one whenever possible.

---

## 4. Existing bundle types and new ones

| Types that already have a contract | Types that use this document |
|---|---|
| volcano, go_cluster_dot, go_bar, go_rrvgo_treemap | feature_enrichment, ma_plot |
| multi_group_heatmap, ts_profile, venn, count_summary | peak_feature_composition, coverage_track |
| cross_condition_heatmap, cross_condition_dotplot | ts_clusters (a new column combination), others |

Bundles of existing types and of new types may be mixed in one project. Bundles of existing types follow their contract; bundles of new types follow this document.

---

## 5. Submitting several bundles at once (a whole new project)

You may add an optional `project_manifest.yaml` at the project root:

```yaml
project_name: lab-atac-acute-ts-integrated   # the name in config_<project>.yaml
study: 2026-lab-atac
layout_family: atac_integrated                      # a hint at the layout family (optional)

# the bundles and the renderer each uses (inferred from metadata.yaml if absent)
bundles:
  - name: feature_enrichment_bundle
    plot_type: peak_feature_enrichment
    panel: [row1-6, col2]
  - name: ts_clusters_bundle
    plot_type: multi_group_heatmap
    panel: [row1-6, col0]
  # ...
```

With this file, the config fig-atlas generates automatically is more accurate.

---

## 6. Submission checklist

<!-- i18n: prose -->
```
[ ] inputs/data.csv — UTF-8, the full results, exact column names
[ ] metadata/metadata.yaml — with figure_id, plot_type, data_source, plot_params
[ ] example/plot.png — the result of drawing it once with the existing script or tool (recommended)
[ ] example/script.R or script.py — the original script (optional; improves the synthesised renderer)
[ ] If a new renderer is needed: a new name in plot_type, and example/ always included
[ ] If the data have direction (UP/DOWN): state whether it is one direction or mixed
```

---

*This contract does not itself specify a new bundle type. The concrete column specification of each bundle is documented in a separate contract (or a revision of an existing one) after fig-atlas first takes that bundle in.*
