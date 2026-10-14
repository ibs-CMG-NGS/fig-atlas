# Design decisions (ADR)

This folder records fig-atlas's main design decisions and their reasons. The rules themselves are in [`AGENTS.md`](../../AGENTS.md); here is **why each rule is so**. Decisions that lived only in conversations or a personal AI memory are moved into the repository, so other people and other agents see the same reasons.

| # | Decision | Status |
|---|---|---|
| [0001](0001-final-size-rendering.md) | Figures are drawn 1:1 at their final printed size (an A4 page preset) | Accepted (2026-09-30) |
| [0002](0002-config-holds-the-full-block.md) | The project config is the source of truth: every parameter a renderer reads, with comments | Accepted (2026-08), review gate G0 |
| [0003](0003-renderers-are-shapes.md) | Renderers are shapes, in the core; a field's knowledge goes into packs | Accepted (2026-10-07) |
| [0004](0004-procedures-are-commands.md) | Procedures are deterministic commands; AI calls the same commands over MCP | Accepted (2026-10-08) |
| [0005](0005-agents-md-single-source.md) | The single source of the rules is the root `AGENTS.md` | Accepted (2026-10-08) |
| [0006](0006-documentation-in-two-languages.md) | The documentation is English, the source of truth, with a Korean version beside it | Accepted (2026-10-14) |

## Writing a new decision

Create `NNNN-short-name.md` with the next number (and its Korean version, `NNNN-short-name.ko.md`), in the form below. When a decision changes, the old record is not deleted; its status becomes "superseded (→ NNNN)".

<!-- i18n: prose -->
```markdown
# NNNN. The decision in one line

- Status: accepted | proposed | superseded (→ NNNN)
- Date: YYYY-MM-DD

## Context
What was the problem; which facts forced the decision.

## Decision
What was decided.

## Consequences
What gets better, the price, and what keeps the decision (tests, commands, checks).
```
