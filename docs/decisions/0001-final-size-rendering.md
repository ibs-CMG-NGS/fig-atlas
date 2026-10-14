# 0001. Figures are drawn 1:1 at their final printed size (an A4 page preset)

- Status: accepted
- Date: 2026-09-30

## Context

The same config text size looked different from figure to figure, because each figure had a different canvas size (22–28 inch canvases drawn and then shrunk). In the print audit of 2026-09-30, the compendium figures printed at 26–38 % of their drawn size. The smallest text was 2–3 pt, and one figure was seven A4 pages tall. The target journal had not been chosen yet, and papers are often resubmitted to several journals.

## Decision

- Figures are drawn **1:1 at their final printed size**, without shrinking.
- The default page is A4 portrait with narrow margins (`styles/page_a4_portrait_narrow.yaml`, text area 184.6 × 271.6 mm). On top of it goes `styles/print.yaml` (body text 7 pt, ticks 6 pt, panel tags 10 pt; text at least 5 pt, lines at least 0.25 pt).
- Once a journal is chosen, its guidelines become a `styles/journal_<name>.yaml` preset, whose header gives the source URL and the date checked.
- Exploratory projects (about 44) are moved over only when needed.

## Consequences

- A pt value in the config is the printed size, so a researcher can predict the result from the number alone.
- All six compendium figures fit on one A4 page at scale 1.00. A figure that does not fit is split, reduced, or moved to a supplementary table.
- What keeps it: `fig_atlas/page.py` (`PageSpec`, `save_page_figure`), `fig_atlas/print_check.py`, `fa audit-print`, `fa build --preflight` (minimum text and line sizes, taller than one page). The skeleton `fa new project` writes also draws at page size.
