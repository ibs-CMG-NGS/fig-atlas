# 0004. Procedures are deterministic commands; AI calls the same commands over MCP

- Status: accepted
- Date: 2026-10-08

## Context

Creating projects, ingesting bundles, promoting and retiring existed only as prose in CLAUDE.md and the agent skill documents. An AI read those documents and edited files directly to carry them out. So they were hard to do without AI, results could differ from AI to AI, and people found the results hard to verify. The user also works with Gemini CLI, Antigravity CLI and opencode besides Claude Code (gate G4).

## Decision

- Mechanical procedures become `fa` commands: `fa new project|renderer`, `fa ingest bundle`, `fa promote`, `fa retire`.
- Common conventions of the commands that change files:
  - `--dry-run`: shows only the files that would change and the diff.
  - `--json`: gives results for machines.
  - Idempotent: if the result is already there, nothing changes.
  - An unexpected file is not overwritten but reported as a conflict.
  - Moves are made with `git mv`.
  - A build checks the result afterwards.
- AI calls the same commands as **MCP tools** (`fa mcp`).
  - The tool definitions are generated from the CLI parser.
  - Without `apply: true` a changing tool is a dry run; the agent shows the diff to the user and applies it after they agree.
  - The server uses only the standard library (the official `mcp` package's API is changing fast at 2.x).
- Work that takes judgement is not made into commands: interpreting intent in Case C, writing the storyline, the reasons for a revision, reviewing figures.

## Consequences

- People, Claude Code and other agents produce the same results. The same task done with the CLI, opencode and Antigravity gave the same files, and the figures were identical byte for byte (2026-10-08, `docs/howto/ai_agents.md`).
- The skill documents shrink to "which command when + the points of judgement".
- What keeps it:
  - `tests/test_repo_commands.py`: idempotence, conflicts, full builds of the skeletons
  - `tests/test_mcp_server.py`: every tool call is a correct `fa` command
