# 0008. A published figure's inputs are checked to be kept in more than one place; fig-atlas does not keep them

- Status: proposed
- Date: 2026-11-11

## Context

Every build records what a figure was made from: each input file with its path, size and sha256 (`figure_NN.provenance.json`), the source data and the test tables beside the figure, and, through the data requests, the delivery a file came in. `fa verify` fails when an input no longer matches its recorded hash.

A hash is a fingerprint, not a copy. It proves that a file is the one the figure was built from **while the file exists**; when the file is gone, the record points at nothing. Three facts make that a real risk rather than a theoretical one:

- **Inputs are outside version control.** `raw_data/` is ignored by git (it is large and often unpublished), so the inputs of a repository's figures usually exist wherever the person who built them keeps them -- often one computer.
- **The record starts at the bundle.** What came before it (the instrument's files, tracking output, images, sequencing reads) may be named in the bundle's metadata, but nothing checks it.
- **Data are lost by ordinary events**, not by intent: a laboratory moves, a person leaves, a disk fails. The availability of the data behind a paper falls quickly with its age (Vines et al., *Curr. Biol.* 2014), and when a question is raised about a published figure years later, a concern that cannot be checked against the original files cannot be resolved either way.

A laboratory's data sit in places of different kinds -- the computer the figures are built on, an analysis server reached over ssh, a NAS that is mounted some of the time -- and fig-atlas cannot reach all of them from one process, or from CI.

## Decision

**fig-atlas checks that the inputs of published figures are kept; it does not keep them.** Copying, syncing and long-term storage belong to the tools and services made for them (rsync, git-annex or DataLad, an institutional store, a repository with a DOI). fig-atlas adds the missing link between its records and those places: for each input, by hash, *where is it, and when was that last confirmed?*

The commands are `fa copies ...` (not "archive": `<domain>/archive/` already means retired projects).

1. **A manifest of what must be kept.** `fa copies manifest` collects, from the provenance records of the published figures, every input once: sha256, size, repository path, the figures that read it and the data request it came with. A file is identified by its hash, not its path, so a copy counts wherever it lies and whatever it is called.

2. **Locations are declared by name; their addresses stay on the machine.** The repository config lists the locations and the rule:

   ```yaml
   copies:
     min_copies: 2          # each input must be confirmed in at least this many locations
     min_sites: 1           # ... in at least this many different sites (2 = one copy outside the lab)
     max_age_days: 180      # a confirmation older than this no longer counts
     locations:
       workstation: {site: lab}
       nas:         {site: lab}
       server:      {site: institute}
   ```

   Where a name points -- a folder, a mount point, `user@host:/path` -- is written in a file that is not committed (`.fa_local.yaml`), because it differs on every machine and should not be published with the repository. Two kinds of address cover the places above: a **path** (this computer, an external disk, a mounted NAS: anything the operating system can open) and **ssh** (a server).

3. **A check runs where the files are, and leaves a receipt.** `fa copies check <location>` looks for each file of the manifest at the location -- at the same relative path first, then by size and hash anywhere under it -- and writes a receipt: location, date, host, and for each hash whether it was found. For a path it hashes the files directly; for ssh it runs the system's `sha256sum` on the server, so the server needs no fig-atlas. The receipt is a small file committed to the repository (`docs/copies/<location>.json`), with no absolute paths in it.

   Receipts are what make the three kinds of place equal. A NAS that is not mounted today, or a server CI cannot reach, is still accounted for by its last receipt and that receipt's age.

4. **`fa verify` and publish read the receipts.** For every input of a published figure, the number of locations with a receipt that found it, within `max_age_days`, must reach `min_copies` and `min_sites`. For a paper project a shortfall is an error at publish; elsewhere it is a warning. `fa copies status` lists the inputs that fall short and the locations whose receipts are getting old. A repository that declares no `copies:` block gets one line of information and nothing else changes.

5. **Upstream originals join the same list (second step).** A bundle's metadata may declare the files it was derived from (`upstream.files`: name, sha256, size). They enter the manifest marked `upstream` and are checked the same way. A published bundle that declares none is reported, not failed: most existing bundles have none yet.

Not part of this decision: looking **inside** the data for signs of trouble (the same run of values in different groups, the same image in two panels). That is a data check in the sense that preflight is a layout check, and gets its own record.

## Consequences

- The chain a figure's record promises -- data request, delivered file, bundle, figure -- gets its last link: the file's hash is tied to places and dates, so "can this figure still be traced to its data?" has an answer that a command computes.
- The loss this guards against is the ordinary one: all copies in one place, or nobody noticing that a copy went away. With `min_sites: 2`, a laboratory move cannot take every copy.
- **What it does not do.** It does not prevent fabrication or error in the data, and it does not store anything. A receipt says a file was at a location on a date; it is as good as the declaration of that location and the person who ran the check. `site` is declared, not detected: two "sites" on one disk are a wrong declaration that no command can see.
- **The price.** Someone has to run the checks, on each location, often enough that receipts stay within `max_age_days`. Hashing some gigabytes over ssh takes minutes; results are cached by size and modification time at the location. The upstream step asks every delivery to list its original files, which is work for whoever delivers.
- **What keeps the decision.** Tests on temporary folders standing in for locations (a file found at another path, a file changed, a receipt too old, a site short); a test that `fa copies` never writes to a location; `fa verify` in CI, which needs only the committed receipts. The storage tools stay replaceable: a location filled by rsync, by git-annex or by hand is checked the same way.
- Open before acceptance: the defaults (`min_copies: 2`, `max_age_days: 180`); whether the working copy must itself be a declared location; whether a deposit with a DOI becomes a third kind of address, confirmed by its published checksums.
