"""Planned file changes for the `fa` commands that edit the repository
(roadmap Phase 7: fa new project, fa retire, fa promote, ...).

A command first builds a ChangeSet -- files to create, move, edit -- from the
repository as it is, then either shows it (``--dry-run``: a unified diff per
file) or applies it. Plans are idempotent: running a command whose result is
already in place plans nothing. A planned create over a different existing
file is a conflict, reported instead of overwritten. Moves inside a git
repository use ``git mv`` so history follows the file.
"""
from __future__ import annotations

import difflib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class ChangeConflict(Exception):
    """The plan would overwrite something it did not expect."""


@dataclass
class Change:
    kind: str                      # create | move | edit
    path: str                      # repository-relative (source, for a move)
    new_path: str | None = None    # move destination
    old_text: str | None = None    # current content (None for create)
    new_text: str | None = None    # content after the change (None: unchanged on a move)

    def diff(self) -> str:
        a = (self.old_text or "").splitlines(keepends=True)
        b = (self.new_text if self.new_text is not None else self.old_text or "").splitlines(keepends=True)
        src = "/dev/null" if self.kind == "create" else f"a/{self.path}"
        dst = f"b/{self.new_path or self.path}"
        head = f"rename {self.path} -> {self.new_path}\n" if self.kind == "move" else ""
        return head + "".join(difflib.unified_diff(a, b, src, dst))


@dataclass
class ChangeSet:
    root: Path
    changes: list[Change] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)          # things a person should know or do

    def _rel(self, p: Path) -> str:
        return Path(p).resolve().relative_to(self.root.resolve()).as_posix()

    def _read(self, rel: str) -> str:
        return (self.root / rel).read_bytes().decode("utf-8")

    # ---------------------------------------------------------------- plan --
    def create(self, path: Path, text: str) -> None:
        rel = self._rel(self.root / path)
        target = self.root / rel
        if target.exists():
            if self._read(rel) == text:
                return                                     # already there
            raise ChangeConflict(f"{rel} exists with other content; not overwriting")
        self.changes.append(Change("create", rel, new_text=text))

    def edit(self, path: Path, new_text: str) -> None:
        rel = self._rel(self.root / path)
        old = self._read(rel)
        if old != new_text:
            self.changes.append(Change("edit", rel, old_text=old, new_text=new_text))

    def move(self, src: Path, dst: Path, new_text: str | None = None) -> None:
        s, d = self._rel(self.root / src), self._rel(self.root / dst)
        if not (self.root / s).exists():
            if (self.root / d).exists():                   # already moved: maybe still to edit
                if new_text is not None:
                    self.edit(self.root / d, new_text)
                return
            raise ChangeConflict(f"{s} does not exist")
        if (self.root / d).exists():
            raise ChangeConflict(f"{d} exists; not overwriting")
        old = self._read(s)
        self.changes.append(Change("move", s, d, old_text=old, new_text=None if new_text == old else new_text))

    # ---------------------------------------------------------------- show --
    @property
    def empty(self) -> bool:
        return not self.changes

    def summary(self) -> list[str]:
        out = []
        for c in self.changes:
            if c.kind == "move":
                out.append(f"move    {c.path} -> {c.new_path}" + (" (edited)" if c.new_text is not None else ""))
            else:
                out.append(f"{c.kind:<7} {c.path}")
        return out

    def diff(self) -> str:
        return "\n".join(c.diff() for c in self.changes)

    def as_json(self, applied: bool) -> str:
        """The changes; a dry run (not applied) also carries each unified diff,
        so a reader of the JSON (an agent) can show what would change."""
        return json.dumps({"applied": applied, "changes": [
            {"kind": c.kind, "path": c.path, **({"new_path": c.new_path} if c.new_path else {}),
             **({} if applied else {"diff": c.diff()})}
            for c in self.changes], "notes": self.notes}, indent=1)

    # --------------------------------------------------------------- apply --
    def apply(self) -> None:
        git = (self.root / ".git").exists() and shutil.which("git") is not None
        for c in self.changes:
            if c.kind == "create":
                (self.root / c.path).parent.mkdir(parents=True, exist_ok=True)
                (self.root / c.path).write_bytes(c.new_text.encode("utf-8"))
            elif c.kind == "edit":
                (self.root / c.path).write_bytes(c.new_text.encode("utf-8"))
            elif c.kind == "move":
                dst = self.root / c.new_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                tracked = git and subprocess.run(["git", "ls-files", "--error-unmatch", c.path], cwd=self.root,
                                                 capture_output=True).returncode == 0
                if tracked:
                    subprocess.run(["git", "mv", c.path, c.new_path], cwd=self.root, check=True, capture_output=True)
                else:
                    shutil.move(str(self.root / c.path), str(dst))
                if c.new_text is not None:
                    dst.write_bytes(c.new_text.encode("utf-8"))


# ------------------------------------------------- .vscode/tasks.json list --
TASKS = Path(".vscode") / "tasks.json"


def tasks_with(text: str, add: tuple[str, ...] = (), remove: tuple[str, ...] = ()) -> str:
    """tasks.json text with project names added to / removed from the
    projectSelector options ("ALL" first, the rest sorted), editing only
    those lines so the rest of the file keeps its formatting."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    try:
        start = next(i for i, ln in enumerate(lines) if '"id": "projectSelector"' in ln)
        opt = next(i for i in range(start, len(lines)) if '"options": [' in lines[i])
        end = next(i for i in range(opt, len(lines)) if lines[i].strip().startswith("]"))
    except StopIteration as exc:
        raise ChangeConflict(".vscode/tasks.json has no projectSelector options list") from exc
    items = [ln.strip().rstrip(",").strip('"') for ln in lines[opt + 1:end] if ln.strip()]
    indent = lines[opt + 1][: len(lines[opt + 1]) - len(lines[opt + 1].lstrip())] if end > opt + 1 else " " * 8
    names = sorted((set(items) - {"ALL"} | set(add)) - set(remove))
    head = ["ALL"] if "ALL" in items else []
    body = [f'{indent}"{n}"' + ("," if k < len(head + names) - 1 else "") for k, n in enumerate(head + names)]
    return nl.join(lines[:opt + 1] + body + lines[end:])
