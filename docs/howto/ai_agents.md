# How-to: connect fig-atlas to AI agents (`fa mcp`)

fig-atlas's procedures (new project, bringing in a bundle, building, checking, promoting, retiring) are all `fa` commands. People run the commands themselves; AI agents call the same commands as **MCP (Model Context Protocol) tools**. MCP is the common protocol for agents to call outside tools, so with one server many agents — Claude Code, Gemini CLI, opencode, Antigravity, Cursor, Codex and others — use the same tools.

```bash
fa mcp                     # or: python -m fig_atlas mcp [--root <repository>]
```

The agent starts this command as a child process and talks to it over standard input and output. Nothing more needs installing.

## 1. The tools

| Tool | What it does | Changes files? |
|---|---|---|
| `fa_list`, `fa_renderers`, `fa_bundle_contracts` | Lists projects, the figures that can be drawn, the bundle contracts | No |
| `fa_bundle_check` | Checks a bundle against its contract | No |
| `fa_status`, `fa_impact`, `fa_lineage` | Stale figures, what a file affects, where a figure came from | No |
| `fa_lint`, `fa_claims` | Config keys never read and typos, hand-typed numbers | No |
| `fa_build`, `fa_verify` | Building (with preflight) and verifying | Only `outputs/` |
| `fa_figure_images` | Returns the built figures and preflight overlays as images | No |
| `fa_new_project`, `fa_new_renderer`, `fa_ingest_bundle`, `fa_promote`, `fa_retire` | Creating projects and renderers, bringing in bundles, promoting, retiring | **Yes** (section 2) |

The tools' names, arguments and descriptions are generated from the `fa` commands' help, so they cannot drift from the CLI (`tests/test_mcp_server.py` checks that every tool call becomes a correct `fa` command). The result is each command's `--json` output.

## 2. Safeguards on the tools that change files

- Without `apply`, a call is a **dry run**: nothing is written; it returns the files that would change and the diff.
- The agent shows that diff to the user and calls again with `apply: true` only after the user agrees.
- These tools are marked "destructive" in MCP, so most agents ask the user for approval before running them.
- The commands' own rules hold too: if the result is already there, nothing changes (idempotent), and an unexpected file is not overwritten but reported as a conflict.

## 3. Settings per agent

In the examples below, `<python>` is the Python with fig-atlas installed. For a conda environment it is the python in the `fig-atlas` environment folder that `conda env list` shows (e.g. on Windows `C:\Users\<user>\miniconda3\envs\fig-atlas\python.exe`; in a shell with the environment on, `python -c "import sys; print(sys.executable)"` prints it too). If `fa` is on the PATH, `fa` can replace `<python> -m fig_atlas`. The server puts the DLL folder of a Windows conda environment (`Library/bin`) into its child processes, so that needs no setting. If you start the agent outside the repository, add `--root <repository path>` before `mcp`.

**opencode** (tested, 2026-10-08) — the repository's `opencode.json`, or the file `OPENCODE_CONFIG` points to:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "fig-atlas": {
      "type": "local",
      "command": ["<python>", "-m", "fig_atlas", "mcp"],
      "enabled": true
    }
  }
}
```

**Antigravity CLI** (tested, 2026-10-08):

```bash
agy mcp add fig-atlas -- <python> -m fig_atlas mcp
```

**Claude Code** (tested, 2026-10-13 — with an `--mcp-config` file):

```bash
claude mcp add fig-atlas -- <python> -m fig_atlas mcp
```

**Gemini CLI** — `~/.gemini/settings.json` or the repository's `.gemini/settings.json`:

```json
{ "mcpServers": { "fig-atlas": { "command": "<python>", "args": ["-m", "fig_atlas", "mcp"] } } }
```

**Cursor** — `.cursor/mcp.json`: the same `mcpServers` format as Gemini CLI.

**Codex CLI** — `~/.codex/config.toml` (Windows: `C:\Users\<user>\.codex\config.toml`; create it if missing):

```toml
# Connects the fig-atlas tools to Codex.
[mcp_servers.fig-atlas]
# The Python with fig-atlas installed. Write Windows paths with forward slashes (/) or in single quotes
# (inside double quotes, \ is a special character in TOML).
command = 'C:\Users\<user>\miniconda3\envs\fig-atlas\python.exe'
args = ["-m", "fig_atlas", "mcp"]
# A build (fa_build) can take more than a minute depending on the figure. Raise the longest time (seconds) one tool may take.
tool_timeout_sec = 600
```

Codex reads the repository's `AGENTS.md` on its own, so the rules file needs no separate connection. Start `codex` in the repository folder, check with `/mcp` that `fig-atlas` is listed, and try "show me the project list with the fig-atlas tools" (section 4). This setting follows the format of Codex's documentation and has not yet been run in this repository (to be confirmed in the usability test).

Entries without "tested" follow the format of each agent's documentation and have not been run in this repository.

## 4. Checking the connection

Ask the agent "show me the project list with the fig-atlas tools", and `fa_list` should be called. Also check that the agent's MCP list command (`opencode mcp list`, `agy mcp list`, `claude mcp list`, ...) shows `fig-atlas` as connected.

## 5. The rules agents follow

On connecting, the server sends a short note pointing to the detailed rules in the repository's [`AGENTS.md`](../../AGENTS.md) (raw data are read only; every visual value is in a commented config). Work that takes judgement — interpreting a figure's intent from a mockup (Case C), writing the storyline, writing the reasons for a revision — is not done by the commands. That part belongs to the agent and the person.

## 6. Cross-agent test (2026-10-08)

The same task (a new exploratory project → bundle check → bringing it in → building with preflight → looking at the figure → promoting it to paper Figure 1) was done three ways.

- (a) by a person with `fa` commands
- (b) by opencode with MCP tools only (shell and file editing tools off)
- (c) by Antigravity CLI with MCP tools only

The config, analysis script, figure spec and `.vscode/tasks.json` of the three results were all the same, and the built PDF and PNG were identical byte for byte. In opencode's call log, every step that changes files came first as a dry run, then with `apply: true`. Both agents read the Venn numbers (A only 18, B only 15, shared 12) from the figure returned by `fa_figure_images`.

On 2026-10-13 the same task was done again with Claude Code (claude-sonnet-5). Shell and file tools were off (`--strict-mcp-config --disallowedTools ...`), only MCP tools were used, and nothing was approved in advance in the prompt. At each of the three changing steps the agent showed the dry-run result and asked the person, and called again with `apply: true` only after the person approved. Compared with a person's (CLI) run with that day's code, all six files were identical byte for byte.
