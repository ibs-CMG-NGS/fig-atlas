# fig-atlas

A tool that **draws paper figures from a config, checks them before print, records where they came from, and manages them through a paper's life (exploration → paper figure → retirement)**. A field-neutral core is used together with domain packs (omics and others).

- **You adjust a figure in its config.** Colours, sizes, thresholds and layout are all in a commented YAML file, so you can change them without reading Python.
- **Figures are drawn at their printed size.** They are drawn 1:1 on the A4 text width, and `--preflight` checks for overlapping or clipped text, minimum sizes, colours that colour-blind readers cannot tell apart, and fonts.
- **Every figure keeps a record of its sources.** The hashes of its input data, code and parameters are recorded, and when data change you are told which figures are now stale.
- **Procedures are commands.** Creating a project, bringing in data, promoting and retiring figures are `fa` commands, and AI agents call the same commands as MCP tools.

## Where to start

| I want to | Read |
|---|---|
| understand what this tool is and how to use it (for researchers, no programming needed) | [Guide for researchers](guide/00-how-to-read.md) |
| try it for the first time | [Tutorial: first figure (15 min)](tutorials/first_figure.md) |
| make a figure from my data | [Data bundle contracts](contracts/README.md) → `fa ingest bundle` |
| make a figure of microscope or blot images | [Tutorial: a microscopy figure](tutorials/imaging_figure.md) |
| use it with an AI agent | [Connect AI agents](howto/ai_agents.md) |
| use it in another field | [Write a domain pack](howto/new_domain_pack.md) |
| assemble paper figures | [A figure's life](guide/11-lifecycle.md) |
| know why it is designed this way | [Design decisions (ADR)](decisions/README.md) |

`fa --help` lists every command. The repository's rules, for people and AI alike, are in [`AGENTS.md`](../AGENTS.md).
