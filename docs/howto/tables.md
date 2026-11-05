# How-to: draw a summary table

A figure is not the only thing a paper shows. A table of group means, a table of constructs, a table of sequencing runs -- these belong on a page beside the figures, and until now they were the one thing fig-atlas could not draw: they were pasted in as a screenshot from a spreadsheet, at whatever font the spreadsheet happened to use.

The `table` renderer draws them at print size, in the publication convention, from the same bundles and the same config as a figure.

## Before anything else: this is not how you submit a table

**Journals take tables as editable text** -- Word, Excel, or the publisher's own form. A rendered table is a picture: it cannot be copyedited, it cannot be re-typeset into the journal's own style, and a screen reader cannot read it aloud. Submitting one as a figure usually means it comes back.

So use this renderer for

- a compendium page, where the table sits beside the figures it goes with,
- a talk or a poster, where the table has to match the figures' font and sizes,
- a check: the table drawn at print size shows immediately whether it fits a page at all,

and submit the CSV itself -- `inputs/data.csv`, or the `outputs/supplementary/*.csv` the generator writes. The drawn table and the submitted table then come from one file, so they cannot disagree.

## 1. From a table you already have, without writing code

Any CSV is a table bundle: there are no required columns, because any table can be printed.

```bash
cp -r <fig-atlas>/examples/gallery/table raw_data/<project>/group_summary
# replace raw_data/<project>/group_summary/inputs/data.csv with your table
fa bundle check raw_data/<project>/group_summary
fa ingest bundle raw_data/<project>/group_summary --project <project>
fa build <project> --preflight
```

`fa ingest bundle` writes the whole `plots.<name>` block into the project config -- every parameter with its unit and what it changes -- and from then on the table is tuned from the config like any panel. `fa bundle check` reports a column named in `columns` that the data does not have, and warns about a per-column key that names no column (a typo in `column_format` is otherwise invisible: the number simply prints unformatted).

## 2. The per-column treatment is what makes it look like a table

Layout is not what separates a professional table from a pasted one. **Alignment and number format are.** Without them one table prints `0.4871234` beside `41`, and a reader cannot compare two rows at a glance.

```yaml
plots:
  group_summary:
    renderer: "table"
    bundle: "raw_data/<project>/group_summary"
    columns: ["group", "n", "mean_latency_s", "sd_latency_s", "p_vs_vehicle"]
    column_labels:
      mean_latency_s: "Latency (s), mean"
      p_vs_vehicle: "P vs vehicle"
    column_format:               # a format per numeric column
      mean_latency_s: ".1f"
      sd_latency_s: ".1f"
      p_vs_vehicle: ".3g"        # .3f would print 1e-07 as 0.000
    column_align:                # default: numbers right, text left
      group: left
    column_width:                # [0-1] of the table width; the rest are measured
      group: 0.34
    na_text: "--"                # what an empty cell prints as
    title: "Latency to fall, by treatment group"
    footnotes:
      - "Welch's t test against vehicle, each dose separately."
```

| Set it when | Key |
|---|---|
| a float column prints its full repr | `column_format` |
| a heading is the raw column name (`mean_latency_s`) | `column_labels` |
| a text column squeezes the numeric ones | `column_width` |
| an empty cell reads as a value | `na_text` |
| the columns read as one block | `col_gap` (raise it) |
| a heading wraps to three lines | `header_size` (lower it) |

Everything else -- the rules, the fonts, the spacing -- comes from the style preset, so you do not set it per table.

## 3. The look comes from a style preset

`table_classic` is the publication convention: three horizontal rules (above the headings, under them, under the last row), no vertical rules, no fills. It ships with fig-atlas and is the renderer's default, so a project that sets nothing already draws it that way.

For a table meant to be read on a screen rather than printed, `row_stripe: true` shades every other row. Do not put it in a paper.

```yaml
project:
  style: ["default", "print", "table_classic"]
```

## 4. A table page in the compendium

A storyline's `tables:` entries become pages after the figure pages, one page per table, drawn by this renderer (`fa storyline compile`). Each entry names the CSV and may carry a `render:` block -- the renderer's parameters, plus a few keys that belong to the page rather than the table.

```yaml
tables:
  - slot: "Main Table 1"
    file: "outputs/supplementary/main_table_1.csv"
    generator: "scripts/make_main_table_1.py"
    description: "The constructs, their coordinates and what each one measures"
    render:
      columns: ["line", "chromosome", "position", "copies", "note"]
      column_labels: {copies: "Copies"}
      sort_by: "position"        # which rows a long table shows first
      sort_ascending: true
      orientation: auto          # auto | portrait | landscape
      transpose: false           # first column becomes the headings (a short, wide table)
```

Two things the compendium does on its own, and both are worth knowing:

- **A table longer than a page shows the rows that fit** -- measured by drawing, not guessed -- and says under it how many of how many, in what order, and that the rest are in the CSV.
- **A table wider than a page is the same problem sideways.** Below about nine columns it stays upright; beyond that it is drawn rotated, and past a certain width no font size helps -- every column is narrower than its longest word. The answer is to choose: name in `render.columns` the columns a reader reads off paper and leave the machine-readable rest in the CSV. The page then notes how many columns of how many it shows.

A column format nobody sets is chosen from the data: a whole-number float loses its decimals, a column reaching into the thousands gets digit grouping, a small P value stays in exponent form, and an integer of five figures or more is grouped (`7,301,884`, not `7301884`, beside the same table's `chr1:24,905,310`).

## 5. Inside an analysis script

A script draws a table like any other shape, by name, and registers what it printed as that panel's source data:

```python
import fig_atlas
from fig_atlas import source_data

printed = fig_atlas.render("table", ax, summary, cfg.get("plots", {}).get("group_summary", {}))
source_data.add(printed, panel="b", title="Latency by treatment group")
```

`render_table` returns the rows **as they were printed**, formatted and in order, so the source data and the page carry the same text. Its `attrs["height_pt"]` is the height the table drew to, which is how the compendium sizes a page's box to its content.

## 6. The numbers in a table are computed, not typed

The same rule as a figure legend. A count, a coordinate, a distance, a rate goes into the table by being read from the delivered data, in the generator or the analysis script ([analysis recipes](analysis_recipes.md)). Only a judgement -- a construct's name, a sentence of interpretation -- is written out, and a number inside such a sentence takes the computed value through a format field.

A typed table drifts silently, and the drift is invisible: the figures get corrected, the table does not, and nothing in the build compares them. A generator that reads the data can also be tested -- change a value in a copy of the input and check the cell moves.

## 7. Limits

| | |
|---|---|
| Long tables | `max_rows` (default 40) drops the rest and counts them in `truncation_note`. A table of thousands of rows is not this shape; keep it as CSV |
| Cell text | wraps to `max_lines` (default 3); a cell cut there ends in `truncation_mark`, so a cut never passes as the whole text |
| Smallest text | the print floor is 5.0 pt (`cell_size`); preflight reports anything under it as an error |
| Spanning headings | `column_groups` puts a label over a run of columns, with its own rule under it |
| Merged cells, nested headers, in-cell colour scales | not drawn. A table that needs them is a heatmap |

## Where to look next

- [Table bundle contract](../contracts/table_bundle_contract.md) -- `plot_type: table` and what `fa bundle check` checks
- [Renderer gallery](../reference/gallery.md#table) -- the example bundle, with its data and the commands to copy it
- [Config keys](../reference/config.md) -- every parameter of the renderer, generated from its schema
- [Compute the numbers a figure prints](analysis_recipes.md) -- where a table's numbers come from
