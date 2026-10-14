---
title: 10. When the data change
audience: researchers (no programming experience needed)
reviewed: 2026-10-14
---

# 10. When the data change: provenance and freshness

> **Has this ever happened to you?** A collaborator wrote "I changed the alignment criteria and sent the result files again". You had to find, one by one, how many figures used those files and which ones to redraw.

**The key idea:** a build records, for each figure, **which files it read, with their fingerprints**. So when a file changes you see at once which figures are **stale**, and you can find every figure that uses a file.

## What the provenance record keeps

| Record | Example |
|---|---|
| Data files read, with fingerprints | `raw_data/.../data.csv` — `e8db6666271d` |
| The config, with its fingerprint | `configs/config_pilot-imaging.yaml` — `608a6c941faa` |
| Software versions | The repository commit, fingerprints of the analysis script and the renderer files |
| Environment | Versions of Python and the main packages |
| Build time | 2026-10-08 12:37 |

**A fingerprint (hash)** is a short string computed from a file's content. If even one byte of the content differs, it is a completely different value. Even when a file's name or date is the same, you know exactly whether its content changed.

The build keeps this record on its own, without any change to the analysis script. It writes down the files it actually saw being read, so a path written somewhere cannot differ from the file really read.

## What you do

💬 **Which figures are stale:** "Check whether any figures are stale." Each figure is reported as **fresh** or **stale**, with the reason, e.g. "data.csv changed", "3 config keys changed", "renderer file changed".

💬 **Find the figures that use a file:** "Find every figure that uses `raw_data/…/concordance.csv`." It finds them across projects.

💬 **See where one figure comes from:** "Trace the sources of Figure 3." It shows results ← run ← config ← code ← data ← (if recorded) the analysis tool that made the data.

💬 **What changed:** "Show what changed in Figure 3 since the last storyline snapshot." It lists the input files, config keys and numbers that changed. Useful when writing a response to reviewers.

Then build the stale figures again (💬 "rebuild all stale figures", or ⌨ check with `fa status`, then `fa build project-name`).

## Good to know

- **A file whose date alone changed is not stale.** If the content (the fingerprint) is the same, the figure is fresh. Copying or downloading a file again does not call for a redraw when its content is the same.
- **You can keep stale figures out of the storyline PDF.** Built in strict mode, it refuses to make the PDF when a figure is stale or has check errors, and tells you (chapter 11).
- **Provenance left by the analysis pipeline carries on.** If a bundle's note names the tool and version that made the data, they go into the figure's provenance record too. The chain of sources does not break at the bundle.

---
Previous: [9. Transparency in numbers, statistics and images](09-integrity.md) · Next: [11. Into the paper: a figure's life](11-lifecycle.md)
