---
title: Appendix A. Glossary
audience: researchers (no programming experience needed)
reviewed: 2026-10-14
---

# Appendix A. Glossary

In alphabetical order. In brackets: other names, or the names used in files and commands.

| Term | Meaning | More |
|---|---|---|
| **AI assistant / agent** | An AI such as Claude Code or Gemini CLI that runs tools for you when you ask in words | chapter 13 |
| **archive / retire** | Moving a project no longer used to `archive/` instead of deleting it | chapter 12 |
| **build** | One run that redraws the figure from its config, arranges, checks and records it | chapter 4 |
| **bundle** | The data folder for one panel: a table (`data.csv`) + a note (`metadata.yaml`) | chapter 3 |
| **Case A, B, C** | The three entry points for a new figure. A = plotting code you wrote + data, B = a standard bundle, C = data + a capture, sketch or description of the figure you want | chapter 5 |
| **CI** | Checks that run automatically each time a change reaches the repository. They stop rule violations. | — |
| **compendium** | A PDF with all the storyline's Figures in order | chapter 12 |
| **config** | The file with every value of a figure, each with an explaining comment. Where the researcher changes a figure | chapter 6 |
| **contract** | The rule saying which columns a bundle needs for each kind of figure. The bundle check uses it. | chapter 3, [the contracts](../contracts/README.md) |
| **exploratory / paper / archive** | The three stages of a project. Also the names of their folders. | chapters 2, 12 |
| **figure spec** | The file with a figure's title, a note per panel and the limits of what it claims. Under `figure_specs/` | chapters 2, 8 |
| **fingerprint** (hash, sha256) | A string computed from a file's content, unique to it. It changes if even one byte changes. | chapter 11 |
| **live number** (claim) | A result number in a legend that is not typed by hand but filled in from the analysis. Written `{name}` in the legend. | chapter 10 |
| **MCP** | The common way for AI assistants to call outside tools. fig-atlas offers its tools this way. | [Connect AI agents](../howto/ai_agents.md) |
| **note** (`metadata.yaml`) | The file in a bundle that says "what figure this is" (`plot_type`) and its first settings (`plot_params`) | chapter 3 |
| **panel** | One part of a figure (a, b, c, ...) | chapter 4 |
| **panel tag** | The letter a, b, c at a panel's upper left. Placed automatically on the panel's outer edge. | chapter 4 |
| **preflight** | The check for overlapping or clipped text, text size, colour and font problems in a figure. error / warn / info | chapter 9 |
| **project** | The unit that makes one figure: three files, the config, the analysis script and the figure spec | chapter 2 |
| **promote** | Moving an exploratory project to a paper Figure project and renaming it | chapter 12 |
| **provenance record** | The record, kept automatically, of which data, settings and software made a figure, and when | chapter 11 |
| **pt** (point) | The unit of text size and line width. 1 pt ≈ 0.35 mm | chapter 6 |
| **renderer** | The software component that draws one kind of figure (line with error band, scatter, heatmap, ...). Researchers rarely deal with it directly. | — |
| **research unit** (domain) | The unit that groups projects (a researcher or a study). E.g. `lab`, `kim`, `screening` | chapter 2 |
| **revision record** | The numbered record written each time the storyline changes: what changed, why, and on which data | chapter 12 |
| **snapshot** | A saved state of the storyline at one point (assignment, figure provenance, numbers), used for later comparison | chapter 12 |
| **Source Data** | A table of the values actually plotted in a figure. Some journals ask for it. | chapter 10 |
| **stale / fresh** | Stale if the data, settings or software changed after the figure was made; fresh if not | chapter 11 |
| **storyline** | The document with the paper's figure assignment (which project is Figure what) and its story | chapter 12 |
| **verify** | The check that the results (figure files, README, statistics tables, ...) are complete and agree. PASS / WARN / FAIL | chapter 9 |
| **YAML** | The format of the config. `name: value` lines grouped by indentation. | chapter 6 |

---
Previous: [14. The rules on one page](14-rules.md) · Next: [Appendix B. Questions and troubleshooting](92-faq.md)
