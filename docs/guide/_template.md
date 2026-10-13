---
title: How to write a new chapter (a template for authors)
audience: authors of the guide
reviewed: 2026-10-14
---

# How to write a new chapter

Copy this file to add a chapter to the guide (`docs/guide/`). It does not appear on the site.

## File and table of contents

1. The file name is `NN-short-english-name.md` (e.g. `07-results.md`). The number is the reading order. The English version (`NN-name.md`) is the source, and the Korean version (`NN-name.ko.md`) is written in the same commit (`tests/test_docs_i18n.py` compares their structure).
2. In the front matter at the top, write `title` (the chapter title), `audience` and `reviewed` (the date its content was last checked).
3. Add a line under `nav` → `Guide for researchers` in `mkdocs.yml` (with the English file name). The tests stop a chapter missing from the table of contents (`tests/test_guide.py`).
4. Pictures go in `docs/guide/img/`. A picture that can be made from example data is added to `scripts/make_guide_images.py`, so the script makes it again.

## Principles

- **The reader is a researcher.** It must read well without knowing programming or AI. Explain a technical term once where it first appears, and add it to the glossary if it is not there.
- **Plain Markdown only.** Use standard links (`[text](relative-path)`), tables, block quotes and code blocks only. No syntax specific to one tool (MkDocs syntax such as `!!! note`, wiki syntax such as `[[link]]`), so the page looks the same on GitHub and in any other documentation tool. Draw diagrams as `mermaid` code blocks, which both GitHub and the site draw.
- **Write only commands and paths that exist.** The tests check.

## The order of a chapter

<!-- i18n: prose -->
```markdown
# N. Chapter title

> **Has this ever happened to you?** One or two sentences of a scene from real lab life.

**The key idea:** the one sentence to remember from this chapter.

## What the tool does
What happens automatically. One picture or table.

## What you do
💬 **Ask an AI:** "say ...".
⌨ **Command:** one line (the full list in Appendix C).
💡 **Tip (if you use a particular editor):** only conveniences you can do without. The text must not depend on one editor.

## Good to know
Things to watch for, common mistakes.

---
Next: [N+1. Next chapter](NN-next.md)
```
