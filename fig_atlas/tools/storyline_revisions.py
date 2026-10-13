"""Storyline revision records (roadmap Phase 3S, step S.2).

The storyline markdown keeps a prose log of revisions -- blockquote blocks
headed like ``> **2026-09 개편(18) — title**: ...`` scattered through its
sections. This module copies them, verbatim and without touching the md, into
one structured record per revision number,
``docs/storylines/<topic>/revisions/RNNN.md`` (YAML front matter + the original
blocks), and writes an index (``revisions/README.md``) that also lists unused
numbers and numbers that look reused for different changes.

Records are created once and never overwritten, so front matter filled in by
a person (kind, evidence, ...) survives later syncs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# A revision block opens with a blockquote line whose bold header names the
# revision: "> **2026-09 개편(18) — title**: ..." or "> *(이력)* **2026-09 개편(6)**: ...".
HEADER = re.compile(r"^>\s*(?:\*\([^)]*\)\*\s*)?\*\*(?P<date>20\d\d-\d\d(?:-\d\d)?\s+)?(?:개편|Revision)\s?\((?P<n>\d+)\)"
                    r"(?:\s*[—-]\s*(?P<title>[^*]+?))?\*\*")
FULL_DATE = re.compile(r"\((20\d\d-\d\d-\d\d)\)")
KINDS = "renumber | redesign | promote | retire | data-update | definition-change | layout"


def _q(s) -> str:
    return json.dumps(s, ensure_ascii=False)


def extract_blocks(md: Path) -> list[dict]:
    """Every revision block in ``md``, verbatim, with the heading it sits
    under. A block is its header line plus the blockquote lines continuing it
    (up to an empty '>' line, a non-quote line or the next header)."""
    lines = md.read_text(encoding="utf-8").split("\n")
    blocks, heading, i = [], "", 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        m = HEADER.match(line.strip())
        if not m:
            i += 1
            continue
        body, j = [line], i + 1
        while (j < len(lines) and lines[j].startswith(">") and lines[j].strip() != ">"
               and not HEADER.match(lines[j].strip())):
            body.append(lines[j])
            j += 1
        text = "\n".join(body)
        title = (m.group("title") or "").strip()
        date = (m.group("date") or "").strip()
        if not date:
            found = FULL_DATE.search(title) or FULL_DATE.search(text)
            date = found.group(1) if found else ""
        blocks.append({"n": int(m.group("n")), "date": date, "title": title, "section": heading,
                       "line": i + 1, "text": text})
        i = j
    return blocks


def group(blocks: list[dict]) -> dict[int, list[dict]]:
    by_n: dict[int, list[dict]] = {}
    for b in blocks:
        by_n.setdefault(b["n"], []).append(b)
    return by_n


def report(by_n: dict[int, list[dict]]) -> dict:
    nums = sorted(by_n)
    gaps = [n for n in range(1, (nums[-1] if nums else 0) + 1) if n not in by_n]
    # One number, blocks with different explicit titles: likely two changes sharing a number.
    collisions = {n: sorted({b["title"] for b in bs if b["title"]}) for n, bs in by_n.items()
                  if len({b["title"] for b in bs if b["title"]}) > 1}
    # Several blocks without conflicting titles: usually one change logged in
    # each section it touched, but a reused number can hide here too.
    multi = [n for n, bs in sorted(by_n.items()) if len(bs) > 1 and n not in collisions]
    return {"count": len(nums), "blocks": sum(len(v) for v in by_n.values()), "gaps": gaps,
            "collisions": collisions, "multi_block": multi, "latest": f"R{nums[-1]:03d}" if nums else "R000"}


def mentions(text: str, project_names: set[str]) -> tuple[list[str], list[str]]:
    """Projects named in the text, and data-request documents it cites."""
    projects = sorted(p for p in project_names if p in text)
    requests = sorted(set(re.findall(r"[\w.-]+_request\.md", text)))
    return projects, requests


def record_text(n: int, bs: list[dict], md_rel: str, project_names: set[str], snapshot: str | None = None) -> str:
    projects, requests = mentions("\n".join(b["text"] for b in bs), project_names)
    dates = sorted({b["date"] for b in bs if b["date"]})
    titles = [b["title"] for b in bs if b["title"]]
    front = ["---",
             f"id: R{n:03d}",
             f"date: {_q(dates[-1] if dates else '')}",
             f"title: {_q(titles[0] if titles else '')}",
             f"kind: []          # {KINDS}",
             "figures: [" + ", ".join(_q(p) for p in projects) + "]   # projects named in the blocks",
             "evidence:",
             "  requests: [" + ", ".join(_q(r) for r in requests) + "]",
             f"snapshot: {_q(snapshot)}   # compile snapshot (fa storyline diff)" if snapshot else
             "snapshot: \"none -- pre-ledger (recorded from the storyline's prose log)\"",
             f"source: {_q(md_rel)}",
             "sections:"]
    front += [f"  - {{line: {b['line']}, heading: {_q(b['section'])}}}" for b in bs]
    front += ["---", ""]
    body = []
    for b in bs:
        body += [f"### {b['section'] or '(top)'} (line {b['line']})", "", b["text"], ""]
    return "\n".join(front + body)


def blocks_in_record(path: Path) -> list[str]:
    """The verbatim blocks stored in a record (for the lossless check)."""
    text = path.read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1] if text.startswith("---") else text
    out, cur = [], []
    for line in body.split("\n"):
        if line.startswith("### "):
            if cur:
                out.append("\n".join(cur).strip("\n"))
            cur = []
        elif line.startswith(">") or (cur and line):
            cur.append(line)
    if cur:
        out.append("\n".join(cur).strip("\n"))
    return out


def sync(md: Path, out_dir: Path, root: Path, project_names: set[str]) -> tuple[list[Path], dict]:
    """Write records for revision numbers that have none yet, and the index.
    A record made after the revision was compiled points at its snapshot."""
    snaps = root / "outputs" / "storylines" / md.stem
    by_n = group(extract_blocks(md))
    out_dir.mkdir(parents=True, exist_ok=True)
    new = []
    for n, bs in sorted(by_n.items()):
        path = out_dir / f"R{n:03d}.md"
        if not path.exists():
            snap = snaps / f"R{n:03d}"
            snap_rel = snap.relative_to(root).as_posix() + "/" if (snap / "revision.json").is_file() else None
            path.write_text(record_text(n, bs, md.relative_to(root).as_posix(), project_names, snap_rel),
                            encoding="utf-8")
            new.append(path)
    rep = report(by_n)
    write_index(out_dir, by_n, rep, md, project_names)
    return new, rep


def write_index(out_dir: Path, by_n: dict, rep: dict, md: Path, project_names: set[str]) -> None:
    lines = ["# Storyline revisions", "",
             f"<!-- generated by `fa storyline revisions --sync` from {md.name}; the RNNN.md records are the "
             "editable source -->", "",
             f"{rep['count']} revisions ({rep['blocks']} blocks in the storyline's prose log); latest "
             f"**{rep['latest']}**. Records made from the prose log carry `snapshot: none -- pre-ledger`: "
             "there is no committed state of the compendium to restore for them.", ""]
    if rep["gaps"]:
        lines.append(f"- Numbers never used: {', '.join(str(g) for g in rep['gaps'])}")
    for n, titles in sorted(rep["collisions"].items()):
        lines.append(f"- **Possible numbering collision -- revision {n}** has blocks with different titles: "
                     + "; ".join(f'"{t}"' for t in titles) + ". Check whether these are two changes.")
    if rep["multi_block"]:
        lines.append("- Logged in more than one place (one change per section, or a reused number -- read the "
                     f"record to tell): {', '.join(str(n) for n in rep['multi_block'])}")
    lines += ["", "| Revision | Date | Title | Blocks (sections) | Projects named |", "|---|---|---|---|---|"]
    for n, bs in sorted(by_n.items(), reverse=True):
        titles = sorted({b["title"] for b in bs if b["title"]}) or ["(untitled)"]
        dates = sorted({b["date"] for b in bs if b["date"]})
        projects, _ = mentions("\n".join(b["text"] for b in bs), project_names)
        secs = "; ".join(sorted({(b["section"] or "(top)")[:40] for b in bs}))
        lines.append(f"| [R{n:03d}](R{n:03d}.md) | {', '.join(dates)} | {' / '.join(titles)} | "
                     f"{len(bs)} ({secs}) | {len(projects)} |")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
