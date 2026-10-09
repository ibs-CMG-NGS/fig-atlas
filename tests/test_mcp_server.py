"""fa mcp: the fa commands as MCP tools (roadmap 7.6)."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fig_atlas.cli import build_parser
from fig_atlas.mcp_server import SPECS, Server, argv_for, serve, tool_definitions

ROOT = Path(__file__).resolve().parents[1]
TASKS = ('{\n  "inputs": [\n    {\n      "id": "projectSelector",\n      "type": "pickString",\n'
         '      "options": [\n        "ALL"\n      ],\n      "default": "ALL"\n    }\n  ]\n}\n')


def _sample(prop: dict):
    if "enum" in prop:
        return prop["enum"][0]
    return {"boolean": True, "integer": 3, "number": 1.5, "array": ["a", "b"]}.get(prop["type"], "x")


@pytest.mark.parametrize("spec", SPECS, ids=[s.name for s in SPECS])
def test_every_tool_call_is_a_valid_fa_command(spec):
    """Each tool's arguments, all filled in, give a command line the CLI
    parser accepts: the tools and `fa --help` cannot drift apart."""
    tool = next(t for t in tool_definitions() if t["name"] == spec.name)
    args = {k: _sample(p) for k, p in tool["inputSchema"]["properties"].items() if k != "apply"}
    argv = argv_for(spec, args)
    ns = build_parser().parse_args(argv)
    assert ns.command == spec.command and ns.json
    for k, v in args.items():
        assert getattr(ns, k) == (v if not isinstance(v, (int, float)) or isinstance(v, bool)
                                  else type(getattr(ns, k))(v)), k


def test_change_tools_dry_run_unless_applied():
    spec = next(s for s in SPECS if s.name == "fa_retire")
    assert argv_for(spec, {"project": "p"})[-1] == "--dry-run"
    assert "--dry-run" not in argv_for(spec, {"project": "p", "apply": True})
    tools = {t["name"]: t for t in tool_definitions()}
    assert tools["fa_retire"]["annotations"]["destructiveHint"] is True
    assert tools["fa_list"]["annotations"]["readOnlyHint"] is True
    assert "apply" not in tools["fa_build"]["inputSchema"]["properties"]
    with pytest.raises(ValueError, match="unknown"):
        argv_for(spec, {"project": "p", "bogus": 1})
    with pytest.raises(ValueError, match="needs: project"):
        argv_for(spec, {})


def test_protocol_messages():
    s = Server(ROOT)
    init = s.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
    assert init["result"]["protocolVersion"] == "2025-06-18" and "tools" in init["result"]["capabilities"]
    future = s.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"protocolVersion": "2099-01-01"}})
    assert future["result"]["protocolVersion"] == "2025-11-25"          # our newest
    assert s.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert s.handle({"jsonrpc": "2.0", "id": 3, "method": "ping"})["result"] == {}
    assert s.handle({"jsonrpc": "2.0", "id": 4, "method": "bogus"})["error"]["code"] == -32601
    assert s.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                     "params": {"name": "no_such_tool"}})["error"]["code"] == -32602
    bad = s.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "fa_promote", "arguments": {}}})
    assert bad["result"]["isError"] and "needs" in bad["result"]["content"][0]["text"]
    out = io.BytesIO()
    serve(ROOT, io.BytesIO(b'not json\n\n{"jsonrpc":"2.0","id":7,"method":"ping"}\n'), out)
    lines = [json.loads(x) for x in out.getvalue().decode().splitlines()]
    assert lines[0]["error"]["code"] == -32700 and lines[1] == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_session_dry_run_then_apply(tmp_path):
    """A client over stdio: new project as a dry run (a diff, nothing written),
    then applied; the tool result is the command's JSON."""
    for d in ("configs", "fig_atlas", "scripts", ".vscode"):
        (tmp_path / d).mkdir()
    (tmp_path / "scripts" / "build_atlas.py").write_text("")
    (tmp_path / ".vscode" / "tasks.json").write_text(TASKS, encoding="utf-8")

    def call(i, name, args):
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}}
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            call(2, "fa_new_project", {"name": "demo-mcp"}),
            call(3, "fa_new_project", {"name": "demo-mcp", "apply": True}),
            call(4, "fa_list", {})]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
    res = subprocess.run([sys.executable, "-m", "fig_atlas", "--root", str(tmp_path), "mcp"],
                         input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True,
                         encoding="utf-8", cwd=tmp_path, env=env, timeout=300)
    assert res.returncode == 0, res.stderr
    replies = {r["id"]: r["result"] for r in map(json.loads, res.stdout.splitlines())}
    dry = json.loads(replies[2]["content"][0]["text"])
    assert dry["applied"] is False and any("+++ b/configs/config_demo-mcp.yaml" in c["diff"] for c in dry["changes"])
    assert "Dry run" in replies[2]["content"][1]["text"]
    applied = json.loads(replies[3]["content"][0]["text"])
    assert applied["applied"] is True and not replies[3]["isError"]
    assert (tmp_path / "configs" / "config_demo-mcp.yaml").is_file()
    assert [p["name"] for p in json.loads(replies[4]["content"][0]["text"])] == ["demo-mcp"]
