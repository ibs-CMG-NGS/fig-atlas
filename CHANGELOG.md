# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased] — first public tree (0.1.0.dev0)

fig-atlas was developed in a private research repository from July 2026 and used for the figures
of one manuscript before being published as a package. This first public tree contains:

- **Projects and builds**: commented YAML configs as the single source of every visual value
  (parameter schemas for all renderers, `fa param scaffold / explain / sync`, `fa lint`),
  final-size rendering on page presets, `fa build` (analysis → publish → pre-print checks →
  verify), byte-identical rebuilds.
- **Pre-print checks** (`fa build --preflight`, `fa preflight`): 24 checks for overlaps, clipping,
  panel intrusion, print sizes, fonts, resolution, panel tags and colour (colour-vision deficiency,
  colormaps, contrast), with overlays and report / enforce modes.
- **Provenance**: automatic records of the files each figure read, its code, configuration and
  environment; `fa status`, `fa impact`, `fa lineage`, `fa diff-figure`; live numbers in legends
  (`fig_atlas.claims`), statistics tables (`fig_atlas.stats`), Source Data, image adjustment
  records, RO-Crate export (`fa export`).
- **Storyline ledger**: `storyline.yaml`, a generated figure–project registry, numbered revision
  records, compile-time snapshots, diffs and evidence tracing (`fa storyline ...`).
- **Commands for every procedure**: `fa init`, `fa new project | renderer`, `fa bundle check`,
  `fa ingest bundle` (Case B), `fa promote`, `fa retire`; dry-run diffs, JSON output, idempotent.
- **AI agents**: `fa mcp` serves the commands as MCP tools; checked with the CLI, opencode and
  Antigravity giving identical files.
- **Domain-neutral core and packs**: plug-in entry points for renderers, contracts, ingest maps,
  recipes and commands; an omics pack; an image panel; generic line-with-band and
  effect-vs-significance shapes.
- **Documentation**: a researcher guide (Korean), tutorials run as tests, how-to guides, generated
  reference pages and a renderer gallery, design decision records, a documentation site (MkDocs).
