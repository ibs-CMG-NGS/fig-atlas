"""Evidence ledger (roadmap Phase 3S, step S.4).

Data requests (``docs/data_contracts/*_request.md``) record why the storyline
needed new data and what came back. Each carries a front matter block:

    request: class_v2_enrichment_rerun
    status: delivered        # open | partial | delivered | resolved | superseded
    date: "2026-10-01"       # date on the Status line
    delivered: [...]         # where the delivery landed (raw_data/ files or folders)
    derived: [...]           # bundle files built from it that figures read
    superseded_by: [...]

Whether a request is *integrated* is not declared: it is computed from the
provenance records -- a published figure read one of its files. ``evidence``
follows the chain slot -> project -> figure -> inputs (with their hashes and
upstream bundle) -> requests -> revision records.

``sync`` adds a drafted front matter block to request documents that have
none (status, date and delivery paths read from the Status/Update lines);
the document text below it is kept byte for byte, and existing front matter
is never changed.
"""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

import yaml

STATUSES = ("open", "partial", "delivered", "resolved", "superseded")
DATE = re.compile(r"20\d\d-\d\d-\d\d")
TOKEN = re.compile(r"`([^`\s]+)`")
# File names too generic to identify a request by mention alone.
GENERIC = {"data.csv", "metadata.yaml", "metadata.json", "statistics.csv", "README.md"}
FILE_EXT = (".csv", ".tsv", ".txt", ".yaml", ".yml", ".json", ".bed", ".gz", ".xlsx", ".rds")


# ------------------------------------------------------------------ parsing --
def split_front_matter(text: str) -> tuple[dict | None, str]:
    if text.startswith("---"):
        parts = re.split(r"^---[ \t]*\r?$", text, maxsplit=2, flags=re.M)
        if len(parts) == 3:
            return yaml.safe_load(parts[1]) or {}, parts[2].lstrip("\r\n")
    return None, text


def _header(body: str) -> list[str]:
    """Lines between the title and the first horizontal rule: Target,
    Consumer, Status and the dated Update notes."""
    out = []
    for line in body.splitlines()[1:]:
        if line.strip() == "---":
            break
        out.append(line)
    return out


def _expand(token: str) -> list[str]:
    """`a/{x,y}/<class>.csv` -> glob patterns a/x/*.csv, a/y/*.csv."""
    m = re.search(r"\{([^{}]*)\}", token)
    if m:
        return [p for alt in m.group(1).split(",") for p in _expand(token[:m.start()] + alt + token[m.end():])]
    return [re.sub(r"<[^<>]*>", "*", token)]


def _paths(text: str) -> list[str]:
    return sorted({p for t in TOKEN.findall(text) if t.startswith("raw_data/") for p in _expand(t)})


def _delivery_lines(body: str) -> list[str]:
    """Paths on the body's "Delivery:" lines and under "Delivery" headings;
    `.../name` means the folder of the line's previous path."""
    out, lines = [], body.splitlines()
    picked = []
    for i, line in enumerate(lines):
        if line.lstrip("*_ ").startswith("Delivery"):
            picked.append(line)
        elif line.startswith("#") and "delivery" in line.lower():      # "### Delivery path" + its first paragraph
            para = False
            for nxt in lines[i + 1:]:
                if nxt.startswith("#") or (para and not nxt.strip()):
                    break
                para = para or bool(nxt.strip())
                picked.append(nxt)
    for line in picked:
        prev = None
        for t in TOKEN.findall(line):
            if t.startswith(".../") and prev:
                parent = prev.rstrip("/").rsplit("/", 1)[0]
                t = parent + "/" + t[4:]
            if t.startswith("raw_data/"):
                out += _expand(t)
                prev = t
    return out


def draft(path: Path, body: str) -> dict:
    """Front matter drafted from a request's Status/Update lines."""
    head = _header(body)
    status_line = next((l for l in head if l.startswith("**Status**")), "")
    low = status_line.lower()
    header_text = "\n".join(head)
    if "superseded" in low or ("superseded" in header_text.lower() and not re.search(r"deliver|fulfil|resolv|open", low)):
        status = "superseded"
    elif "resolved" in low:
        status = "resolved"
    elif "partial" in low or "partly" in low:
        status = "partial"
    elif re.search(r"\bopen\b", low):
        status = "open"
    elif "delivered" in low or "fulfilled" in low:
        status = "delivered"
    else:
        status = "open"
    date = DATE.search(status_line)
    superseded_by = sorted({t for l in head if "superseded" in l.lower() for t in TOKEN.findall(l)
                            if t.endswith("_request.md") and t != path.name})
    return {"request": path.stem.removesuffix("_request"), "status": status,
            "date": date.group(0) if date else "",
            "delivered": sorted(set(_paths(header_text) + _delivery_lines(body)))
            if status in ("delivered", "partial", "resolved") else [],
            "derived": [], "superseded_by": superseded_by}


def _q(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def front_matter_text(fm: dict, nl: str) -> str:
    lines = ["---",
             f"request: {_q(fm['request'])}",
             f"status: {fm['status']}          # {' | '.join(STATUSES)} (integrated = computed from provenance)",
             f"date: {_q(fm['date'])}",
             "delivered:         # where the delivery landed: raw_data/ files or folders (globs allowed)"]
    lines += [f"  - {_q(p)}" for p in fm["delivered"]] or ["  []"]
    lines += ["derived:           # bundle files built from the delivery that figures read"]
    lines += [f"  - {_q(p)}" for p in fm["derived"]] or ["  []"]
    lines += ["superseded_by: [" + ", ".join(_q(s) for s in fm["superseded_by"]) + "]", "---", "", ""]
    return nl.join(lines)


def load_requests(req_dir: Path) -> list[dict]:
    out = []
    for p in sorted(req_dir.glob("*_request.md")):
        text = p.read_text(encoding="utf-8")
        fm, body = split_front_matter(text)
        out.append({"path": p, "name": p.name, "front_matter": fm, "body": body,
                    "mentions": sorted({q for t in TOKEN.findall(body) for q in _expand(t)
                                        if t.startswith("raw_data/") or
                                        (t.endswith(FILE_EXT) and "/" not in t and t not in GENERIC)})})
    return out


def sync(req_dir: Path) -> list[Path]:
    """Add drafted front matter to request documents that have none."""
    added = []
    for p in sorted(req_dir.glob("*_request.md")):
        raw = p.read_bytes().decode("utf-8")
        if split_front_matter(raw)[0] is not None:
            continue
        nl = "\r\n" if "\r\n" in raw else "\n"
        p.write_bytes((front_matter_text(draft(p, raw), nl) + raw).encode("utf-8"))
        added.append(p)
    return added


# ----------------------------------------------------------------- matching --
def _covers(pattern: str, path: str) -> bool:
    if "{" in pattern or "<" in pattern:
        return any(_covers(p, path) for p in _expand(pattern))
    pattern = pattern.rstrip("/")
    if any(c in pattern for c in "*?["):
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern + "/*")
    return path == pattern or path.startswith(pattern + "/")


def link(req: dict, input_path: str) -> str | None:
    """'declared' when the request's delivered/derived paths cover the input,
    'mentioned' when its text names the file, else None."""
    fm = req["front_matter"] or {}
    if any(_covers(p, input_path) for p in (fm.get("delivered") or []) + (fm.get("derived") or [])):
        return "declared"
    base = input_path.rsplit("/", 1)[-1]
    for m in req["mentions"]:
        if "/" in m:
            if _covers(m, input_path):
                return "mentioned"
        elif base not in GENERIC and fnmatch.fnmatch(base, m):
            return "mentioned"
    return None


# ------------------------------------------------------------------ queries --
def revision_records(rev_dir: Path) -> list[dict]:
    out = []
    for p in sorted(rev_dir.glob("R*.md")):
        if not re.fullmatch(r"R\d+", p.stem):
            continue
        fm, _ = split_front_matter(p.read_text(encoding="utf-8"))
        if fm:
            out.append({"id": fm.get("id", p.stem), "title": fm.get("title", ""), "figures": fm.get("figures") or [],
                        "requests": (fm.get("evidence") or {}).get("requests") or []})
    return out


def figure_evidence(root: Path, record: dict, requests: list[dict], cache=None) -> list[dict]:
    """Each recorded raw input of a figure, whether it still matches the
    recorded hash, and the requests behind it."""
    out = []
    for item in record.get("inputs", []):
        path = item["path"]
        if not path.startswith("raw_data/"):
            continue
        p = root / path
        now = cache.sha256(p) if (cache and p.is_file()) else None
        out.append({"path": path, "sha256": item.get("sha256"), "bundle": item.get("bundle"),
                    "current": None if now is None else now == item.get("sha256"),
                    "requests": [{"request": r["name"], "how": how} for r in requests
                                 if (how := link(r, path))]})
    return out


def ledger(root: Path, requests: list[dict], records: list[tuple[Path, dict]]) -> list[dict]:
    """Per request: declared status and the published figures that read its files."""
    rows = []
    for r in requests:
        fm = r["front_matter"] or {}
        used = {}
        for rec_path, rec in records:
            for item in rec.get("inputs", []):
                how = link(r, item["path"]) if item["path"].startswith("raw_data/") else None
                if how:
                    fig = rec_path.parent.relative_to(root).as_posix()
                    if used.get(fig) != "declared":
                        used[fig] = how
        missing = [p for p in fm.get("delivered") or [] if not any(c in p for c in "*?[")
                   and not (root / p.rstrip("/")).exists()]
        rows.append({"request": r["name"], "status": fm.get("status", "(no front matter)"), "date": fm.get("date", ""),
                     "delivered": fm.get("delivered") or [], "derived": fm.get("derived") or [],
                     "missing": missing, "superseded_by": fm.get("superseded_by") or [],
                     "integrated": sorted(f for f, h in used.items() if h == "declared"),
                     "mentioned_by": sorted(f for f, h in used.items() if h == "mentioned")})
    return rows
