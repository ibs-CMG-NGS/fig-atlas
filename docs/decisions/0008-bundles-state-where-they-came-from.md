# 0008. A bundle may state where it came from; fig-atlas carries that and does not check it

- Status: proposed
- Date: 2026-11-11

## Context

Every build records what a figure was made from: each input file with its path, size and sha256 (`figure_NN.provenance.json`), and, through the data requests, the delivery a file came in. That record **starts at the bundle**. What the bundle itself was made from -- the count table on the analysis server, the tracking output, the images, and the script that turned them into `inputs/data.csv` -- is not in it. From a bundle's metadata the record takes only `app_version`, `plot_type`, `figure_id` and the statistics tables.

This matters on the day a question is raised about a figure. Data behind papers are lost by ordinary events -- a laboratory moves, a person leaves, a disk fails -- and their availability falls quickly with a paper's age (Vines et al., *Curr. Biol.* 2014). A copy can still be made on the day it is needed. The knowledge of **which file on which machine, through which script, became this bundle** cannot: it exists when the bundle is made, in the head of whoever (or whatever agent) makes it, and nowhere else afterwards. Without it "the original cannot be found" is the end of the matter; with it, one knows what to look for, and with a hash one can prove that a file recovered from a backup is that original.

In the case study's repository, none of 270 bundle metadata files names an upstream file in a structured field. Some say a good deal in free-text `notes` (model, client version, reference genome): the will to write it down is there, a place for it is not.

A stronger design was considered and set aside: declaring storage locations and having `fa verify` require, by hash and with dated receipts, that every input of a published figure exists in at least N of them. It guards against the loss itself, but it only works while someone keeps running the checks, and a check that must pass for a figure to stay valid is a hurdle people route around when they do not feel the risk. Keeping data is also the laboratory's and the institution's responsibility, with tools made for it (rsync, git-annex or DataLad, an institutional store, a repository with a DOI), not a figure tool's.

## Decision

**A bundle's metadata may carry an `upstream` block that says where its data came from. It is optional. fig-atlas copies it into the figure's record and shows it; it does not open, hash or require the files it names.**

```yaml
upstream:
  host: analysis-server        # where the bundle was made (a name is enough)
  produced_by: scripts/make_qc_table.py @ a1b2c3d   # script and commit, or tool and version
  files:
    - path: /data/h2o2/atac/counts/peak_counts.tsv   # the path there
      sha256: 4f1c...          # when known
      size: 18234112           # bytes, when known
```

1. **Written by whoever makes the bundle, when it is made.** That is the only moment the information is at hand, and it costs a few lines. Every field is optional; a `files` entry with a path and no hash is better than no entry.
2. **The main path is the data request.** Most bundles are made on request, often by an agent that knows exactly which files it read and which script it ran, and can run `sha256sum` where the files are. The one request template, [`docs/contracts/data_request_template.md`](../contracts/data_request_template.md), asks for the `upstream` block in every bundle, so it is filled without relying on anyone's memory.
3. **A person making a bundle by hand gets help, not a rule.** The bundle metadata template carries the block, commented; a command fills `files` (path, hash, size) from the files one points it at, when they can be opened on that machine; `fa bundle check` and `fa ingest bundle` say in one line of information when a bundle states no upstream.
4. **fig-atlas carries and shows it.** The block goes into the input's `bundle` entry of the provenance record as written, and `fa storyline evidence` shows it in the chain: request, upstream files, bundle, figure. A summary line counts the published figures' bundles that state none.
5. **Nothing fails.** A missing or partial block is never an error or a warning, at build, verify or publish. Existing bundles are not filled in after the fact; the convention starts with new deliveries.

## Consequences

- The chain a figure's record promises reaches one step further back, to the files the bundle was made from, for every bundle that states them.
- **What it does not do.** It does not keep the files, check that they still exist, or check that the block is true. A stated upstream is a claim by whoever made the bundle, recorded as such. It does nothing about fabricated or mistaken data.
- **The price** is a few lines per delivery. For bundles made by hand some blocks will stay empty; that is accepted, because requiring them would bring back the hurdle this decision avoids.
- Server paths and host names end up in bundle metadata. `raw_data/` is outside version control, so they are not published with a repository; a bundle that is released needs a decision about that block (keep, or reduce to file names and hashes).
- Free-text `notes` stay as they are. Parameters of a run (model, versions, reference) belong there or in fields a contract defines; `upstream` is only about files and what produced the bundle from them.
- **What keeps the decision.** A test that a bundle with an `upstream` block has it in the provenance record unchanged, and one without builds, verifies and publishes with no finding; a test that no code path opens a path named in the block; the request template and the bundle template carrying the block.
- Left for later, each with its own record if taken up: a one-off comparison of a folder against a paper's list of inputs (useful at submission or before a move), and checks inside the data (the same run of values in different groups, the same image in two panels).
