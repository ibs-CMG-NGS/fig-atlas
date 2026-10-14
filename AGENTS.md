# Project Rules (Figure Atlas Template)

These are the rules of this repository, for people and for AI agents alike. This file is their single
source: agents read it directly (Codex, opencode, Cursor, Antigravity, Copilot, and Gemini CLI through
`.gemini/settings.json`), and `CLAUDE.md` imports it for Claude Code -- edit the rules here only.
`tests/test_agent_docs.py` checks that the paths and `fa` commands named here exist. The reasons behind
the main design choices are recorded in `docs/decisions/` (ADRs). Procedures are `fa` commands
(`fa --help`); agents connected over MCP call the same commands as tools (`docs/howto/ai_agents.md`).

**Documentation in two languages.** The documentation site is English, the source of truth, with a
Korean version beside each page (`page.md` and `page.ko.md`, shown at `/ko/`). Change both in the same
commit: `tests/test_docs_i18n.py` fails when their headings, code blocks, tutorial steps, images,
tables or link targets differ (`docs/decisions/0006-documentation-in-two-languages.md`). A new page
is written in both languages; `docs/i18n_pending.txt` lists pages not yet in English (none now).

---

## 1. Core Philosophy & Development Principles

1. **Immutability of Raw Data**:
   * Raw datasets (CSV/TSV, etc.) must NEVER be modified or edited directly. Keep them strictly read-only under `raw_data/<project_name>/<bundle_name>/inputs/data.csv`.
2. **Config-Driven Visualization & Zero Hardcoded Styling Rule**:
   * All visual attributes (axis limits, font sizes, titles, legends, colors, margins, coordinates, and spacings) must be dynamically controlled via configurations (`configs/config_*.yaml` and/or bundle `metadata/metadata.yaml`) using `params.get()`.
   * **Strict prohibition of hardcoded visual variables**: Rendering scripts must NEVER contain hardcoded "magic numbers" or fixed strings for visual styling (e.g., canvas margins, padding, panel titles, annotation fonts, thresholds, line widths, marker sizes, tick rotations, or subgridspec ratios). Everything that influences the visual layout, typography, or styling of a figure must be exposed as a configurable parameter in YAML with sensible fallbacks (`cfg.get("param_name", default)`). Any researcher or collaborator must be able to fine-tune spacing, labels, colors, and layout entirely from `configs/config_<project_name>.yaml` without editing Python scripts.
   * **The project config is the source of truth, not just an override layer.** Whenever a bundle's `metadata/metadata.yaml` already carries a `plot_params` block (Case B/C), copy the *full* block into `configs/config_<project_name>.yaml` under `plots.<plot_name>` — every key the renderer's `params.get()` calls reference (colors, thresholds, xlim/ylim, cmap, sizing, top_n, etc.), not only the values you intend to change. Bundle metadata may still act as a fallback in the merge chain (`bundle < global_style < config`), but nothing a user might want to tune should be left depending on that fallback. See the `plots:` blocks of `configs/config_pilot-imaging.yaml` for the expected shape; `fa ingest bundle` writes such a block for you (docs/decisions/0002). Renderers declare their parameters in a `SCHEMA` (fig_atlas.schema); keys an analysis script reads itself are declared in that script's `LAYOUT_SCHEMA` (dotted paths, `*` for one level) -- `fa param scaffold` / `fa param sync` / `fa param explain` take descriptions from them, and `fa lint` lists the keys a build still takes from code defaults.
3. **Sample Renaming Principle**:
   * Abbreviations or publication-ready modifications to raw sample names must be mapped dynamically using the `sample_rename_map` configuration option inside the YAML at plot rendering time, keeping raw files intact.
4. **Global rcParams Harmonization**:
   * Common styles (border thicknesses, tick sizes, labels) across all subplots should be updated globally using Matplotlib `rcParams` at the start of the analysis script execution.
5. **Panel Tag Outer Bounding Box Alignment Rule**:
   * In multi-panel publication figures, panel identifiers (`a`, `b`, `c`, `d`, ...) must NEVER be aligned merely to the inner plot spine/data box. Instead, they must strictly define and align with the **outermost visual boundary (Outer Bounding Box)** of the entire subpanel (including y-axis titles, tick labels, and grouping brackets). Vertically stacked panels within a column (e.g., Col 0: a & c; Col 1: b & d) must share a unified vertical plumb line for their panel tags and maintain coordinated horizontal starting lines for their data bodies.
6. **Self-Documenting Config Files & Rich In-Line Commenting Rule**:
   * **Researcher Self-Service UI**: The configuration file (`configs/**/*.yaml`) is not merely a machine-readable key-value store; it is the **primary user interface (UI)** through which researchers inspect, understand, and fine-tune publication figures without reading Python rendering scripts.
   * **Mandatory Rich In-Line Comments**: Every visual parameter, layout ratio, threshold, and style option MUST be accompanied by clear, self-explanatory English comments containing:
     1. **Visual Role & Biological Semantics**: What element or behavior this key controls (e.g., `# X-axis symlog linear threshold: values within [-linthresh, linthresh] are plotted linearly`).
     2. **Unit & Coordinate System**: The explicit unit or coordinate space (e.g., `# inches`, `# points (pt)`, `# [0.0 ~ 1.0] figure-relative fraction`, `# data coordinates`, `# hex color`).
     3. **Tuning Guidance**: Concrete visual effect of increasing or decreasing the value (e.g., `# increase to widen the gap between heatmap and colorbar`, `# increment by 0.05 if row labels clip canvas edge`).
   * **Block-Level Structural Headers**: Subpanels, multi-tier GridSpecs, and complex grouped parameters must include structured block headers describing their overall architecture (e.g., `# [Panel a] Experimental timeline schematic`, `# [GridSpec 2x2 Layout] d, e, f, g alignment parameters`).
   * **Zero Comment Stripping**: When AI agents edit, update, or refactor YAML files, existing comments MUST be strictly preserved. Never rewrite YAML files using automated dumpers that strip comments (e.g., raw PyYAML `dump`). Maintain all formatting, section guides, and explanatory annotations intact. Scripted edits go through `fig_atlas.yamledit` (ruamel.yaml), which only edits a file that round-trips byte for byte and refuses the rest.


---

## 2. Naming Conventions

When creating or modifying files, agents must strictly follow these naming patterns:
* **Project Identifier (`<project_name>`)**: Designated name specified by the user (e.g., `pilot-imaging`).
* **Namespace (`<domain>/<category>`)**: Every project belongs to a domain (e.g. `lab`, `kim`, ...) and a category (`exploratory` or `paper`), determined by which researcher/study the project belongs to and whether it's an exploratory analysis or a paper-synthesis figure. Configs, analysis scripts, and figure specs for a namespaced project live under `<domain>/<category>/` inside `configs/`, `analysis/`, and `figure_specs/` respectively -- e.g. `configs/<domain>/paper/config_<domain>-paper-main-fig1-<slug>.yaml`. One-off test/sandbox projects with no assigned domain (e.g. `pilot-imaging`) stay flat at the top level of each directory and use `configs/config.yaml` as the default.
* **Configuration File**: `configs/<domain>/<category>/config_<project_name>.yaml` (sandbox default: `configs/config.yaml`).
* **Figure Specification**: `figure_specs/<domain>/<category>/figure_<number>_<project_name>.py` (e.g., `figure_specs/<domain>/paper/figure_01_<domain>-paper-main-fig1-<slug>.py`; sandbox: `figure_specs/figure_01_pilot-imaging.py`).
* **Consolidated Analysis Script**: `analysis/<domain>/<category>/<project_name>_analysis.py` (sandbox: `analysis/pilot-imaging_analysis.py`). A project's config always carries its own analysis script's exact path in `project.analysis_script` -- read that field rather than assuming the naming convention, since the build tooling (`fa build`, `Snakefile`) does the same.
* **Config file discovery is location-independent**: `fig_atlas.get_config()` and `fa build <name>` locate a project's config by filename search under `configs/` (recursively), not by assuming a fixed depth -- so a bare project name works the same whether the project is namespaced or flat/sandbox.
* **Create projects with `fa new project <name> --domain <d> --category <c>`** (or no namespace for a sandbox): it writes the config, analysis-script skeleton and figure spec in the right places (and, where the repository has one, adds the name to the VS Code build list in `.vscode/tasks.json`); `--dry-run` shows the files first.
* **Agents connected over MCP** (`fa mcp`; setup for Claude Code, Gemini CLI, opencode, Antigravity, Cursor, Codex in `docs/howto/ai_agents.md`) get these commands as tools (`fa_new_project`, `fa_ingest_bundle`, `fa_build`, `fa_figure_images`, `fa_promote`, ...). A tool that changes files returns a dry-run diff unless called with `apply: true`: show the diff to the user and apply only with their consent.
* **No editor is required.** Everything runs through `fa` commands (or the same commands as MCP tools); VS Code is an optional convenience. Where a repository keeps a VS Code build list (`.vscode/tasks.json`, the `Ctrl+Shift+B` dropdown), `fa new project`, `fa promote` and `fa retire` keep it in step, and `fa storyline check` reports a list that disagrees with the storyline; without that file these steps are skipped. A project made by hand in such a repository is added to the `projectSelector` options (alphabetically) by hand.

---

## 3. User Request Handling ("Ingest Plot" Protocol)

When the user requests custom plot ingestion (e.g., "Ingest this custom script", "이 스크립트 ingest 해줘" or requests integrating custom code), the agent must immediately activate the 7-phase ingestion protocol documented in `.agents/skills/ingest_plot/SKILL.md`.
* **Required Initial Step**: Confirm the target `<project_name>` with the user (whether it adds to an existing project or initializes a new one with `fa new project`).
* **Branching Logic (Data State Check)**:
  * **Case A (Unstructured custom script + raw data)**: Run all 7 phases sequentially to structure the directory, isolate raw data, extract parameters into `metadata.yaml`, refactor renderers, integrate configs/specs, and verify the build.
  * **Case B (Pre-packaged compliant bundle)**: If structured inputs (`inputs/data.csv` and `metadata/metadata.yaml`) are already present under `raw_data/<project_name>/`, **skip Phase 3 (data isolation) and Phase 4 (metadata creation)**. First run `fa bundle check raw_data/<...>/<bundle>` (structure, the contract for its `plot_type`, and the renderer that draws it; an error means a column the renderer needs is missing -- report it to the user instead of patching raw data). Then `fa ingest bundle raw_data/<...>/<bundle> --project <name>` (after `fa new project` for a new one) writes the full commented `plots.<name>` block -- the renderer, the bundle path, every schema parameter with the bundle's value where it gives one -- and builds; a project made by `fa new project` draws it with `draw_plots` and needs no code. The values are a starting point: bundles often carry on-screen sizes, so check the build with `--preflight` and tune text sizes in the config. Write or refactor a renderer only when no installed one draws the `plot_type` (`fa bundle contracts`), or for a figure the script lays out itself.
  * **Case C (Data + visual intent, no code)**: If the user provides raw data plus a **reference image (mockup/screenshot/sketch) or a natural-language description**, synthesize the renderer from the data + image instead of extracting it from user code. This case **requires** an interpretation-confirmation gate before generating code and a render-and-compare visual loop after. Follow the "Case C 전용 절차" section in `.agents/skills/ingest_plot/SKILL.md`.

**Asset accumulation (reuse-first)**: Treat the renderer packages (plot types) and `styles/*.yaml` (named style presets) as growing asset libraries. Reuse an existing renderer/preset whenever one fits; author new ones only for genuinely new plot types or looks, and add them back so future projects inherit them -- start a renderer with `fa new renderer <name> [--plot-type <type>]` (a module with its SCHEMA, a test, the package export and, with `--plot-type`, the mapping `fa ingest bundle` uses; core by default, `--package <pack>.renderers` only for a field-specific shape). **Renderers are shapes, not fields**: a bar, line, scatter, heatmap or dot-matrix renderer belongs in the core (`fig_atlas/renderers/`) even when its first data were omics. A field (omics, electrophysiology, imaging, ...) lives in a domain pack as what is specific to it -- data readers and ingest adapters, bundle contracts, recipes (a core shape + the field's column roles, vocabulary and defaults; `fig_atlas/recipes.py`) and analysis helpers. Only a shape that means nothing outside its field (a sequence logo, genome tracks) is a pack renderer. The core never imports a pack (`tests/test_core_boundary.py`). Scripts may draw by name with `fig_atlas.render("volcano", ax, df, params)` and need not know where a renderer lives (`fa renderers` lists the names); the omics pack still holds renderers from before this rule, moved to core shapes + recipes one at a time (roadmap 6a.3).

---

## 4. Manuscript Figure Assembly Protocol (3-Phase Lifecycle)

When the user asks for paper storylines, figure candidate screening, or assembling multi-panel manuscript figures (e.g., "논문 스토리라인 짜줘", "Main Figure 1 합성해줘"), all agents must follow the 3-phase lifecycle described in the researcher guide (`docs/guide/11-lifecycle.md`) and the assemble skill (`.agents/skills/assemble_figure/SKILL.md`):
1. **Phase 1 (Exploratory)**: Conditions explored via atomic 1-Figure projects with clean manifests.
2. **Phase 2 (Screening & Storyline)**: Read `outputs/clean_atlas_manifest.csv` and `figure_specs/*.py`, propose a hypothesis-driven figure assignment plan in `docs/storylines/figure_plan_<topic>.md`, and obtain user approval.
3. **Phase 3 (Paper Assembly)**: Synthesize composite publication-grade figures (a paper project per figure, `<domain>-paper-main-fig<N>-<slug>` in `configs/`, `analysis/` and `figure_specs/` under `<domain>/paper/` -- usually an exploratory project promoted with `fa promote`) by reusing modular data loaders and the renderers (`fig_atlas/renderers/*`, `fig_atlas_omics/renderers/*`) under unified `GridSpec` layouts.
4. **Publication checks**: build paper figures with `fa build <project> --preflight` (or `python -m fig_atlas build ...`) and resolve every preflight **error** (overlaps, clipping, panel intrusion, print-size minimums, Type 3 fonts) through the config before reporting a figure as done; report warnings/info to the user rather than silently changing colours or design. Overlays: `outputs/preflight/<project>/`.
5. **Live numbers in legends**: a count, percentage or statistic quoted in a FigureSpec's `title`, `panel_notes` or `claim_boundary` must come from the data -- record it in the analysis script (`fig_atlas.claims.record("n_anchors", n)`) and write `{n_anchors:,}` in the text; publish fills it and verify fails on a placeholder with no value. Do not add hand-typed result numbers: `fa claims --check` (CI) fails when a figure has more than `docs/baselines/hand_typed_numbers.csv`. Thresholds, figure references and design values (time points, doses) are fine as typed.
6. **Significance marks come from `fig_atlas.stats`**: a figure that draws stars or brackets runs its tests through `fig_atlas.stats` (test, multiple-testing correction and star thresholds from the config) and registers the test table with `stats.record(table, name=...)` before saving; the build writes it beside the figure, publish copies it to `figure_NN_statistics/`, and verify fails if it is missing. Describe the test in the legend with a live claim (e.g. `describe_stars(params)` recorded as `{star_rule}`), not typed text, so the legend follows the config. Do not call scipy tests directly in a renderer or script for marks that are drawn.
7. **Images are adjusted in the panel, never beforehand**: draw microscope images, blots and gels with `render_image_panel` from the original files (crop, linear display range per channel, gamma, scale bar from `pixel_size`); never save a brightened or cropped copy as input. The build records the source hashes and every adjustment, the README lists them, and verify fails if a source image changed; when verify warns about a nonlinear adjustment (gamma != 1), say so in the figure legend.

---

## 5. Promotion & Retirement Protocol (탐색 프로젝트의 논문 승격 및 은퇴 프로젝트 아카이빙 규칙)

1. **Strict 1:1 Numbering Alignment between Storylines and Paper Projects**:
   * The manuscript Main Figure number declared in the storyline (`docs/storylines/figure_plan_<topic>.md`) MUST strictly match the project identifier and config name: `configs/<domain>/paper/config_<domain>-paper-main-fig{N}-<slug>.yaml`.
   * Agents and researchers must never leave a mismatch where Main Figure 3 in the storyline points to an exploratory project name or an obsolete figure numbering.

2. **Promotion Protocol (Exploratory $\rightarrow$ Paper)**:
   * **Use `fa promote <project> --figure <N> --slug <slug>`** (`--supp` for a supplementary figure): run it with `--dry-run` first, then without. The same command renumbers a paper figure when one before it is merged or dropped. It performs the steps below and builds the promoted project once; it lists other files that still name the old project and leaves the storyline to you (record the figure in `storyline.yaml`, then `fa storyline registry` and `fa storyline check`).
   * When an exploratory project is promoted to a manuscript Main Figure:
     * **Config**: Relocate to `configs/<domain>/paper/config_<domain>-paper-main-fig{N}-<slug>.yaml`. Update `project.name`, `project.spec_pattern`, and `project.analysis_script`.
     * **Analysis Script**: Relocate to `analysis/<domain>/paper/<domain>-paper-main-fig{N}-<slug>_analysis.py`. Update fallback `CONFIG_PATH` to point to the new config.
     * **Figure Specs**: Relocate to `figure_specs/<domain>/paper/figure_<number>_<domain>-paper-main-fig{N}-<slug>.py`. Update `source_stem` (pointing to `<domain>/paper/<project_name>/figures/...`) and `primary_code`.
     * **Cross-References**: Verify and update any dependent projects (e.g., Supplementary figures or cross-project data loaders) referencing the old config path.
     * **Build list** (only where `.vscode/tasks.json` exists): include the new project in the `projectSelector` options and remove old exploratory `-full` aliases.

3. **Retirement & Archiving Protocol**:
   * **Use `fa retire <project>`** (`--dry-run` first): it performs the steps below -- move to `<domain>/archive/`, update the moved paths, drop it from the VS Code build list if there is one -- and builds the retired project once to confirm it still builds.
   * When an earlier paper draft or exploratory figure is superseded or retired from the storyline:
     * **Never delete raw assets or reproducible code**.
     * Move the superseded config, analysis script, and figure specs to `<domain>/archive/` subdirectories (`configs/<domain>/archive/`, `analysis/<domain>/archive/`, `figure_specs/<domain>/archive/`).
     * Update the moved files' paths to their new location -- `project.analysis_script` in the config, `primary_code` (and `source_stem`, if it named the old namespace) in each figure spec -- then build the retired project once (`fa build <name>`) to confirm it still builds. A retired project must stay independently buildable.
     * Where `.vscode/tasks.json` exists, remove the retired project name from its `projectSelector` so the build dropdown stays uncluttered.

4. **Master Mapping Registry Table**:
   * Every storyline document (`docs/storylines/figure_plan_<topic>.md`) must feature a **Master Figure-Project 1:1 Mapping Registry** table at the top. This table acts as the index linking every Main Figure (1 to N) and Supplementary Figure to its exact clickable config, analysis script, and figure spec file. Write these as repository-relative links (e.g. `../../configs/<domain>/paper/config_<project>.yaml` from `docs/storylines/`), never `file:///` absolute paths -- those break on every other machine. The table is generated: record the assignment in `docs/storylines/<topic>/storyline.yaml`, then run `fa storyline registry` (rewrites the table) and `fa storyline check` (configs, specs, `.vscode/tasks.json` and archive consistency) -- never edit the table by hand.

5. **Revision Records**:
   * Every storyline change is logged in the storyline md as a numbered `> **YYYY-MM-DD 개편(N) — title**: ...` block (N = the latest number reported by `fa storyline revisions`, plus one; never reuse a number for a different change). Then run `fa storyline revisions --sync`, which copies the block verbatim into `docs/storylines/<topic>/revisions/RNNN.md`, and fill that record's `kind` and `evidence` front matter. Sync never overwrites an existing record and never edits the md. Before writing the block, run `fa storyline diff --draft` (what actually changed since the last snapshot) and quote it rather than copying numbers by hand; after adding it, compile with `fa storyline compile --strict` and save `fa storyline diff --write`.
   * Data requests (`docs/data_contracts/*_request.md`) carry front matter -- `status`, `date`, `delivered` (where the delivery landed) and `derived` (bundle files built from it); `fa storyline requests --sync` drafts it for new documents. Keep it current when data arrives; `fa storyline evidence <slot|project>` traces a figure back to the requests and revisions behind it.

