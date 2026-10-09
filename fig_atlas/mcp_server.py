"""`fa mcp`: the fa commands as tools for any AI agent (roadmap 7.6).

A Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0),
with no dependency beyond the standard library. Claude Code, Gemini CLI,
opencode, Antigravity, Cursor, Codex and other MCP clients start it as::

    fa mcp                      # or: python -m fig_atlas mcp [--root <repo>]

Each tool runs one ``fa ... --json`` command in a child process (so nothing a
build prints can corrupt the protocol stream) and returns its JSON. The tool
list and argument schemas are generated from the CLI's own parser, so the
tools and ``fa --help`` cannot drift apart. Commands that change files never
write unless called with ``apply: true``: without it they return the planned
diff (``--dry-run``), which the agent shows the user first. ``fa_figure_images``
returns the built figures (and preflight overlays) as images so the agent can
look at them.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = (
    "fig-atlas manages publication figures as config-driven projects. Read AGENTS.md in the repository for the "
    "rules (raw data is read-only; every visual value lives in the project config with comments). Typical flow: "
    "fa_new_project -> fa_bundle_check -> fa_ingest_bundle -> fa_build (preflight) -> fa_figure_images -> "
    "fa_verify; fa_promote / fa_retire move projects through the paper lifecycle. Tools that change files "
    "return a dry-run diff unless apply is true: show the diff to the user and apply only with their consent.")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    command: str                       # fa subcommand
    fixed: tuple[str, ...] = ()        # leading positional values (e.g. "project" for fa new)
    kind: str = "read"                 # read | build | change
    exclude: tuple[str, ...] = ()      # parser dests not offered as arguments
    description: str = ""              # replaces the subcommand's help
    timeout: int = 600                 # seconds


ALWAYS_EXCLUDED = ("help", "json", "dry_run", "root", "command")

SPECS = (
    ToolSpec("fa_list", "list", description="List the projects (name, namespace, config)."),
    ToolSpec("fa_renderers", "renderers",
             description="Plot names a plots: block or fig_atlas.render() can draw: core, packs and recipes."),
    ToolSpec("fa_bundle_check", "bundle", ("check",),
             description="Check data bundles against the contract of their plot_type: structure, required "
                         "columns, the renderer that draws them. Run before fa_ingest_bundle."),
    ToolSpec("fa_bundle_contracts", "bundle", ("contracts",), exclude=("paths", "all", "verbose"),
             description="The bundle contracts and plot types the installed renderers draw."),
    ToolSpec("fa_status", "status", exclude=("check",)),
    ToolSpec("fa_impact", "impact"),
    ToolSpec("fa_lineage", "lineage"),
    ToolSpec("fa_lint", "lint", exclude=("write", "check")),
    ToolSpec("fa_claims", "claims", exclude=("write", "check")),
    ToolSpec("fa_build", "build", kind="build", timeout=3600,
             description="Build projects (analysis -> publish -> verify); preflight adds the print checks "
                         "(overlaps, clipping, sizes, fonts). Writes only under outputs/."),
    ToolSpec("fa_verify", "verify", kind="build"),
    ToolSpec("fa_new_project", "new", ("project",), kind="change", exclude=("package", "plot_type", "doc"),
             description="Create a project: commented config, analysis-script skeleton, figure spec, build-list "
                         "entry. Flat sandbox without domain/category."),
    ToolSpec("fa_new_renderer", "new", ("renderer",), kind="change",
             exclude=("domain", "category", "raw_root", "slug"),
             description="Create a renderer skeleton with its SCHEMA, test and package export; plot_type makes "
                         "fa_ingest_bundle use it. Renderers are shapes: core by default."),
    ToolSpec("fa_ingest_bundle", "ingest", ("bundle",), kind="change", timeout=3600,
             description="Add a data bundle to a project: check it, write its full commented plots block to the "
                         "config, then build. The values are a starting point: check the build with preflight."),
    ToolSpec("fa_promote", "promote", kind="change", timeout=3600),
    ToolSpec("fa_retire", "retire", kind="change", timeout=3600),
)

APPLY = {"type": "boolean", "default": False,
         "description": "false (default): return the planned changes as a diff and write nothing. true: apply "
                        "them -- only after the user has seen the dry run and agreed."}


# ------------------------------------------------------------ tool schemas --
def _subparsers() -> tuple[dict[str, argparse.ArgumentParser], dict[str, str]]:
    from .cli import build_parser
    sub = next(a for a in build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    return dict(sub.choices), {a.dest: a.help for a in sub._choices_actions}


def _arguments(parser: argparse.ArgumentParser, spec: ToolSpec) -> list[argparse.Action]:
    out, fixed = [], len(spec.fixed)
    for a in parser._actions:
        if a.dest in ALWAYS_EXCLUDED or a.dest in spec.exclude or isinstance(a, argparse._HelpAction):
            continue
        if not a.option_strings and fixed:          # a positional filled by spec.fixed
            fixed -= 1
            continue
        out.append(a)
    return out


def _property(a: argparse.Action) -> dict:
    if isinstance(a, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        prop = {"type": "boolean"}
    elif a.nargs in ("*", "+"):
        prop = {"type": "array", "items": {"type": "string"}}
    elif a.type is int:
        prop = {"type": "integer"}
    elif a.type is float:
        prop = {"type": "number"}
    else:
        prop = {"type": "string"}
    if a.choices and prop["type"] == "string":
        prop["enum"] = list(a.choices)
    if a.help and a.help is not argparse.SUPPRESS:
        prop["description"] = a.help
    if a.default not in (None, False, argparse.SUPPRESS) and not isinstance(a.default, list):
        prop["default"] = a.default
    return prop


def _required(a: argparse.Action) -> bool:
    return (not a.option_strings and a.nargs not in ("*", "?")) or bool(getattr(a, "required", False))


def tool_definitions() -> list[dict]:
    parsers, helps = _subparsers()
    tools = []
    for spec in SPECS:
        actions = _arguments(parsers[spec.command], spec)
        props = {a.dest: _property(a) for a in actions}
        if spec.kind == "change":
            props["apply"] = APPLY
        tools.append({
            "name": spec.name,
            "description": spec.description or (helps.get(spec.command) or spec.command),
            "inputSchema": {"type": "object", "properties": props,
                            "required": [a.dest for a in actions if _required(a)], "additionalProperties": False},
            "annotations": {"readOnlyHint": spec.kind == "read", "destructiveHint": spec.kind == "change",
                            "idempotentHint": True, "openWorldHint": False},
        })
    tools.append({
        "name": "fa_figure_images",
        "description": "The built figure PNGs of a project (and its preflight overlays, if any) as images, to "
                       "look at a figure after fa_build. Build first.",
        "inputSchema": {"type": "object", "properties": {
            "project": {"type": "string", "description": "project name"},
            "max_images": {"type": "integer", "default": 4, "description": "at most this many images"},
            "max_pixels": {"type": "integer", "default": 1600,
                           "description": "longest side of each returned image, in pixels (downscaled copies)"}},
            "required": ["project"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
                        "openWorldHint": False},
    })
    return tools


def argv_for(spec: ToolSpec, args: dict) -> list[str]:
    """The fa command line for a tool call (always --json)."""
    parsers, _ = _subparsers()
    actions = {a.dest: a for a in _arguments(parsers[spec.command], spec)}
    unknown = set(args) - set(actions) - ({"apply"} if spec.kind == "change" else set())
    if unknown:
        raise ValueError(f"unknown argument(s) for {spec.name}: {', '.join(sorted(unknown))}")
    missing = [d for d, a in actions.items() if _required(a) and args.get(d) in (None, "", [])]
    if missing:
        raise ValueError(f"{spec.name} needs: {', '.join(missing)}")
    positional, options = [], []
    for dest, a in actions.items():
        v = args.get(dest)
        if v is None or v is False or v == []:
            continue
        values = [str(x) for x in v] if isinstance(v, list) else [] if v is True else [str(v)]
        if not a.option_strings:
            positional += values
        else:
            flag = max(a.option_strings, key=len)
            options += [flag, *values] if values or v is True else []
    argv = [spec.command, *spec.fixed, *positional, *options, "--json"]
    if spec.kind == "change" and not args.get("apply"):
        argv.append("--dry-run")
    return argv


# ------------------------------------------------------------- tool calls --
def _env() -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    dll = Path(sys.prefix) / "Library" / "bin"        # conda on Windows: matplotlib's DLLs
    if dll.is_dir() and str(dll) not in env.get("PATH", ""):
        env["PATH"] = str(dll) + os.pathsep + env.get("PATH", "")
    return env


def run_fa(root: Path, argv: list[str], timeout: int) -> tuple[int, str, str]:
    try:
        res = subprocess.run([sys.executable, "-m", "fig_atlas", "--root", str(root), *argv], cwd=root,
                             env=_env(), capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=timeout, stdin=subprocess.DEVNULL)
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"fa {' '.join(argv)} did not finish within {timeout} s"


def _text(s: str) -> dict:
    return {"type": "text", "text": s}


def call_tool(root: Path, name: str, args: dict) -> dict:
    if name == "fa_figure_images":
        return figure_images(root, **args)
    spec = next((s for s in SPECS if s.name == name), None)
    if spec is None:
        raise KeyError(name)
    try:
        argv = argv_for(spec, args or {})
    except ValueError as exc:
        return {"content": [_text(str(exc))], "isError": True}
    rc, out, err = run_fa(root, argv, spec.timeout)
    content = [_text(out.strip() or "(no output)")]
    if rc != 0 and err.strip():
        content.append(_text("stderr:\n" + err.strip()[-4000:]))
    if spec.kind == "change" and not args.get("apply") and rc == 0:
        content.append(_text("Dry run: nothing was written. Show these changes to the user; call again with "
                             "apply: true only if they agree."))
    return {"content": content, "isError": rc != 0}


def _png_paths(root: Path, project: str) -> list[Path]:
    rc, out, _ = run_fa(root, ["verify", project, "--json"], 300)
    paths = []
    try:
        rows = json.loads(out).get("rows", [])
    except (json.JSONDecodeError, AttributeError):
        rows = []
    for r in rows:
        if r.get("kind") == "figure_file" and str(r.get("path", "")).lower().endswith(".png"):
            p = root / str(r["path"]).replace("\\", "/")
            if p.is_file():
                paths.append(p)
    overlay = root / "outputs" / "preflight" / project
    paths += sorted(overlay.glob("*.png")) if overlay.is_dir() else []
    return paths


def figure_images(root: Path, project: str, max_images: int = 4, max_pixels: int = 1600) -> dict:
    from PIL import Image
    paths = _png_paths(root, project)
    if not paths:
        return {"content": [_text(f"no built PNG figures for {project!r}; run fa_build first")], "isError": True}
    content = [_text("\n".join(p.relative_to(root).as_posix() for p in paths[:max_images]))]
    for p in paths[:max_images]:
        with Image.open(p) as im:
            im = im.convert("RGB") if im.mode not in ("RGB", "RGBA") else im.copy()
            im.thumbnail((max_pixels, max_pixels))
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
        content.append({"type": "image", "mimeType": "image/png", "data": base64.b64encode(buf.getvalue()).decode()})
    if len(paths) > max_images:
        content.append(_text(f"{len(paths) - max_images} more image(s); raise max_images to see them"))
    return {"content": content, "isError": False}


# ---------------------------------------------------------------- protocol --
@dataclass
class Server:
    root: Path
    tools: list[dict] = field(default_factory=list)

    def handle(self, msg: dict) -> dict | None:
        """One JSON-RPC message in; the response (None for a notification)."""
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:                                   # notification (initialized, cancelled, ...)
            return None
        try:
            if method == "initialize":
                asked = (msg.get("params") or {}).get("protocolVersion")
                version = _version()
                result = {"protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
                          "capabilities": {"tools": {"listChanged": False}},
                          "serverInfo": {"name": "fig-atlas", "version": version},
                          "instructions": INSTRUCTIONS}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                self.tools = self.tools or tool_definitions()
                result = {"tools": self.tools}
            elif method == "tools/call":
                p = msg.get("params") or {}
                try:
                    result = call_tool(self.root, p.get("name", ""), p.get("arguments") or {})
                except KeyError:
                    return _error(mid, -32602, f"unknown tool {p.get('name')!r}")
                except TypeError as exc:                  # bad arguments to fa_figure_images
                    result = {"content": [_text(str(exc))], "isError": True}
            elif method in ("resources/list", "prompts/list"):
                result = {method.split("/")[0]: []}
            else:
                return _error(mid, -32601, f"method not found: {method}")
        except Exception as exc:                          # noqa: BLE001 -- reported to the client
            return _error(mid, -32603, f"{type(exc).__name__}: {exc}")
        return {"jsonrpc": "2.0", "id": mid, "result": result}


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("fig-atlas")
    except PackageNotFoundError:
        return "0+unknown"


def _error(mid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def serve(root: Path, stdin=None, stdout=None) -> int:
    """Read requests line by line until stdin closes."""
    stdin = stdin or sys.stdin.buffer
    stdout = stdout or sys.stdout.buffer
    server = Server(root)
    for raw in stdin:
        if not raw.strip():
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            reply = _error(None, -32700, "parse error")
        else:
            if isinstance(msg, list):                     # a batch (older protocol versions)
                replies = [r for r in (server.handle(m) for m in msg) if r is not None]
                reply = replies or None
            else:
                reply = server.handle(msg)
        if reply is not None:
            stdout.write((json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8"))
            stdout.flush()
    return 0
