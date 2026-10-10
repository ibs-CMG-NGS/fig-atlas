"""Comment-preserving YAML edits (roadmap Phase 2, step 2.0).

Configs are the researchers' UI: their comments, order and layout must
survive any automated edit (AGENTS.md 1.6, "Zero Comment Stripping"), so tools
never write them with PyYAML. This module edits through ruamel.yaml and only
when that is lossless: a file is edited only if loading and dumping it
unchanged reproduces it byte for byte (under one of the indentation styles the
repository uses). Otherwise ``load`` raises ``NotRoundTrippable`` naming the
first line that would change, and the tool leaves the file alone.

    doc = yamledit.load(path)          # raises NotRoundTrippable
    doc.data["plots"]["volcano"]["lfc_min"] = 1.0
    doc.save()                         # same style, same line endings
"""
from __future__ import annotations

import difflib
import io
from dataclasses import dataclass
from pathlib import Path

# Sequence styles found in the repository's configs: "- item" at the parent
# key's column, or indented two more.
STYLES = (dict(mapping=2, sequence=2, offset=0), dict(mapping=2, sequence=4, offset=2))


class NotRoundTrippable(ValueError):
    pass


def _yaml(style: dict):
    from ruamel.yaml import YAML
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(**style)
    y.representer.add_representer(type(None), lambda r, d: r.represent_scalar("tag:yaml.org,2002:null", "null"))
    return y


def _dump(y, data) -> str:
    buf = io.StringIO()
    y.dump(data, buf)
    return buf.getvalue()


def round_trip_style(text: str) -> dict | None:
    """The style under which ``text`` round-trips unchanged, or None."""
    for style in STYLES:
        y = _yaml(style)
        if _dump(y, y.load(text)) == text:
            return style
    return None


@dataclass
class Document:
    path: Path
    data: object
    style: dict
    newline: str

    def text(self) -> str:
        return _dump(_yaml(self.style), self.data).replace("\n", self.newline)

    def save(self) -> None:
        self.path.write_bytes(self.text().encode("utf-8"))


def load(path: Path) -> Document:
    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    style = round_trip_style(text)
    if style is None:
        y = _yaml(STYLES[0])
        out = _dump(y, y.load(text))
        first = next((l for l in difflib.unified_diff(text.splitlines(), out.splitlines(), lineterm="", n=0)
                      if l[:1] == "-" and not l.startswith("---")), "")
        raise NotRoundTrippable(f"{path}: editing would reformat it (first change: {first[1:].strip()[:80]!r}); "
                                "left untouched -- e.g. remove trailing spaces or write multi-line [..] / {..} "
                                "as block lists")
    return Document(path, _yaml(style).load(text), style, newline)
