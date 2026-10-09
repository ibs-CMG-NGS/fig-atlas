"""Tools around renderer schemas (roadmap Phase 2, steps 2.2-2.3).

``extract_defaults(path)`` reads a renderer module's source and lists every
parameter it reads -- ``params.get("key", default)`` and
``text_param(params, "key", default)`` -- with the default as written: the
literal value when it is one, else its source text (``title_sz``,
``a_sz * 0.8``). Used to draft schemas and, in the tests, to prove that a
schema's defaults are exactly the renderer's own (so adding a schema never
changes a figure).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

NO_DEFAULT = object()


@dataclass
class Read:
    key: str
    default: object          # literal value, NO_DEFAULT, or None
    source: str              # default as written
    literal: bool
    line: int


def extract_defaults(path: Path, params_name: str = "params") -> list[Read]:
    text = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(text)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        key_arg = default_arg = None
        if (isinstance(f, ast.Attribute) and f.attr in ("get", "setdefault") and isinstance(f.value, ast.Name)
                and f.value.id == params_name and node.args):
            key_arg = node.args[0]
            default_arg = node.args[1] if len(node.args) > 1 else None
        elif (isinstance(f, ast.Name) and f.id == "text_param" and len(node.args) >= 2
              and isinstance(node.args[0], ast.Name) and node.args[0].id == params_name):
            key_arg = node.args[1]
            default_arg = node.args[2] if len(node.args) > 2 else None
        if not (isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str)):
            continue
        if default_arg is None:
            out.append(Read(key_arg.value, None, "None", True, node.lineno))
            continue
        src = ast.get_source_segment(text, default_arg) or ""
        try:
            val, lit = ast.literal_eval(default_arg), True
        except ValueError:
            val, lit = NO_DEFAULT, False
        out.append(Read(key_arg.value, val, src, lit, node.lineno))
    return sorted(out, key=lambda r: (r.key, r.line))


def by_key(reads: list[Read]) -> dict[str, list[Read]]:
    out: dict[str, list[Read]] = {}
    for r in reads:
        out.setdefault(r.key, []).append(r)
    return out
