# Tutorial: after the data change — finding stale figures, redrawing, revising the storyline

> **Which entry point:** this is what happens **after** a figure has come in, whichever entry point (Case A, B, C) it took. Here it starts from an example bundle (Case B).

A paper figure is not drawn once and done. Data are delivered again, figures move up to paper Figures, the storyline changes. This tutorial follows that course with commands alone.

- Make two figures that read the same data, and **promote** one to paper Figure 1.
- Start a **storyline** and make the first compendium (R000).
- When data are **delivered again**, find which figures are stale (`fa status`) and which figures read that file (`fa impact`).
- Redraw, and record what changed as a storyline **revision record** (R001).

You need: a Python environment with `fa` installed, and a project repository made with `fa init` (or this repository). The example bundles are in `examples/gallery/`. The commands below are for a POSIX shell.

## 1. Two figures that read the same data

<!-- run -->
```bash
fa new project lab-dose --domain lab --category exploratory
fa new project lab-dose-qc --domain lab --category exploratory
mkdir -p raw_data/dose-study
cp -r examples/gallery/dose_response raw_data/dose-study/
fa ingest bundle raw_data/dose-study/dose_response --project lab-dose
fa ingest bundle raw_data/dose-study/dose_response --project lab-dose-qc
fa build lab-dose lab-dose-qc --preflight
```

The two projects read the same bundle. Think of one as the figure for the paper and the other as a quality-control figure.

## 2. Promote to paper Figure 1

<!-- run -->
```bash
fa promote lab-dose --figure 1 --slug viability
```

The config, the analysis script and the figure spec move to `lab/paper/`, and the name becomes `lab-paper-main-fig1-viability`. The paths inside the files are updated too, and the promoted project is built once.

## 3. Start the storyline

<!-- run -->
```bash
fa storyline new dose --title "Dose study"
```

This creates `docs/storylines/dose/storyline.yaml` (which project is which Figure) and `docs/storylines/figure_plan_dose.md` (the narrative and the revision records). Write Figure 1 into `storyline.yaml`.

<!-- replace: docs/storylines/dose/storyline.yaml | figures: [] -->
```yaml
figures:
  - slot: "Main Figure 1"
    project: "lab-paper-main-fig1-viability"
    figure_number: 1
    description: "Viability over dose"
```

<!-- run -->
```bash
fa storyline registry
fa storyline check
fa storyline compile --strict
```

`registry` rewrites the table of the plan document, `check` checks it against the projects, and `compile` makes the compendium PDF and keeps it as **R000** (`outputs/storylines/figure_plan_dose/R000/`). With `--strict` it refuses when a figure is stale or has preflight errors.

## 4. When the data are delivered again

Say the lab sent the data again with compound B's values corrected. We do not edit the original; the newly received file takes its place (here, simulated by changing one line).

<!-- replace: raw_data/dose-study/dose_response/inputs/data.csv | compound B,0.01,1,100.99 -->
```text
compound B,0.01,1,90.99
```

<!-- run -->
```bash
fa status
fa impact raw_data/dose-study/dose_response
```

`fa status` shows the two figures that read the file as **STALE**, with the reason (`input changed: .../data.csv`). It compares content hashes, so a file only opened and closed does not count as changed. `fa impact` finds every figure that read the bundle, across projects. The old output folder from before the promotion is listed separately, as "old output of a project that no longer exists".

In this state, making the compendium is refused:

```bash
fa storyline compile --strict
#   [!] stale: lab-paper-main-fig1-viability fig 1 -- input changed: raw_data/dose-study/dose_response/inputs/data.csv
#   [x] --strict: not compiling with stale figures or preflight errors
```

Redraw, and see what changed since the last compendium.

<!-- run -->
```bash
fa build lab-paper-main-fig1-viability lab-dose-qc --preflight
fa storyline diff --draft
```

`diff --draft` gathers what changed since R000 (figures and the reason: data / config / code) and proposes a draft line for the revision record. No numbers need copying by hand.

## 5. Write the revision record

Complete the proposed line with a title and the reason, and put it under `## Revisions` in the plan document.

<!-- replace: docs/storylines/figure_plan_dose.md | ## Revisions -->
```markdown
## Revisions

> **2026-10-13 Revision (1) — corrected delivery**: the lab re-sent the dose data with compound B corrected; Main Figure 1 was rebuilt from it. Changes since R000: `lab-paper-main-fig1-viability` (data).
```

<!-- run -->
```bash
fa storyline revisions --sync
fa storyline compile --strict
fa storyline snapshots
fa storyline diff
```

`revisions --sync` copies the revision record to `docs/storylines/dose/revisions/R001.md` (then fill in that file's `kind` and `evidence` front matter), and `compile` keeps the new compendium as **R001**. R000 stays as it was. `fa storyline diff` writes a report of the difference between the two compendiums: which inputs of which Figure changed.

Note the delivery in the data request document (`docs/data_contracts/*_request.md`), and `fa storyline evidence "Main Figure 1"` traces the figure back to that request and the revision record.
