---
title: "3. Preparing data: bundles"
audience: researchers (no programming experience needed)
reviewed: 2026-10-14
---

# 3. Preparing data: bundles

> **Has this ever happened to you?** You copied an analysis table for a figure, renamed some columns and deleted a few rows, and later it no longer matched the original results and you could not find where it had changed.

**The key idea:** the data a figure uses arrive as a folder of a fixed shape, a **bundle**, and are **kept as received and only read**. What you want to change, you change in the settings when the figure is drawn.

## What a bundle looks like

A bundle is the data for one panel. One folder holds two files.

```
dose_response/                ← the bundle folder (any name)
  inputs/
    data.csv                  ← the table the figure reads
  metadata/
    metadata.yaml             ← a note saying "what figure this is"
```

**`data.csv`** is a table, the same as "Save as CSV" in Excel. The first rows of the example:

| compound | dose_uM | replicate | viability |
|---|---|---|---|
| compound A | 0.01 | 1 | 98.3 |
| compound A | 0.01 | 2 | 92.95 |
| … | … | … | … |

**`metadata.yaml`** says which kind of figure to draw (`plot_type`) and the settings to draw it with at first (`plot_params`).

```yaml
plot_type: line_band          # a line with an error band
plot_params:
  x_col: dose_uM              # the column on the x axis
  y_col: viability            # the column on the y axis
  group_col: compound         # the column that splits the lines
  x_log: true                 # a log scale on the x axis
  labels_title: "Viability after 48 h"
```

Which kinds of figure (`plot_type`) exist, and which columns each needs, are listed in the [data bundle contracts](../contracts/README.md). There are basic figures for any field (line with error band, effect versus significance scatter, Venn diagram, microscope image) and omics figures (volcano, GO and others).

## Where bundles go

| Data | Place |
|---|---|
| Real research data | `raw_data/<study>/<project>/<bundle>/` — only on the lab's computers, never uploaded to the repository (GitHub). |
| Example data | `examples/` — for practice and the documentation |

If an analysis pipeline (for example a secondary analysis tool for sequencing) exports bundles in this shape, the researcher only has to put the folder in place.

## Raw data are not changed

A bundle's table stays **exactly as the analysis produced it**. Most changes you want for a figure can be made in the settings instead.

| You want to | Instead of editing the raw data |
|---|---|
| shorten sample names (`Chronic_24H_vs_Control` → `24 h`) | the renaming tables in the settings (`…_rename_map`, `group_labels`) |
| cut an axis range | `x_min`, `x_max` and the like in the settings |
| draw only some items | order and selection values in the settings (`group_order`, top N, ...) |
| recalculate values (normalisation, another criterion) | export a **new bundle** from the analysis pipeline, and record what changed in a request document (chapter 11). |

The reason is that **you must always be able to show which data a figure came from**. A build records a fingerprint of each bundle file (a value that changes if even one byte of the content changes). If the raw data change, you are told that the figure is stale (chapter 10).

## Checking a bundle

Before drawing, check that the bundle matches its contract.

💬 **Ask an AI:** "Check the bundle `examples/dose_response`."

⌨ **Command:** `fa bundle check examples/dose_response`

The result is one of three.

| Result | Meaning | What to do |
|---|---|---|
| **ok** | The figure can be drawn. | Go to chapter 4 |
| **warning** (warn) | It can be drawn, but a column the contract recommends is missing. | Read it, and go ahead if that is fine |
| **error** (ERROR) | A column the figure needs is missing. | Do not change the raw data: check that the column names in the note (`metadata.yaml`) are right, or export the data again. |

For example, if the note says `group_col: drug` but the table has no `drug` column, you see:

```
ERROR missing column(s) named by plot_params: drug (group_col)
```

It means "the column `drug`, which the note names as `group_col`, is not in the table". The note must point to the table's real column name (`compound`).

- **A bundle from an analysis pipeline:** ask whoever made it to fix the note and export it again.
- **A bundle you made yourself:** fix the column name in the note (`metadata.yaml`).
- **In either case, do not edit the table (`data.csv`).**

Once the check passes, the note's values are copied into the config, and from then on you change them in the config (chapter 6).

---
Previous: [2. Overview](02-overview.md) · Next: [4. Making your first figure](04-first-figure.md)
