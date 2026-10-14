# 0006. The documentation is English, the source of truth, with a Korean version beside it

- Status: accepted
- Date: 2026-10-14

## Context

The documentation site (guide for researchers, tutorials, how-to guides, contracts, design decisions) was written in Korean, for the lab's members, and it was complete. Readers who come from the paper, a preprint or the Zenodo DOI read English. The Korean pages were good enough that dropping them would have been a loss. The generated reference pages (commands, Python functions, config keys, gallery) were English already.

## Decision

- **English is the site's language and the source of truth**, at `/`. **Korean is beside it**, at `/ko/`, one switch away on every page (`mkdocs-static-i18n`).
- A page's Korean version is `page.ko.md` next to `page.md`; both use the same pictures. The menu's titles are English, with their Korean in `nav_translations`.
- A change to a page is made to both versions in the same commit (AGENTS.md).
- Out of scope: Korean versions of the generated reference pages, and translations of `AGENTS.md` and the skill documents.
- The terms follow the manuscript's (bundle, renderer, config, figure spec, preflight, provenance record, live numbers, ...).

## Consequences

- A reader from the paper lands on English pages; the lab keeps its Korean pages.
- Two versions can drift apart. What keeps them together:
  - `tests/test_docs_i18n.py`: a Korean page needs its English page, with the same heading levels, code blocks (prose comments, diagrams and blocks marked `<!-- i18n: prose -->` aside), tutorial step markers, images, tables and link targets.
  - `tests/test_tutorials.py` runs the English tutorials; their steps are the same bytes in the Korean pages, so both promise the same result.
  - `docs/i18n_pending.txt` lists pages not yet in English (empty once the translation was done) and the test keeps it exact.
- Structure is checked, wording is not: whether the sentences say the same thing is left to review.
