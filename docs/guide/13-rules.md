---
title: 13. The rules on one page
audience: researchers (no programming experience needed)
reviewed: 2026-10-14
---

# 13. The rules on one page

**The key idea:** there seem to be many rules, but they all serve one purpose: **"the figure and its record always agree, so you can show the basis for anything anyone asks"**. The full rules are in [`AGENTS.md`](../../AGENTS.md), and people and AI follow the same ones. The reasons behind the design are in the [design decisions](../decisions/README.md).

| # | Rule | Why | What keeps it |
|---|---|---|---|
| 1 | **Raw data are only read.** Shortening names and cutting ranges are done in the config. | To be able to show at any time which data a figure came from (chapter 3) | Fingerprints in the provenance record; a changed original marks the figure "stale" |
| 2 | **Every value of a figure is in the config, with an explaining comment.** No numbers typed into code. | To understand and change a figure from its config alone, without knowing the program (chapter 6) | The full set of values written when a bundle is attached; a check for numbers in code |
| 3 | **Files in the results folder are not edited by hand.** What to fix is fixed in the config or the figure spec. | They are lost at the next build, and figure and record would disagree (chapter 7) | Every build makes the results anew |
| 4 | **Figures are drawn at printed size, and a figure is done only when it has 0 preflight errors.** | Not to find problems only in the proofs (chapter 8) | Preflight; strict mode before submission |
| 5 | **Result numbers in legends are filled in from the data.** Stars are computed with the test set in the config, and the test table is kept. | So figure, legend and text never drift apart when data change (chapter 9) | A placeholder without a value → verify fails; more hand-typed numbers → CI stops; no test table → verify fails |
| 6 | **Images go in as their originals; adjustments are made in the config when the figure is drawn.** Nonlinear adjustments are stated in the legend. | To answer journals' image integrity rules from the record (chapter 9) | Adjustments recorded automatically; a changed original → verify fails |
| 7 | **Figure numbers and paper project names match one to one, and every storyline change leaves a revision record.** Figures are archived, not deleted. | To answer, three months later, "what changed then, and why" (chapter 11) | Storyline checks; a generated mapping table; a rebuild check after archiving |

## Names and places (for reference)

| What | Place and name |
|---|---|
| Config | `configs/<unit>/<stage>/config_<project>.yaml` |
| Analysis script | `analysis/<unit>/<stage>/<project>_analysis.py` |
| Figure spec | `figure_specs/<unit>/<stage>/figure_01_<project>.py` |
| Stage | `exploratory`, `paper`, `archive` |
| Paper project name | `<unit>-paper-main-fig<N>-<short-name>` (`supp` for supplementary figures) |
| Raw data | `raw_data/<study>/<project>/<bundle>/` |

The commands that create, promote and retire projects get the names and places right on their own. You do not need to remember them, but they help when you look for a file.

---
Previous: [12. Working with AI](12-ai.md) · Next: [Appendix A. Glossary](91-glossary.md)
