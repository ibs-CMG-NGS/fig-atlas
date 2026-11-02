---
title: Layout catalog -- tested layout assets between "no code" and "write it yourself"
status: approved (G1 passed 2026-11-02); implementation in progress
date: 2026-11-02
audience: AI agents implementing the plan, and the researcher who approves it
g1: "passed 2026-11-02 -- name `layouts`; `matrix` in v1; `single` dropped; the new chapter is inserted after 06 (as 07) and 07-13 renumber to 08-14"
related: fig-atlas `plans/PLAN_PLOT_CATALOG.md` (same card/status format), `AGENTS.md` 3 "Asset accumulation", `docs/guide/05-entry-paths.md`, `docs/guide/06-config.md`
---

# Layout catalog

**한 줄 요약** — "구조는 코드, 값은 config"를 철학으로 세우려면 구조의 **예시**가 자산이어야 한다.
이 계획은 자주 쓰는 그림 배치 5가지를 **테스트된 레이아웃 함수**(`fig_atlas/layouts/`)로 만들고,
각각에 예제 프로젝트·갤러리 그림·문서·테스트를 붙여, 연구자가 AI 없이도 import 또는 복사로
커스텀 그림을 만들 수 있게 한다. 새 DSL은 만들지 않는다.

> **Agents: read in this order before touching anything**
> 1. `AGENTS.md` (repository rules; zero hardcoding, asset accumulation, config comments)
> 2. this plan, sections 2-6 (decisions and the artifact contract)
> 3. `plans/PLAN_LAYOUT_CATALOG.status.yaml` (who owns which card; the single source of task state)
> 4. the card you are claiming in section 8, then the files it names
>
> Claim a card before writing code (section 9). One card per branch and PR. If your change needs a
> file another card owns, stop and hand off instead of editing it.

---

## 1. Why

The researcher guide now states the boundary honestly (`docs/guide/05-entry-paths.md`): a bundle-only
figure works while every panel fits one cell of an equal `rows x cols` grid; anything else -- spans,
size ratios, nested grids -- needs a layout script.

The repository's own evidence says that boundary is where most real figures live:

| | scripts | `add_gridspec` | height/width ratios | spans | nested | manual placement | `draw_plots` |
|---|---|---|---|---|---|---|---|
| exploratory (cmg-figures) | 54 | 51 | 48 | 29 | 16 | 10 | 2 |
| paper (cmg-figures) | 29 | 15 | 14 | 4 | 15 | 16 | 0 |

Measured 2026-11-02 by `python scripts/layout_coverage.py --repo ../cmg-figures` (card L-10), which
reads the projects' `*_analysis.py` scripts without running them; its docstring defines each column.
The first draft of this table counted by text search and differs where the definitions tightened:
helper modules beside the scripts are no longer projects (paper 32 -> 29); a panel spanning part of a
row (`gs[0, 0:2]`) is a span as well as a full-row one (exploratory 13 -> 29); a subfigure taking one
cell is a panel, while a second grid on the figure is nesting; and an axes placed or lined up inside a
cell is the panel's own business, not manual placement.

What the layouts cover (same run, 83 scripts):

| | scripts |
|---|---|
| drawn by one of the five layouts today | 20 (`stack` 7, `grid` 5, `wide_bottom` 4, `row` 4) |
| + a layout inside a cell of another (composition) | 37 |
| + `ratios` on `grid`/`matrix` (13), an align helper (6), an overlay helper (2) | 57 |
| not reached: drawn by a helper module or on the canvas | 15 |
| not reached: a second grid placed over the first by bare numbers | 11 |

Layout code of the 20 matched today falls from a median of 9 lines to 5.5 (an estimate: the layout
call, `finish`, one line per cell, inner grids kept). Composition is what the unmatched scripts
mostly lack -- a stack whose rows hold their own panels (`gs[r, c0:c1]`, the GO scripts with a computed
column count), a row whose first cell spans the column (`gs[:, 0]`), a row redrawn over a band of the
outer grid -- not a sixth shape. Adding names would not reach them; letting a cell hold a layout
(and `finish` fit and tag through the levels) would.

So today "structure is code" is true, but the code is retyped every time, unconventionally, and the
non-obvious parts (outer-bbox fitting, panel-tag plumb lines) are the parts most often wrong.
The missing asset class is **layout**: a tested way to say "2x2 with a full-width bottom row" in code.

A philosophy needs examples. Sections 4-7 define what one example must contain so that it is safe to
copy, safe to test, and citable in the method paper.

## 2. Decisions (fix these; changing one needs a plan revision)

- **D1. Structure is code, values are config.** A layout is Python; every number a user might tune
  (ratios, gaps, padding, tag size) is read from the `figures:` block with a default.
- **D2. Layouts are functions, not a DSL.** No `layout: "aab\nccd"` key in `figures:` for v1. A DSL
  is unverifiable intent; a function is ordinary code that can be copied, debugged and tested.
- **D3. One asset = one file.** `fig_atlas/layouts/<name>.py` per layout, so agents work in parallel
  without merge conflicts, mirroring `fig_atlas/renderers/`.
- **D4. Letters are explicit.** `wide_bottom(fig, fcfg, top=("a", "b"), bottom="c")` -- never
  "letter = index in `plots:`". Reordering panels must not silently relabel a figure.
- **D5. Core, not a pack.** Layouts are figure-level shapes, meaningless only outside this package;
  they belong in `fig_atlas/layouts/` (`tests/test_core_boundary.py` must stay green).
- **D6. Layouts never touch ingest.** `fa ingest bundle` keeps writing equal-grid blocks; a layout is
  chosen in the analysis script. No "auto-place this bundle into cell c".
- **D7. Every layout ships with a picture, an example and a test** (section 5). No exceptions: an
  undocumented, untested layout is a liability.
- **D8. Do not change `draw_plots` semantics in this plan.** `layouts.grid` must reproduce its output
  exactly (card L-05), which gives the parity test and a future migration path without a rewrite now.

## 3. Scope

**In scope**

- `fig_atlas/layouts/`: `_core.py` (grid construction, `Layout`, `finish`) plus five layouts:
  `wide_bottom`, `stack`, `grid`, `matrix`, `row`
- one example project per layout under `examples/layouts/<name>/`, with a gallery picture
- generated reference page `docs/reference/layouts.md`, one guide chapter `docs/guide/07-layouts.{md,ko.md}`
  (bilingual, nav entry, cross-links from chapters 6 and 11)
- tests: per-layout behaviour, `grid` parity with `draw_plots`, gallery coverage
- a coverage measurement script and its table (the method paper's evidence)
- the status file and its checker (card/claim protocol)

**Out of scope (write these down as non-goals in the guide chapter)**

- a mosaic/layout DSL in `figures:`, nested layouts in config, per-panel absolute positions
- a `single` layout: one panel is `grid(columns=1)`, and a figure that draws itself on the canvas
  (a schematic) is a renderer with the `(fig, df)` shape, not a layout (G1, 2026-11-02)
- automatic layout selection, or ingest writing layout code
- changing `draw_plots`, `fit_in_cells` or `place_panel_tags` semantics
- new renderers (a layout arranges panels; it does not draw one)
- the method paper text itself (card L-11 produces the table/figure inputs only)

## 4. The layout asset contract

One layout is done only when all six parts exist. Cards in section 8 are grouped so that a card can be
reviewed on its own, but L-08/L-09a/L-09b are the cards that make a layout *usable*.

| # | Part | Location | Rule |
|---|---|---|---|
| 1 | function | `fig_atlas/layouts/<name>.py` | returns `Layout`; reads only `figures:` values, with defaults |
| 2 | docstring | same file | shape (drawn as ASCII), letters, config keys, panel count, when to use, how to adapt |
| 3 | example | `examples/layouts/<name>/` | `config.yaml` (the `figures:` block with comments) + `script.py` (<= 25 lines) + synthetic data |
| 4 | picture | `docs/reference/layouts.md` | generated from the example, like `docs/reference/gallery.md` |
| 5 | test | `tests/layouts/test_<name>.py` | cells do not overlap, every letter present, tags placed, example builds |
| 6 | index entry | `docs/guide/07-layouts` + this plan section 6 | one table row: shape, letters, panels, config keys, example path |

## 5. API (frozen by card L-02; revisions need a plan edit)

```python
# fig_atlas/layouts/__init__.py
from ._core import Layout, finish
from .grid import grid
from .wide_bottom import wide_bottom
from .stack import stack
from .matrix import matrix
from .row import row
__all__ = ["Layout", "finish", "grid", "wide_bottom", "stack", "matrix", "row"]
```

```python
# fig_atlas/layouts/_core.py
@dataclass(frozen=True)
class Layout:
    cells: dict[str, SubFigure]        # letter -> subfigure; draw the panel here
    columns: list[list[str]]           # tag plumb-line groups (place_panel_tags' `columns`)
    rows: list[list[str]]              # tag horizontal alignment groups (`align_rows`)
    shape: str                         # e.g. "2x2 + full-width bottom row", for logs and the gallery

def finish(fig, layout: Layout, fcfg: dict) -> list:   # fit_in_cells + place_panel_tags
    ...
```

Usage in an analysis script (this is the "60 lines -> 3 lines" claim; keep the example this small):

```python
fcfg = CFG.get("figures", {})
lay = layouts.wide_bottom(fig, fcfg, top=("a", "b"), bottom="c")
render_volcano(lay.cells["a"], df_a, params["a"])
render_line_band(lay.cells["b"], df_b, params["b"])
render_dot_matrix(lay.cells["c"], df_c, params["c"])
layouts.finish(fig, lay, fcfg)
```

Rules the implementation must follow:

- `fig.add_subfigure(gs[...])` per letter, exactly as `draw_plots` does today
  (`fig_atlas/bundle_figure.py:98`) -- renderers that lay out their own axes then stay inside the cell.
- `finish` calls `fit_in_cells` (cell bbox based, `bundle_figure.py:135+`) and `place_panel_tags`
  (`fig_atlas/renderers/panels.py:18-56`) with the layout's `columns` and `align_rows=layout.rows`.
- All tuning values come from `figures:`: `wspace`, `hspace`, `panel_pad_mm`, `tags.{show,size,pad_pt}`
  and the layout's own sub-block, e.g. `figures.wide_bottom.height_ratios`. `params.get`-style
  defaults only; no literal magic numbers (AGENTS 1.2). Every key gets a commented entry in the
  example config (AGENTS 1.6). Gaps are realized as separator rows/columns, not passed to the
  GridSpec: matplotlib ignores `wspace`/`hspace` for a SubFigure (section 14, implementation note);
  the default is 0, which gives exactly the cells `draw_plots` makes.
- Panel letters are `string.ascii_lowercase`-compatible single characters; validate at call time and
  raise with the offending letter and the allowed count.

## 6. The five layouts (v1) and why each exists

Evidence is the count of the first draft (text search over `analysis/*/{exploratory,paper}/*.py` in
`cmg-figures`); "matched" is what `scripts/layout_coverage.py` assigns to the layout (L-10, section 1).

| name | shape | cells / letters | evidence (scripts) / matched | config sub-block |
|---|---|---|---|---|
| `wide_bottom` | `n x 2` grid + one panel spanning the last row | `top=(...), bottom="x"` | 14 (2x2 with `gs[1, :]`) / 4 | `wide_bottom.height_ratios` |
| `stack` | one column, `n` rows | `letters=("a","b",...)` | 14 (2x1, 3x1, 4x1) / 7 | `stack.height_ratios` |
| `grid` | equal `rows x cols`, one panel per cell (same as `draw_plots`) | `letters` or `columns=` | all equal-grid figures / 5 | -- (reads `columns`, `wspace`, `hspace`) |
| `matrix` | many small panels, `rows x cols`, uniform | `letters`, `columns=` | 6 (5x3) / 0 | `matrix.wspace/hspace`, `matrix.columns` |
| `row` | one row, `n` cells | `letters` | 4 (1x2, 1x3, 1x5) / 4 | `row.width_ratios` |

The gap between evidence and matched is mostly composition (section 1). `matrix` matches none today
because all six `5x3` scripts give their rows and columns unequal sizes; with `ratios` they would.

Every layout's gaps default to 0 -- cells exactly as `draw_plots` makes them -- except `matrix`
(0.06 / 0.12), so a dense wall is separated without retuning the rest of the project.

`wide_bottom` covers the "schematic strip" case when the strip spans all columns; no separate
`band` layout in v1.

A one-panel figure is `grid(columns=1)`, not a layout of its own (G1). The two `1x1` scripts counted
above and the paper schematics are covered that way; a figure that draws itself on the canvas stays a
`(fig, df)` renderer (`DRAWABLE`, `fig_atlas/bundle_figure.py:53-61`).

## 7. Repository changes (file by file)

| file / dir | change | card |
|---|---|---|
| `plans/PLAN_LAYOUT_CATALOG.status.yaml` | new, card format of `PLAN_PLOT_CATALOG.status.yaml` | L-01 |
| `scripts/check_plan_layout_catalog.py` | validates status vs package (cards, ids, fields) | L-01 |
| `fig_atlas/layouts/_core.py` | `Layout`, `_grid`, `finish`, letter validation | L-02 |
| `fig_atlas/layouts/__init__.py` | explicit exports (append-only per layout card) | L-02 |
| `fig_atlas/layouts/{wide_bottom,stack,grid,matrix,row}.py` | one layout each | L-03..L-07 |
| `tests/layouts/test_<name>.py` | per-layout behaviour + example build | L-03..L-07 |
| `tests/test_layouts_core.py` | `grid` parity with `draw_plots`; `finish` tag/fitting invariants | L-02, L-05 |
| `examples/layouts/<name>/` | config + script + data | L-08 |
| `scripts/make_layout_gallery.py` | builds the pictures from the examples | L-08 |
| `scripts/make_reference.py` | add the `layouts.md` writer (generated page, never hand-edited) | L-08 |
| `docs/reference/layouts.md` | generated | L-08 |
| `tests/test_layouts_gallery.py` | every public layout has an example and a picture | L-08 |
| `docs/guide/07-*.md` .. `14-*.md` (14 files) | renumber old 07-13 to 08-14: file names, H1, front matter, nav, links, prose numbers | L-09a |
| `tests/test_guide.py` | chapter-number consistency test: every `chapter N` / `N장` names a chapter that exists | L-09a |
| `docs/guide/07-layouts.md`, `.ko.md` | new chapter inserted as 07, bilingual, structure parity | L-09b |
| `mkdocs.yml` | renumbered entries (L-09a) + the new 07 (L-09b) | L-09a, L-09b |
| `docs/guide/06-config.md`, `docs/guide/12-lifecycle.md` (+ ko) | cross-link to chapter 07 | L-09b |
| `scripts/layout_coverage.py` | measures coverage of a project repository | L-10 |
| `docs/paper/` (cmg-figures) | table + figure inputs, method note | L-11 |

Reference pages are generated by `scripts/make_reference.py`; hand edits fail review. Guide pages must
keep the bilingual structure the tests compare (`tests/test_docs_i18n.py`): same heading levels, code
blocks, tables and link targets in `page.md` and `page.ko.md`, `reviewed:` set to the edit date.

## 8. Cards

Format follows `plans/PLAN_PLOT_CATALOG.md` section 4. A card is finished when its `done_when` is met
and the commands in `verify` pass. Effort is agent-days.

| id | title | phase | priority | depends_on | files (owner) | effort |
|---|---|---|---|---|---|---|
| L-01 | status file + checker script | 0 | P1 | -- | `plans/PLAN_LAYOUT_CATALOG.status.yaml`, `scripts/check_plan_layout_catalog.py` | 0.5 |
| L-02 | core API: `Layout`, `_grid`, `finish`, exports, parity test skeleton | 1 | P1 | L-01 | `fig_atlas/layouts/_core.py`, `.../__init__.py`, `tests/test_layouts_core.py` | 1.0 |
| L-03 | `wide_bottom` | 1 | P1 | L-02 | `fig_atlas/layouts/wide_bottom.py`, `tests/layouts/test_wide_bottom.py` | 0.5 |
| L-04 | `stack` | 1 | P1 | L-02 | `fig_atlas/layouts/stack.py`, `tests/layouts/test_stack.py` | 0.5 |
| L-05 | `grid` + parity with `draw_plots` | 1 | P1 | L-02 | `fig_atlas/layouts/grid.py`, `tests/test_layouts_core.py` (parity half) | 0.5 |
| L-06 | `matrix` | 2 | P2 | L-02, L-03 (pattern) | `fig_atlas/layouts/matrix.py`, `tests/layouts/test_matrix.py` | 0.5 |
| L-07 | `row` | 2 | P2 | L-02, L-03 | `fig_atlas/layouts/row.py`, `tests/layouts/test_row.py` | 0.25 |
| L-08 | examples + gallery page + coverage test | 2 | P1 | L-03..L-07 | `examples/layouts/*`, `scripts/make_layout_gallery.py`, `scripts/make_reference.py`, `docs/reference/layouts.md`, `tests/test_layouts_gallery.py` | 1.5 |
| L-09a | renumber guide chapters 07-13 to 08-14 (rename only) + number consistency test | 3 | P1 | -- | `docs/guide/*.md` (14 files, rename only), `mkdocs.yml`, `tests/test_guide.py` | 1.0 |
| L-09b | new chapter 07 `layouts` (ko/en) + nav + cross-links | 3 | P1 | L-08, L-09a | `docs/guide/07-layouts.{md,ko.md}`, `mkdocs.yml`, `docs/guide/06-config.*`, `docs/guide/12-lifecycle.*` | 0.5 |
| L-10 | coverage measurement + reported table | 3 | P2 | L-03..L-07 | `scripts/layout_coverage.py` (+ its README section) | 0.5 |
| L-11 | method-paper inputs (coverage table, thumbnails, LOC deltas) | 4 | P2 | L-09b, L-10 | `cmg-figures docs/paper/` (separate repository; coordinate) | 1.0 |
| L-12 | optional: `fa layouts` + `fa_layouts` MCP tool | 4 | P3 | L-08 | `fig_atlas/repo_commands.py`, `fig_atlas/mcp_server.py`, docs | 1.0 |

Phases: 0 infra, 1 core + first two shapes, 2 the rest, 3 documentation and evidence, 4 paper and
surface. G1 passed 2026-11-02 (section 11), so Phase 1 may start.

`done_when` essentials (each card repeats these in its status entry):

- L-02: `Layout`/`finish` documented; a dummy layout passes a build; `tests/test_layouts_core.py`
  green; no import from `fig_atlas_omics` (`tests/test_core_boundary.py` green).
- L-03..L-07: function returns the documented letters; cells do not overlap; tags are placed on the
  outer bounding box (AGENTS 1.5); `finish` respects `panel_pad_mm` and `tags.*`; behaviour test green.
- L-05: for the same panels and `figures:` values, `grid` and `draw_plots` produce the same cell
  rectangles (within 1e-9) and the same tag groups.
- L-08: every public layout has an example that builds, a picture in `layouts.md`, and a docstring
  shape drawing; `tests/test_layouts_gallery.py` fails if one is missing.
- L-09a: rename-only commit (`git show --stat` shows `R100` for the 14 files); no prose, code block or
  link target changed except numbers; `tests/test_guide.py`, `tests/test_docs_i18n.py`,
  `tests/test_docs_site.py` green; the new number test finds no stale `chapter N` / `N장` (N >= 7).
- L-09b: chapter 07 in the nav; both languages pass the structure comparison; `reviewed:` set;
  chapters 06 and 12 cross-link to it.
- L-10: reruns the measurements in section 1 and writes a CSV (`project, level, grid, spans, nested,
  manual, matched_layout, loc_before, loc_after`); totals match this plan or the plan is updated.
- L-11: the table and figure are reproducible from the CSV by a command in the paper's evidence file.
- L-12: `fa layouts` lists name/shape/docstring/example; MCP tool generated from the parser
  (`fig_atlas/mcp_server.py:40-81` pattern), so CLI and MCP cannot drift.

## 9. Collaboration protocol (agents)

1. **Claim.** In `status.yaml`, set your card to `status: claimed`, `owner: <agent/model>`,
   `claimed: YYYY-MM-DD`, and add `branch: layout/L-xx-<slug>`. Commit that alone first, message
   `plan(layouts): claim L-xx`.
2. **Branch and PR.** One card per branch and PR. Title `feat(layouts): L-xx <title>`. Do not mix a
   docs card with a code card. L-09a and L-09b may share one PR but land as two commits: the renumber
   commit changes no content, so it reviews as renames.
3. **Ownership.** Only the card's `files` may be edited. `fig_atlas/layouts/__init__.py` is the single
   shared file: append your import in alphabetical order, never reorder, resolve a conflict by keeping
   both lines. `status.yaml`: edit only your card's fields.
4. **Stop at the seam.** If your change needs another card's file (e.g. a new `figures:` key read by
   `_core.py`), write the need into `status.yaml` as a note and hand off; do not edit it.
5. **Do not touch generated files by hand:** `docs/reference/*.md` (run `python scripts/make_reference.py`),
   `docs/reference/gallery/*`, `.vscode/tasks.json` (managed by `fa new project` / `fa promote`).
6. **Verify before handoff** (section 10) and record the exact commands and results in your card's
   `handoff` note, with the commit sha.
7. **Handoff format** in `status.yaml`:
   `status: in_review`, `handoff: "<sha>; tests: <command> -> <result>; open: <question or none>"`.
8. **Definition of done** is the card's `done_when` plus: tests green, docs bilingual, checker script
   green, no unrelated diff (`git diff --stat` reviewed), and the plan's evidence numbers still true.

### 9.1 Environment pitfalls (observed in this repository)

- **Never rewrite these files with PowerShell `Get-Content -Raw` + `Set-Content`.** It decodes UTF-8
  as the console code page and corrupts Korean text and arrows. Use the editor's targeted edit, or
  Python with `encoding="utf-8"` and explicit newlines.
- Keep the file's existing line endings (CRLF here); a whole-file LF rewrite shows up as hundreds of
  changed lines and hides the real change.
- `conda run -n fig-atlas` fails on this machine; call the environment's python directly:
  `C:\Users\KimYG\miniconda3\envs\fig-atlas\python.exe -m pytest ...`.
- `fa` is not on PATH in every session; `python -m fig_atlas <command>` is equivalent.

## 10. Verification

```bash
# per layout card
python -m pytest tests/layouts/test_<name>.py tests/test_layouts_core.py -q

# gallery and docs
python -m pytest tests/test_layouts_gallery.py tests/test_guide.py tests/test_docs_i18n.py tests/test_docs_site.py -q

# the example really builds, with the publication checks
python examples/layouts/<name>/script.py
python -m fig_atlas build <example-project> --preflight   # where the example is a project

# after the renumber (L-09a): numbers in prose point to real chapters
python -m pytest tests/test_guide.py -q

# plan consistency
python scripts/check_plan_layout_catalog.py

# boundary between core and pack
python -m pytest tests/test_core_boundary.py -q
```

Failures in the preflight **error** class must be fixed in the config or the layout function, not
waived (AGENTS 4.4).

## 11. Gates (researcher decisions)

- **G1 -- scope. PASSED 2026-11-02.** Five layouts (`wide_bottom`, `stack`, `grid`, `matrix`, `row`),
  functions not a DSL (D2), no `single` (a one-panel figure is `grid(columns=1)`), and the new chapter
  inserted after 06 as 07 with 07-13 renumbered to 08-14. Phase 1 may start.
- **G2 -- mosaic.** If, after L-10, a large share of figures is unmatched *because of an irregular but
  equal grid*, decide whether to add `figures.layout` (mosaic + ratios) to `draw_plots`. Do not build
  it before the measurement.
- **G3 -- dependencies.** Expected: none new. Any new dependency stops the card and returns here.
- **G4 -- release.** Ship the catalog in the next minor release only after L-09b (docs) is green.

## 12. Risks and how the plan handles them

| risk | handling |
|---|---|
| Layout functions drift from how real figures are written | L-10 measures the repository; each layout cites its evidence; L-11 reports honestly what is unmatched |
| Docs snippets rot | examples are built and snapshotted in CI (L-08); the reference page is generated |
| Over-abstraction (a layout for every shape) | five layouts, hard cap; new shapes are "copy the closest example", recorded in the guide |
| Layout functions become a second styling layer | they read only `figures:` keys; no colours, fonts or titles |
| Agents collide on shared files | ownership in section 8, append-only `__init__.py`, one card per PR |
| Korean/English docs desync | `tests/test_docs_i18n.py` is part of `done_when` |
| Coverage claim is over-read as "no code needed" | paper text says "X of Y identifiable layouts matched; layout code fell from A to B lines (median)" -- never "no code" |

## 13. Paper mapping (what this plan produces)

- **Table**: layout coverage per repository level, matched layout, unmatched reason, LOC before/after.
  Reproduce with `python scripts/layout_coverage.py --repo <path>`; the numbers in section 1 are the
  starting point.
- **Figure**: the five gallery thumbnails with the ASCII shape and the example script's line count.
- **Method text allowed**: the catalog and its tests are an *asset-accumulation* claim (renderer,
  style, layout), and the config block as the agent-to-scientist handoff.
- **Method text not allowed**: "researchers need no code"; "AI replaces the layout work"; any number
  not produced by L-10/L-11.

## 14. Decisions taken at G1 (2026-11-02)

| question | decision | note |
|---|---|---|
| name | `layouts` | `fig_atlas/recipes.py` stays "plot recipe"; a layout arranges panels |
| `matrix` | in v1 | 6 of the measured figures; differs from `grid` in label density |
| `single` | **dropped** | `grid(columns=1)` covers one panel; schematics are `(fig, df)` renderers |
| chapter position | after 06, as 07 | 07-13 renumber to 08-14 in a rename-only commit (L-09a) |

Measured cost of the renumber (2026-11-02): 14 files (07-13 x ko/en), 20 link targets, 41 English
`chapter N` (N>=7) mentions, 43 Korean `N장` mentions. `06b-` is not allowed: `tests/test_guide.py:64`
requires `^\d\d-[a-z0-9-]+\.md$`.

Remaining gates: G2 (mosaic, only after L-10), G4 (release after L-09b).

### Implementation note (2026-11-02, card L-02): how gaps are realized

`fig.add_subfigure(gs[r, c])` places the subfigure at the **raw** GridSpec cell: `SubFigure` computes
it from the width/height *ratios* only (`SubFigure._redo_transform_rel_fig`), so `wspace`/`hspace`
given to the GridSpec have no effect on panels drawn in subfigures. `draw_plots` therefore passes
spacing keys that do nothing today (no project config in `cmg-figures` sets them); the visible
separation of its panels comes from `panel_pad_mm` and from the tick labels inside each cell.

The layouts make the keys real: `_grid` inserts a separator row/column of ratio `space * mean(cell)`
between cells, which reproduces exactly the spacing `GridSpec` gives `add_subplot` grids. The default
is 0, so a layout's cells are identical to `draw_plots`' cells (the L-05 parity test) and a script can
migrate without the figure changing; raising `wspace`/`hspace` then separates panels for real.
`matrix` defaults to 0.06 / 0.12 in its own block. `draw_plots` is left as it is (section 3: its
semantics are frozen); making its spacing real is a separate decision, not a layout-catalog card.

## 15. Timeline (agent-days, sequential worst case)

| phase | cards | days |
|---|---|---|
| 0 | L-01 | 0.5 |
| 1 | L-02..L-05 | 2.5 |
| 2 | L-06..L-08 (L-07 is 0.25) | 2.25 |
| 3 | L-09a, L-09b, L-10 | 2.0 |
| 4 | L-11, L-12 (optional) | 2.0 |
| **total** | | **~9.25** |

L-03..L-07 can run in parallel after L-02 (one branch each); L-10 can start as soon as L-03 lands
because it measures existing repositories, not the catalog.
