---
title: 7. Checking the results
audience: researchers (no programming experience needed)
reviewed: 2026-10-14
---

# 7. Checking the results

> **Has this ever happened to you?** Uploading figures to a journal, you were asked separately for "Source Data files", "details of statistical tests" and "image processing", and stayed up the night before submission collecting them.

**The key idea:** every build gathers, in one folder with the figure, **a description of the figure (README)**, the values the figure shows, the statistics tables and the provenance record. What a submission needs is already in order.

## The results folder

The results of one figure are gathered in `outputs/project-name/figures/figure_01_name/`.

```
figure_01_main/
  figure_01.png                ← for the screen and talks
  figure_01.pdf                ← for print and submission (vector, editable text)
  figure_01.svg                ← for editing in Illustrator and the like
  README.md                    ← the figure's description (below)
  figure_01.provenance.json    ← the provenance record (a format for programs)
  figure_01_source_data/       ← the values each panel actually shows (when there are any)
  figure_01_statistics/        ← the statistical test tables (figures with stars)
```

**Do not edit the files of this folder by hand.** They are made anew at the next build, so your edits would be lost and the figure and its record would disagree. What you want to change, change in the config (chapter 6) or in the figure spec.

## Reading the figure's README

The README is a human-readable summary the build writes. This is how a real one is laid out (the microscopy pilot project).

| Part | Content | Where it comes from |
|---|---|---|
| Title | `Figure 1: Wortmannin drives FKHR-GFP into the nucleus…` | `title` in the figure spec |
| Panel-level analysis notes | What each panel shows, n, error bars, tests | `panel_notes` in the figure spec |
| Statistics | The statistics table files and which tests they are | The tables the analysis recorded (chapter 9) |
| Source data | A table of the values each panel shows | The values the analysis recorded |
| Images | A microscope image's original files, the cropped region, the brightness range | Recorded by the image panel (chapter 9) |
| Claim boundary | What the figure can and cannot claim | `claim_boundary` in the figure spec |
| Provenance | When it was built, software versions, fingerprints of the config and of the data files read | Recorded automatically (chapter 10) |

The title, panel notes and claim boundary are written by the researcher in the figure spec (under `figure_specs/`). The build fills in the rest.

## At printed size

Open the PDF at 100 % and you see the size on paper. The figure is as wide as the A4 text width (184.6 mm), and text set to 7 pt in the config is 7 pt on paper. So you can judge "can this be read?" right on the screen. If a journal asks for another width (e.g. a single column of 85 mm), change to that page setting and build again.

## What you do

💬 **Ask an AI:** "Show me the first-figure figure and summarise what its README says." The AI looks at the figure itself and describes it.

📂 **Look yourself:** open the folder `outputs/project-name/figures/` in your file browser: the figure files (PNG, PDF) and the README are there. The README is a text file, so Notepad opens it too.

💡 **Tip (if you use VS Code):** open the README and press `Ctrl+Shift+V` to see its tables and headings laid out. In a repository on GitHub, the web page shows it the same way.

💬 **Packing material for submission:** "Pack first-figure for submission." The figure, its description, the values shown, the statistics tables and the provenance record are packed into one archive (zip). It is in a standard format for sharing research data (RO-Crate), so you can upload it as it is to a repository or a journal.

## Good to know

- The `outputs/` folder is not uploaded to the repository (GitHub): with the config and the data, the same figure can be made again any time.
- Building again from the same data and config gives **files that are the same down to the last byte**. "I rebuilt it and it came out slightly different" does not happen.
- The verification table in `outputs/project-name/manifests/` records whether these results were all made (chapter 8).

---
Previous: [6. Changing a figure: reading and writing the config](06-config.md) · Next: [8. Reading the check results](08-checks.md)
