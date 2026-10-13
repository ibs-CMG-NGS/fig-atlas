---
title: Appendix C. Commands on one page
audience: researchers who use a terminal
reviewed: 2026-10-14
---

# Appendix C. Commands on one page

Everything you can ask an AI to do can also be done with the commands below. Use them in a terminal (Command Prompt or PowerShell on Windows, Terminal on macOS and Linux, or the terminal inside an editor) while in the repository folder. First switch the environment on (`conda activate fig-atlas`, from any folder).

- Every command explains itself with `fa --help` and `fa <command> --help`.
- Add `--dry-run` to a command that changes files and it **only shows what would change, writing nothing.**
- Add `--json` and the result comes in a format for programs (the way an AI uses it).

## Projects and data

| You want to | Command | Chapter |
|---|---|---|
| Create a project | `fa new project name --domain lab --category exploratory` | 4 |
| Check a bundle | `fa bundle check bundle-folder` | 3 |
| See the kinds of figure and their contracts | `fa bundle contracts` | 3 |
| Attach a bundle as a panel (+ build) | `fa ingest bundle bundle-folder --project name` | 4 |
| List projects | `fa list` | — |
| See the names of figures that can be drawn | `fa renderers` | — |

## Building and checking

| You want to | Command | Chapter |
|---|---|---|
| Build | `fa build name` | 4 |
| Build + preflight | `fa build name --preflight` | 8 |
| Verify only | `fa verify name` | 8 |
| See where a config value comes from | `fa param explain name plots.panel.key` | 6 |
| Write into the config the keys a build took from defaults | `fa param sync name` (preview) → `--apply` | 6 |
| Find unused config keys and typos | `fa lint name` | 6 |
| Find hand-typed numbers | `fa claims name --list` | 9 |
| Audit printed sizes | `fa audit-print` | 7 |

## Provenance and freshness

| You want to | Command | Chapter |
|---|---|---|
| Find stale figures | `fa status` | 10 |
| Figures that use this file | `fa impact file-path` | 10 |
| A figure's sources | `fa lineage name` | 10 |
| What changed since a snapshot | `fa diff-figure name` | 10 |
| A package for submission (RO-Crate zip) | `fa export name --zip` | 7 |

## A paper's life and the storyline

| You want to | Command | Chapter |
|---|---|---|
| Promote | `fa promote name --figure 2 --slug short-name` | 11 |
| Retire | `fa retire name` | 11 |
| Rewrite the mapping table | `fa storyline registry` | 11 |
| Check the storyline's consistency | `fa storyline check` | 11 |
| Draft what changed | `fa storyline diff --draft` | 11 |
| Sync the revision records | `fa storyline revisions --sync` | 11 |
| Compendium PDF (strict; also saves this point's snapshot) | `fa storyline compile --strict` | 11 |
| Save the record of what changed | `fa storyline diff --write` | 11 |
| List the saved snapshots | `fa storyline snapshots` | 11 |
| Trace a figure's evidence | `fa storyline evidence "Main Figure 3"` | 11 |

## For people who build things

| You want to | Command |
|---|---|
| Start a new kind of figure (a renderer) | `fa new renderer name --plot-type kind` |
| Check for numbers typed into code | `fa lint --hardcoded` |
| Offer the tools to an AI assistant | `fa mcp` ([how to connect](../howto/ai_agents.md)) |

Run `fa new renderer` in a research repository and the renderer is made in that repository's `renderers/` folder. Without installing or changing the package, `fa renderers`, `fa ingest bundle` and `fa build` find that renderer, and the provenance record keeps its file too. If the shape would serve other research as well (bars, lines, scatter, heatmaps), consider moving it into the fig-atlas core later.

---
Previous: [Appendix B. Questions and troubleshooting](92-faq.md) · Next: [Appendix D. Further reading](94-reading.md)
