---
title: 1. Why a tool like this
audience: researchers (no programming experience needed)
reviewed: 2026-10-13
---

# 1. Why a tool like this

> **Sound familiar?**
>
> - Resubmitting to another journal, you resized ten figures and their text, one by one.
> - After reanalysing the data, the text said "1,240" but a figure legend still said "1,212".
> - A reviewer asked "Which data and criteria is Figure 3c based on?", and six months later you could not remember.
> - A co-author asked for "bigger text, please"; once you changed it, that figure no longer matched the others.

**The key idea:** fig-atlas treats a figure **not as something you touch up by hand but as a result rebuilt from settings**. Each of the scenes above then ends with "build again".

## What the tool promises

| Promise | What changes |
|---|---|
| **Drawn from settings** | Colours, sizes, axis ranges and layout are all in a settings file (the config). To change a figure you do not open the figure or the program: you change one line of the config and build again. What you changed stays in writing, so it is easy to undo. |
| **Drawn at printed size** | A figure is not drawn large on screen and then shrunk; it is drawn 1:1 at its size on the page (the A4 text width). Write 7 pt in the config and it is 7 pt on paper. When the journal changes, you change one page setting. |
| **Checked automatically** | Every build looks for overlapping or clipped text, text that is too small, colours that colour-blind readers cannot tell apart, and font formats journals reject. |
| **Its sources are recorded** | Each figure records which data files (down to a value unique to each file, like a fingerprint), which settings and which software made it. When data change, you are told which figures are stale. |
| **Numbers come from the data** | Counts, percentages and statistics in a legend are not typed by hand; they are filled in from the analysis. When the data change, the legend changes with them. |
| **It follows the paper's course** | Exploratory figure → promoted to a paper Figure → figures no longer used are archived. Why the storyline changed, and the data behind each change, are recorded too. |

## What the tool does not do

- **It does not choose analysis methods or statistical criteria.** Which test to use and which threshold is right are yours to decide; you write them in the config.
- **It does not decide the paper's story.** Which figure becomes Figure 1 and what you claim are your judgement. The tool records those decisions and checks that the figures match them.
- **It does not change raw data.** Raw data are only read. Making them look better (shorter names, other units) is done in the config when the figure is drawn.

## So what does a researcher need to learn?

Not much. By the end of this guide you will be able to:

1. prepare data as a **bundle** and read its check results (chapter 3)
2. **make a figure** from a bundle, from code you wrote, or from a sketch of the figure you want (chapters 4 and 5)
3. **read and change the config** (chapter 6)
4. read the **check results** and decide what to fix
5. **promote** a figure to a paper Figure and keep a record

---
Previous: [0. How to read this guide](00-how-to-read.md) · Next: [2. Overview](02-overview.md)
