# Data request template (one form for every request)

Every request for data -- a new bundle, a corrected one, a missing column, a rerun -- starts from this
one form, whether a person writes it or an agent does. It is sent to whoever produces the data (an
analysis pipeline, a server, another package, a colleague) and kept in the repository as the record of
what was asked, what arrived and where it came from.

**How to use it**

1. Copy the block below into `docs/data_contracts/<name>_request.md`. The name must end in
   `_request.md`: that is how `fa storyline requests` and `fa storyline evidence` find it.
2. Fill in every section. A section that does not apply is kept with one line saying so ("None.");
   deleting it leaves the producer guessing whether it was forgotten.
3. Delete the `<!-- ... -->` guidance comments once filled in.
4. Point the producer to this file and to the [bundle contracts](README.md). Everything the bundle
   must look like is there; the request says only what this delivery is.
5. A follow-up on the same data is a new revision **in the same document** (`version: r1.1`, a new
   entry in section 8), not a new document. A different question gets a new document; when it replaces
   an old one, list the old one's name in that one's `superseded_by`.

---

````markdown
---
request: "<name>"          # the file name without _request.md
status: open               # open | partial | delivered | resolved | superseded
date: "YYYY-MM-DD"         # the day it was sent
version: "r1"              # r1, r1.1, r2 ... one per round with the producer (section 8)
delivered: []              # filled when data arrive: the raw_data/ files or folders that landed (globs allowed)
derived: []                # bundle files built here from the delivery, if any
superseded_by: []          # names of requests that replace this one
---

# Data request: <one line that says what is asked>

**Producer**: <who makes the data: pipeline, server, package, person>
**Consumer**: <project(s) and figure/panel that will read it, e.g. `kyg-paper-main-fig3-...`, panel b>
**Contract**: <bundle contract and plot_type for each bundle, e.g. `table_bundle_contract.md`, `line_band`; "new plot type" -> `new_plot_type_contract.md`>
**Priority**: <blocking | needed before <date> | when convenient>

## 0. Why

<!-- What the figure needs, what is missing or wrong now, and what was already ruled out.
     Quote the observation (a number, a file, a build message), not an impression. -->

## 1. Check first -- you may already have it

<!-- Files or results the producer may already hold that would answer this without new work.
     "None." if there is nothing to check. -->

## 2. What to deliver

<!-- One row per bundle. A bundle is one panel's data: inputs/data.csv + metadata/metadata.yaml.
     Folder names, column names and metadata fields follow the contract named above; write here only
     what is specific to this delivery. -->

| Bundle folder (under `raw_data/`) | plot_type | New or change | Columns / content |
|---|---|---|---|
| `<study>/<project>/<bundle>/` | `<plot_type>` | new / change of `<file>` | `<col_a>`, `<col_b>` (unit), ... |

Rules that apply to every bundle (from the contracts):

- Column names exactly as given, case included; order does not matter.
- Values as the analysis produced them: not rounded, not renamed, not shortened for display.
- Absent means no row: no placeholder rows filled with NaN.
- A change to a delivered bundle is a new version: say what changed and why in `metadata.yaml`
  `notes` and in section 8 below. Delivered files are not edited in place without saying so.

## 3. Where it came from (`upstream` in each bundle's metadata.yaml)

Each bundle's `metadata/metadata.yaml` states what it was made from (decision 0008). Fill in what you
know; a path without a hash is better than nothing.

```yaml
upstream:
  host: <machine or service where the bundle was made>
  produced_by: <script path @ commit, or tool and version>
  files:                          # the files the bundle was made from
    - path: <path on that machine>
      sha256: <sha256sum output>  # `sha256sum <file>` on Linux/macOS, `certutil -hashfile <file> SHA256` on Windows
      size: <bytes>
```

## 4. Validation

Before delivering:

- [ ] `fa bundle check raw_data/<...>/<bundle>` reports no error for each bundle
- [ ] every column of section 2 is present with exactly that name
- [ ] `upstream` is filled in each `metadata.yaml` (section 3)
- [ ] <checks specific to this request: expected row count, value range, a known value to match>

## 5. Not asked for

<!-- What this request deliberately leaves out, so it is not produced by mistake. "None." if nothing. -->

## 6. Questions for the producer

<!-- Decisions the producer has to make or confirm. Number them so answers can refer to them. -->

## 7. Delivery

**Destination**: `raw_data/<study>/<project>/` (one folder per bundle, as in section 2)
**Delivery notes**: <a short note beside the bundles, e.g. `raw_data/<study>/DELIVERY_NOTES_<name>.md`,
saying what was delivered and anything that differs from this request>

## 8. Revisions

<!-- One entry per round, newest last. The producer's answer goes here too. -->

### r1 (YYYY-MM-DD) -- request sent
````

---

**When the data arrive** (the person or agent who asked):

1. Run `fa bundle check` on each delivered bundle.
2. Fill `delivered` (and `derived` if bundles were built here) in the front matter and set `status`
   (`delivered`, or `partial` with what is missing in section 8).
3. `fa storyline requests` lists every request with its status and which published figures use it;
   `fa storyline evidence <slot|project>` shows the chain from a figure back to this request.
