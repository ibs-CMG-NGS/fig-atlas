# fig-atlas

**Config-driven, verifiable and provenance-tracked publication figures — across a paper's lifecycle.**

fig-atlas is a layer above matplotlib for the figures of a scientific paper. Each figure is a
reproducible build product of a *data bundle*, a *commented configuration* and a *renderer*:

- **Every visual value lives in the config** — colours, sizes, thresholds, layout — each with a
  comment giving its role, unit and how to tune it. Researchers change figures without reading code.
- **Figures are drawn at final print size** (1:1 on page presets) and **checked before print**:
  24 pre-print checks find text overlaps, clipping, too-small text, colours that colour-blind
  readers cannot tell apart, Type 3 fonts and low resolution, with an overlay showing where.
- **Every figure records its provenance** — the data files it actually read (with hashes), the
  code and configuration — so `fa status` tells which figures a data change made stale, and the
  same inputs rebuild to byte-identical files.
- **Numbers, statistics and images stay honest**: legend numbers are filled from the analysis,
  significance marks come with a published test table, and microscope images are adjusted in the
  panel with every adjustment recorded.
- **The paper's storyline is a ledger**: which project is Main Figure N, numbered revision records
  with the evidence behind each change, snapshots and diffs, a compiled compendium PDF.
- **Procedures are commands** (`fa new project`, `fa ingest bundle`, `fa build --preflight`,
  `fa promote`, `fa retire`, ...): deterministic, with `--dry-run` and `--json`. AI agents call
  the same commands as MCP tools (`fa mcp`) — Claude Code, Gemini CLI, opencode, Antigravity,
  Cursor, Codex — and changes need the user's approval of a dry-run diff.

The core is domain-neutral (bars, lines with error bands, scatter, heatmaps, Venn diagrams, image
panels, ...); field-specific readers, bundle contracts and recipes come as plug-in packs. An omics
pack (`fig_atlas_omics`: volcano, MA, GO enrichment, motifs, ...) is included.

## Install

Python 3.10+.

```bash
git clone https://github.com/ibs-cmg-ngs/fig-atlas
cd fig-atlas
pip install -r requirements.txt
pip install -e .            # add [docs] for the documentation site
fa --help
```

With conda: `conda env create -f environment.yml -p ./fig-atlas`, then `conda activate ./fig-atlas`
and `pip install -e .`.

## Quick start

Your figures live in a *project repository*, separate from this package:

```bash
fa init my-figures && cd my-figures
fa new project first-figure
fa bundle check /path/to/bundle                       # inputs/data.csv + metadata/metadata.yaml
fa ingest bundle /path/to/bundle --project first-figure
fa build first-figure --preflight
```

The figure, its README (panel notes, statistics, data provenance) and the check results appear
under `outputs/first-figure/`. Change any value in `configs/config_first-figure.yaml` and rebuild.

This repository is itself a project repository with two worked examples: the tutorial's example
bundles (`examples/`) and an imaging figure from public microscope images (`pilot-imaging`).

## Documentation

Online: **https://ibs-cmg-ngs.github.io/fig-atlas/** — or locally: `pip install -e .[docs]`, then `mkdocs serve`
and open http://127.0.0.1:8000.

- **Researcher guide** (`docs/guide/`, Korean): what the tool does and how a figure flows from data
  to paper, for scientists with no programming background.
- **Tutorials**: [first figure](docs/tutorials/first_figure.md) (run by CI as written),
  [imaging figure](docs/tutorials/imaging_figure.md).
- **How-to**: [connect AI agents](docs/howto/ai_agents.md), [write a domain pack](docs/howto/new_domain_pack.md).
- **Reference** (generated from the code): [commands](docs/reference/cli.md),
  [config keys](docs/reference/config.md), [renderer gallery](docs/reference/gallery.md),
  [data bundle contracts](docs/contracts/README.md).
- **Design decisions**: [docs/decisions/](docs/decisions/README.md).
- **Rules for people and AI agents** working in a project repository: [AGENTS.md](AGENTS.md).

## Development

```bash
pip install -e .[docs]
pytest                         # unit, renderer snapshot, tutorial and documentation tests
fa reference --check && fa inventory --check && fa lint --hardcoded --check && fa claims --check
mkdocs build --strict
```

New renderers start with `fa new renderer <name>` (a module with its parameter schema, a test and
the package export). Renderers are shapes, not fields: see design decision 0003.

## Licence and citation

Code: MIT, © 2026 ibs-CMG-NGS ([LICENSE](LICENSE)). Please cite as in [CITATION.cff](CITATION.cff).
