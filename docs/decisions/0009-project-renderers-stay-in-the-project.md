# 0009. A project's own renderers stay in the project; what they rely on is a public contract

- Status: proposed
- Date: 2026-11-18

## Context

Most people install a release of fig-atlas and keep their figures in a project repository made with
`fa init`. When no installed renderer draws the plot they need, `fa new renderer` writes one into
that repository's `renderers/` folder, which fig-atlas finds without installing anything
(`fig_atlas/plugins.py`). With an AI agent this becomes the ordinary way to get a new plot shape:
the agent writes a renderer in minutes, and a figure made from a mockup (Case C) nearly always ends
in one.

[Decision 0003](0003-renderers-are-shapes.md) says where a renderer goes *in the fig-atlas source*:
a shape belongs in the core. It says nothing about renderers outside the source, and the tooling
leaned toward bringing them in: `fa new renderer` told the user that a shape other projects could
use "is worth offering to the fig-atlas core later", and the rules speak of renderers being "added
back so future projects inherit them". A path for that -- a command that turns a project renderer
into a pull request to the core -- was considered.

It was set aside. A researcher who installed a release wants their figures drawn reproducibly;
maintaining a package is not their job, and a step that expects it is a hurdle with nothing in it
for them. People who do want to change fig-atlas already work in a clone and can open a pull
request. And the reuse that matters most already happens: every project of a repository shares its
`renderers/`, which for a lab is the unit that accumulates.

What a project renderer does need is to keep working. Once renderers live outside the package for
good, the names they import and the way they are called are an interface other people's code
depends on -- until now they were internal, changed whenever the core renderers changed together.

## Decision

1. **A project's `renderers/` is a home, not a waiting room.** A renderer there belongs to that
   repository and every project in it can use it. Nothing asks for it to be offered to the core,
   and no command exists to do so.
2. **The core grows when maintainers see a shape recur** -- in the case-study repositories they
   work in, or in an issue that asks for a plot. An issue is all a user needs to ask for one.
3. **What a renderer outside fig-atlas relies on is a public contract**, listed in one place,
   `fig_atlas/renderer_api.py`:
   - the calling convention: `render_<name>(ax, df, params)` draws on a matplotlib Axes from a
     DataFrame and a dict of parameters and returns the rows it drew; the module sets `SCHEMA` and
     `FAMILY`;
   - a repository's `renderers/__init__.py` exports its renderers and may carry an `INGEST` table;
   - the names `Schema`, `Param`, `CODE_DEFAULT`, `StyleRef`, `typography`, `uses_schema`
     (`fig_atlas.schema`), `text_param` (`fig_atlas.params`), `stars` (`fig_atlas.stats`),
     `fig_atlas.render`, and every public renderer function `fig_atlas.renderers.render_*`.

   A release removes or changes one of these only after a release that warns about it
   (`DeprecationWarning`), and the changelog says so under "Changed" with what a project renderer
   has to do. Anything else -- a module or name starting with `_`, a helper inside another
   renderer's module -- may change in any release.
4. **The project repository checks its own renderers.** The rules `fa init` writes (`AGENTS.md`)
   tell people and agents to draw a new shape as a renderer in `renderers/`, starting from
   `fa renderers` and `fa new renderer --from`, never as drawing code in an analysis script or an
   edit to the installed package. The CI workflow `fa init` writes runs `tests/renderers` when the
   repository has renderers, so an upgrade that breaks one shows up in the pull request that pins
   the new release.

## Consequences

- `fa new renderer` in a project repository no longer suggests offering the renderer to the core;
  it says the renderer relies only on the contract.
- `fa new renderer --from` copies a core renderer whole, and many core renderers use internal
  helpers (`fig_atlas.renderers._basic`). The command lists the copy's imports that are outside the
  contract, so the user knows which lines a later release may break. If copies keep needing the
  same helper, that helper should get a public name and join the contract, rather than every copy
  depending on an internal one.
- `tests/test_renderer_api.py` fails when a contract name disappears, and checks that the templates
  `fa new renderer` writes import only contract names.
- fig-atlas follows semantic versioning, which before 1.0 lets a minor release change anything;
  for the renderer interface this decision promises more: a release that warns comes first.
- Repositories made by an earlier `fa init` keep their old `AGENTS.md` and CI workflow; they can
  copy the new rule and step from a fresh `fa init` in an empty folder.
- [Decision 0003](0003-renderers-are-shapes.md) stands for the fig-atlas source: there a shape still
  belongs in the core.
