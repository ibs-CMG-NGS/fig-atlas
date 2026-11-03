"""What the layouts are, read from their docstrings (``fa layouts``, the
``fa_layouts`` MCP tool).

Each layout module's docstring is its documentation: a one-line summary, the
shape drawn in ASCII, how to use it, and its config keys. ``catalog`` reads
them into plain data, so the command line, the MCP tool and the reference page
describe the same thing. Nothing here imports matplotlib.
"""
from __future__ import annotations

import inspect
import re
import sys

EXAMPLES = "examples/layouts"              # in the fig-atlas source repository
PAGE = "docs/reference/layouts.md"


def _md(text: str) -> str:
    return text.replace("``", "`")


def _parse(doc: str) -> dict:
    """Summary, ASCII shape, usage paragraphs and config bullets of one layout docstring."""
    lines = doc.strip("\n").splitlines()
    drawn = [i for i, ln in enumerate(lines) if ln.startswith("    ") and ln.strip()[:1] in "+|"]
    shape = [lines[i][4:] for i in drawn]
    rest = "\n".join(lines[(drawn[-1] + 1) if drawn else 1:])
    usage_text, _, config_text = rest.partition("Config (``figures:``)")
    config, current = [], None
    for ln in config_text.splitlines()[1:]:
        if ln.startswith("- "):
            current = ln[2:].strip()
            config.append(current)
        elif ln.startswith("  ") and current is not None and ln.strip():
            config[-1] = config[-1] + " " + ln.strip()
        elif not ln.strip() and config:
            current = None
    keys = [sorted(set(re.findall(r"``([a-z_.]+)``", item.split(" -- ")[0]))) for item in config]
    return {
        "summary": _md(lines[0]),
        "shape": "\n".join(shape),
        "usage": _md(re.sub(r"\n(?!\n)", " ", usage_text.strip())).replace("\n ", "\n"),
        "config": [{"keys": k, "text": _md(item)} for k, item in zip(keys, config)],
    }


def catalog() -> dict:
    """Every public layout, and how layouts nest.

    ``layouts``: one entry per layout -- name, call signature, summary, ASCII
    shape, usage, config keys (``figures:``), the example folder and the
    reference page. ``composition``: the rules for a layout inside a cell of
    another. ``fixed_size``: a panel kept at its printed size.
    """
    from .. import layouts
    from . import _core

    entries = []
    for name in layouts.LAYOUTS:
        fn = getattr(layouts, name)
        info = _parse(sys.modules[fn.__module__].__doc__ or "")
        entries.append({"name": name, "call": f"layouts.{name}{inspect.signature(fn)}", **info,
                        "example": f"{EXAMPLES}/{name}/", "page": f"{PAGE}#{name}"})
    rules = _core.__doc__.split("Composition:", 1)[1].strip().split("\n\n")
    lead = " ".join(rules[0].split()).rstrip(":")              # the sentence that introduces the example
    fixed = " ".join(_core.__doc__.split("Fixed size:", 1)[1].split("Composition:", 1)[0].split())
    return {
        "layouts": entries,
        "composition": {
            "summary": _md(lead[:1].upper() + lead[1:]) + ".",
            "example": "\n".join(ln[4:] for ln in rules[1].splitlines()),
            "rules": _md(" ".join(rules[-1].split())),
            "max_depth": _core.MAX_DEPTH,
            "values": "figures.cells.<letter>",
            "page": f"{PAGE}#composition",
        },
        "fixed_size": {
            "summary": _md(fixed),
            "values": "figures.cells.<letter>.size_mm, or layouts.mm_axes(cell, left, top, width, height)",
            "page": f"{PAGE}#fixed-size",
        },
        "finish": "layouts.finish(fig, layout, fcfg) -- once, on the outermost layout, after drawing",
    }
