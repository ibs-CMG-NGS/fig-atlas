"""Live numbers for figure text (roadmap Phase 3P, step P.4).

Numbers quoted in a figure's legend (FigureSpec ``panel_notes``,
``claim_boundary``, ``title``) are typed by hand today, so they go stale
silently when the data changes -- the figure is rebuilt, its text is not.

An analysis script records the numbers it computed::

    from fig_atlas import claims
    claims.record("n_open_anchors", int(len(anchors)), source="promoter DA peaks, padj < 0.05")

and the FigureSpec text refers to them with placeholders::

    panel_notes=["{n_open_anchors:,} promoter anchors open in human."]

``fa build`` stores recorded values in the figure's provenance record and
publish fills the placeholders (Python format specs: ``{n:,}``, ``{f:.1%}``).
A placeholder with no recorded value is left as written and verify FAILs.

``scan`` finds the numbers still typed by hand, so their count can be
tracked down to zero. It sorts every number it finds:

- ``claim``      a quantity the data determines (counts, percentages,
                 statistics) -- the ones that go stale
- ``threshold``  a cut-off after a comparison sign (``padj < 0.05``)
- ``reference``  a figure / table / panel / revision / version number
- ``other``      dates, identifiers (GO:0006979), ranges in names, ...

The sort is a heuristic: read the ``claim`` list before acting on it.
"""
from __future__ import annotations

import re

# values recorded by this run (name -> {"value", "source"}); the provenance
# recorder copies them into every figure record the run writes.
REGISTRY: dict[str, dict] = {}

PLACEHOLDER = re.compile(r"\{([A-Za-z_]\w*)(?::([^{}]*))?\}")


def record(name: str, value, source: str = "") -> object:
    """Register a number this run computed; returns ``value`` unchanged."""
    if not re.fullmatch(r"[A-Za-z_]\w*", name):
        raise ValueError(f"claim name must be an identifier: {name!r}")
    if hasattr(value, "item"):                 # numpy scalars -> plain Python, for JSON
        value = value.item()
    REGISTRY[name] = {"value": value, "source": source}
    return value


def fill(text: str, values: dict) -> tuple[str, list[str]]:
    """Replace ``{name}`` / ``{name:spec}`` with recorded values. Returns the
    text and the placeholder names that had no value (left as written)."""
    missing = []

    def sub(m: re.Match) -> str:
        name, spec = m.group(1), m.group(2) or ""
        if name not in values:
            missing.append(name)
            return m.group(0)
        v = values[name]["value"] if isinstance(values[name], dict) else values[name]
        return format(v, spec)

    return PLACEHOLDER.sub(sub, text), missing


def placeholders(text: str) -> list[str]:
    return [m.group(1) for m in PLACEHOLDER.finditer(text)]


# ------------------------------------------------------------------ scanning --
NUMBER = re.compile(r"(?<![\w.])[-−+]?\d(?:[\d,]*\d)?(?:\.\d+)?(?:\s?%)?(?![\w])")
# Experimental design, not results: time points and stages ("acute day 1",
# "chronic 24 h", "day 1/3", "3-h pulse", "Stage 1") and confidence levels.
_DESIGN_BEFORE = re.compile(r"(?:\b(?:day|days|Day|stage|Stage|week|weeks|hour|hours|chronic|acute)\s*|\d/)$")
_DESIGN_AFTER = re.compile(r"^(?:\s?[-–]?\s?h\b|/\d|\s?%\s*CI|\s*CIs?\b|\s?[-–]h\b)")
_REFERENCE = re.compile(
    r"(?:\b(?:Main\s+)?(?:Fig(?:ure|s)?\.?|Figures?|Tables?|Panels?|Supplementary(?:\s+(?:Figure|Table))?|Extended\s+Data"
    r"(?:\s+Fig(?:ure)?\.?)?|ED|S|R|v|개편\(|Revision\s?\(|Act|Step|step|row|rows|col|column|Request|item|§|section|Section|Part|"
    r"phase|Phase|class|cluster|module|Module|Cluster|tier|Tier|pattern|Pattern|chr|top|Top)\s*[-–]?\s*)$")
_THRESHOLD = re.compile(r"(?:[<>≤≥=]|<=|>=|\bat\s+least|\bover|\babove|\bbelow|\bunder|\bcut-?off|\bthreshold|"
                        r"\bFDR|\bpadj|\bq|\bp|\bP|\bFC|\|log2FC\||log2FC|\bmin(?:imum)?|\bmax(?:imum)?)\s*$")
_OTHER_BEFORE = re.compile(r"(?:GO:|hsa|mmu|KEGG:|R-HSA-|ENS\w*|rs|[A-Za-z]\d*[-_]|20\d\d-|\d\s?[-–]\s?|/\s?|\.)$")
_DATE = re.compile(r"^20\d\d$")
_UNIT_AFTER = re.compile(r"^\s*(?:pt|mm|in|cm|px|dpi|uM|µM|μM|nM|mM|M|h|H|D|d|bp|kb|Mb)\b")


def classify(text: str, start: int, end: int) -> str:
    before = text[max(0, start - 40):start]
    token = text[start:end].strip()
    after = text[end:end + 6]
    if _DATE.match(token) or _OTHER_BEFORE.search(before):
        return "other"
    if _DESIGN_BEFORE.search(before) or _DESIGN_AFTER.match(after) or (token.endswith("%") and
                                                                       re.match(r"^\s*CI", after)):
        return "other"
    if re.search(r"\b[nN]\s*=\s*$", before):
        return "claim"            # "n = 1,354": a count, not a cut-off
    if _REFERENCE.search(before) or re.match(r"^[a-z](?:[–-][a-z])?\b|^[A-Z]\b", after):
        return "reference"
    if _THRESHOLD.search(before):
        return "threshold"
    if _UNIT_AFTER.match(after):
        return "other"            # doses, durations, print sizes: design, not results
    return "claim"


def scan(text: str) -> list[dict]:
    """Numbers typed into ``text`` (placeholders excluded), each classified."""
    blanked = PLACEHOLDER.sub(lambda m: " " * len(m.group(0)), text)
    out = []
    for m in NUMBER.finditer(blanked):
        token = m.group(0).strip()
        if not any(ch.isdigit() for ch in token):
            continue
        kind = classify(blanked, m.start(), m.end())
        lo, hi = max(0, m.start() - 30), min(len(text), m.end() + 30)
        out.append({"number": token, "kind": kind, "context": text[lo:hi].replace("\n", " ")})
    return out



def use_from(project: str, figure: int = 1, names: list[str] | None = None, root=None) -> dict:
    """Take numbers another figure recorded (from its published provenance
    record), so a figure quoting them -- a summary schematic, a legend that
    refers back -- shows the same values. Reading the record makes it an
    input of this build, so this figure goes stale when those numbers change.
    Raises if that figure has not been built with a record."""
    import json
    from . import get_config
    from .projects import find_project, find_root
    root = root or find_root()
    figures_root = get_config(find_project(root, project).config).figures_root
    hits = sorted(figures_root.glob(f"figure_{figure:02d}_*/figure_{figure:02d}.provenance.json"))
    if not hits:
        raise FileNotFoundError(f"{project} figure {figure} has no published provenance record; build it first")
    values = json.loads(hits[0].read_text(encoding="utf-8")).get("claims") or {}
    taken = {}
    for name, v in values.items():
        if names is None or name in names:
            REGISTRY[name] = {"value": v["value"], "source": f"{project} figure {figure}: {v.get('source', '')}"}
            taken[name] = v["value"]
    missing = sorted(set(names or []) - set(taken))
    if missing:
        raise KeyError(f"{project} figure {figure} recorded no value for: {', '.join(missing)}")
    return taken
