---
title: 9. Honest numbers, statistics and images
audience: researchers (no programming experience needed)
reviewed: 2026-10-14
---

# 9. Honest numbers, statistics and images

> **Has this ever happened to you?**
> - After a reanalysis the figure showed the new data, but the legend's "n = 1,212" was still the old number.
> - A reviewer asked "Which test are the stars from, and did you correct for multiple testing?"
> - A journal asked how the brightness of microscope images had been adjusted.

**The key idea:** the **numbers, stars and image adjustments** in a figure all come from the data and the settings automatically, and are recorded. Nothing is typed by hand or adjusted separately. That is how figure and legend stay in agreement when the data change, and how you can show the basis for any answer.

## Live numbers

Result numbers in a figure's title or panel notes (counts, percentages, statistics) are **not typed by hand**.

| A hand-typed number | A live number |
|---|---|
| `"... 1,240 concordant genes ..."` | `"... {n_concordant:,} concordant genes ..."` |
| When the data change, it stays and becomes wrong. | The value the analysis computed is filled in at the build. When the data change, it changes too. |

- The analysis script records the value (`claims.record("n_concordant", n)`), and the legend writes its name in braces.
- If a legend names a value that was not recorded, verify fails (chapter 8).
- Thresholds (`P < 0.05`), other figure numbers and design values (times, doses) may be typed by hand: they are the design, not the results.
- If hand-typed result numbers increase, CI (the repository's automatic checks) stops it.

💬 **Ask an AI:** "Find hand-typed numbers in Figure 2's legend and have the analysis record them instead."

## The statistics table behind the stars

A figure that draws stars (`*`, `**`) or comparison brackets follows these steps.

1. **Write in the config** which test to use (e.g. Welch's t-test), whether to correct for multiple testing (e.g. Benjamini–Hochberg), and the star thresholds (e.g. `* P < 0.05`).
2. The build runs the tests as set and saves a **test table** (comparison, n, statistic, P, adjusted P, stars) next to the figure.
3. The legend's sentence on the star thresholds is filled in from the config too. Change the config and the stars, the table and the legend change together.
4. Without a test table, verify fails.

So to "which test did you use?", you show the `figure_NN_statistics/` folder of the results.

> Which test and correction are right is **for you to decide**. The tool computes and records what you set.

## Values shown (Source Data)

Some journals ask for the values actually plotted in each figure as tables (Source Data). If the analysis registers the values each panel draws, the build exports them per panel to `figure_NN_source_data/`. They are not the raw data but **exactly the values on the figure**.

## Microscope, blot and gel images

Images go in **as their original files, and adjustments are made in the settings when the figure is drawn**.

| Not this | But this |
|---|---|
| Putting in a copy with adjusted brightness and contrast | Writing, per channel, the display range in the config (which values show as black and as full brightness) |
| Putting in a cropped copy | Writing the region to crop (pixel coordinates) in the config |
| Drawing a scale bar by hand on the figure | Writing the pixel size (µm) in the note: an exact scale bar is drawn automatically |

The build records the original files' fingerprints, the cropped region, the display range and colour per channel in the "Images" part of the README (chapter 7). If an original file changes, verify fails.

A nonlinear brightness adjustment (gamma ≠ 1) makes verify warn. Gamma adjustment is allowed, but under journals' image integrity rules **the legend must say so**.

A worked example: [the microscopy tutorial](../tutorials/imaging_figure.md)

## Good to know

The rules of this chapter are not paperwork. They let you **answer from the record** to reviewers' questions, journals' requests for material and any suspicion of misconduct. You do not have to rely on remembering "how did I do that back then".

---
Previous: [8. Reading the check results](08-checks.md) · Next: [10. When the data change](10-freshness.md)
