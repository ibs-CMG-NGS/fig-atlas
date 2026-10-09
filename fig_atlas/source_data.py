"""Source Data: the values each panel actually plots (roadmap Phase 3P, step P.5).

Journals ask for the numbers behind every panel -- what was drawn, not the
raw inputs. An analysis script registers the table a panel is drawn from,
before it saves the figure::

    from fig_atlas import source_data
    source_data.add(volcano_df[["peak_id", "log2FoldChange", "padj", "direction"]],
                    panel="a", title="Human ATAC acute day 1 vs control, every peak")
    fig.savefig(...)

Tables registered since the previous ``savefig`` belong to the figure saved
next. ``fa build`` (the provenance recorder) writes them as CSV files beside
that figure (``<stem>.source_data/panel_a.csv``, one per table), lists them in
the figure's provenance record with row counts and hashes, and publish copies
them to ``figure_NN_source_data/`` with an index. CSV keeps the output
byte-identical between builds; outside ``fa build`` registering is a no-op.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

PENDING: list[dict] = []


def add(df, panel: str, title: str = "", name: str = "", note: str = ""):
    """Register the table panel ``panel`` is drawn from; returns ``df``."""
    if not re.fullmatch(r"[A-Za-z0-9]+", str(panel)):
        raise ValueError(f"panel must be letters/digits, e.g. 'a': {panel!r}")
    if name and not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError(f"name must be letters, digits, '_' or '-': {name!r}")
    PENDING.append({"panel": str(panel), "name": name, "title": title, "note": note, "df": df.copy()})
    return df


def take() -> list[dict]:
    """Tables registered since the last call (the recorder takes them on savefig)."""
    out = PENDING[:]
    PENDING.clear()
    return out


def file_name(t: dict) -> str:
    return f"panel_{t['panel']}" + (f"_{t['name']}" if t["name"] else "") + ".csv"


def write(tables: list[dict], out_dir: Path, rel) -> list[dict]:
    """Write tables as CSV into ``out_dir``; return their record entries.
    ``rel`` turns a path into its repository-relative string."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("panel_*.csv"):
        old.unlink()                               # a rebuild replaces the set
    entries, seen = [], set()
    for t in tables:
        fname = file_name(t)
        if fname in seen:
            raise ValueError(f"two source-data tables for {fname}; give them different name=")
        seen.add(fname)
        path = out_dir / fname
        t["df"].to_csv(path, index=False, lineterminator="\n")
        entries.append({"panel": t["panel"], "name": t["name"], "title": t["title"], "note": t["note"],
                        "path": rel(path), "rows": int(len(t["df"])), "columns": [str(c) for c in t["df"].columns],
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return entries


def index_markdown(entries: list[dict], figure_number: int, title: str) -> str:
    """README of a published figure_NN_source_data/ folder."""
    lines = [f"# Source data: Figure {figure_number}", "", title, "",
             "Values each panel plots, one CSV per table (written by the build that made the figure; "
             "hashes in the figure's provenance record).", "",
             "| Panel | File | Rows | Columns | Content |", "|---|---|---|---|---|"]
    for e in entries:
        cols = ", ".join(e["columns"][:8]) + (" ..." if len(e["columns"]) > 8 else "")
        content = e["title"] + (f" ({e['note']})" if e["note"] else "")
        lines.append(f"| {e['panel']} | `{Path(e['path']).name}` | {e['rows']:,} | {cols} | {content} |")
    return "\n".join(lines) + "\n"
