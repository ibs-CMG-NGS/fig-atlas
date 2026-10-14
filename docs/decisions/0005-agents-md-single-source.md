# 0005. The single source of the rules is the root `AGENTS.md`

- Status: accepted
- Date: 2026-10-08

## Context

The same rules existed twice, in `CLAUDE.md` and in `.agents/AGENTS.md` (differing only by two blank lines). Every change to a rule had to be made in two places. Both files pointed to an example already deleted (`configs/config_pilot-test.yaml`) and to an old name (`config_paper_main.yaml`), and nothing checked them. And each agent reads a different file.

| Agent | Reads |
|---|---|
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` by default |
| Codex, opencode, Cursor, Copilot and others | the root `AGENTS.md` (the [agents.md](https://agents.md/) convention) |
| Antigravity CLI | both `.agents/AGENTS.md` and the root `AGENTS.md` (checked 2026-10-08) |

## Decision

- The rules are in one place, `AGENTS.md` at the repository root. People read this file as the rules document too.
- `CLAUDE.md` only imports it with `@AGENTS.md`.
- `context.fileName` in `.gemini/settings.json` makes Gemini CLI read `AGENTS.md`.
- The skill documents (`.agents/skills/*/SKILL.md`) hold only procedures and points of judgement, and point to `AGENTS.md` for the rules.
- The reasons for the rules are in this folder (the ADRs).
- Design decisions that were in a personal AI memory (0001, 0002) were moved here. Notes on research content (experimental design, target selection criteria) belong in the storyline and data request documents.

## Consequences

- Changing a rule once shows every agent and every person the same rule.
- `tests/test_agent_docs.py`, which keeps it, checks:
  - that `CLAUDE.md` only imports `AGENTS.md`
  - that the repository paths and `fa` commands named in `AGENTS.md` and the skill documents exist
  - that the Gemini settings point to `AGENTS.md`
- Some "CLAUDE.md §x" references in code comments and analysis scripts were left as they are: changing a file that makes figures changes its content hash and would mark those figures "stale". Since `CLAUDE.md` imports `AGENTS.md`, those references reach the same rules.
