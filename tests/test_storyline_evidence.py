"""Evidence ledger (fig_atlas/tools/storyline_evidence.py, roadmap S.4): drafting
request front matter without touching the text, linking figure inputs to the
requests that delivered them, and the evidence chain."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

DELIVERED = """# Data Request: Re-run

**Target**: pipeline
**Status**: **DELIVERED 2026-10-01** — integrated (storyline 개편(33)). Supersedes `old_request.md`.

---

## A
Delivery: `raw_data/s/anchor/ora_v2/` and `.../gsea_v2/`, plus a provenance file.

### Delivery path
`raw_data/s/{gene,atac}-full/inputs/table_<class>_v2.csv`

Background: the old file `raw_data/s/anchor/rna_bundle/inputs/data.csv` and `motif_hits_v1.csv`.
"""

SUPERSEDED = """# Data Request: PCA

**Status**: This is a from-scratch computation request.

> **Update 2026-10-02**: Request B is **superseded** by `new_request.md`.

---
body
"""

PARTLY = "# R\n\n**Status**: **PARTLY DELIVERED 2026-10-01 — follow-up open (§6).** Received `raw_data/x/inputs/`.\n\n---\n"


@pytest.fixture(scope="module")
def ev():
    spec = importlib.util.spec_from_file_location("storyline_evidence", REPO / "fig_atlas" / "tools" / "storyline_evidence.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_draft_reads_status_and_delivery_paths(ev, tmp_path):
    d = ev.draft(tmp_path / "rerun_request.md", DELIVERED)
    assert d["request"] == "rerun" and d["status"] == "delivered" and d["date"] == "2026-10-01"
    assert d["delivered"] == ["raw_data/s/anchor/gsea_v2/", "raw_data/s/anchor/ora_v2/",
                              "raw_data/s/atac-full/inputs/table_*_v2.csv", "raw_data/s/gene-full/inputs/table_*_v2.csv"]
    assert d["superseded_by"] == []                     # "Supersedes X" is not "superseded by X"
    s = ev.draft(tmp_path / "pca_request.md", SUPERSEDED)
    assert s["status"] == "superseded" and s["superseded_by"] == ["new_request.md"] and s["delivered"] == []
    p = ev.draft(tmp_path / "p_request.md", PARTLY)
    assert p["status"] == "partial" and p["delivered"] == ["raw_data/x/inputs/"]


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_sync_adds_front_matter_and_keeps_text_byte_for_byte(ev, tmp_path, nl):
    doc = tmp_path / "rerun_request.md"
    original = DELIVERED.replace("\n", nl).encode("utf-8")
    doc.write_bytes(original)
    assert ev.sync(tmp_path) == [doc]
    now = doc.read_bytes()
    assert now.endswith(original) and now.startswith(b"---")
    assert b"\r\n" not in now[: len(now) - len(original)] if nl == "\n" else True
    fm, body = ev.split_front_matter(now.decode("utf-8"))
    assert fm["status"] == "delivered" and body.startswith("# Data Request")
    edited = now.replace(b"status: delivered", b"status: resolved")
    doc.write_bytes(edited)
    assert ev.sync(tmp_path) == [] and doc.read_bytes() == edited   # existing front matter is never touched


def test_links_declared_mentioned_and_generic_names(ev, tmp_path):
    doc = tmp_path / "rerun_request.md"
    doc.write_text(DELIVERED, encoding="utf-8")
    ev.sync(tmp_path)
    text = doc.read_text(encoding="utf-8").replace(
        "derived:           # bundle files built from the delivery that figures read\n  []",
        'derived:           # bundle files built from the delivery that figures read\n  - "raw_data/s/{a,b}/pathway_*_v2.csv"')
    doc.write_text(text, encoding="utf-8")
    (req,) = ev.load_requests(tmp_path)
    assert ev.link(req, "raw_data/s/anchor/ora_v2/ora_concordant.csv") == "declared"     # under a delivered folder
    assert ev.link(req, "raw_data/s/gene-full/inputs/table_concordant_v2.csv") == "declared"
    assert ev.link(req, "raw_data/s/b/pathway_ora_v2.csv") == "declared"                  # derived, brace glob
    assert ev.link(req, "raw_data/s/c/pathway_ora_v2.csv") is None
    assert ev.link(req, "raw_data/s/anchor/rna_bundle/inputs/data.csv") == "mentioned"    # full path named
    assert ev.link(req, "raw_data/other/motif_hits_v1.csv") == "mentioned"                # distinctive file name
    assert ev.link(req, "raw_data/other/inputs/data.csv") is None                         # generic name alone

    records = [(tmp_path / "outputs" / "p" / "figures" / "figure_01_x" / "figure_01.provenance.json",
                {"inputs": [{"path": "raw_data/s/anchor/ora_v2/ora_concordant.csv", "sha256": "a"}]}),
               (tmp_path / "outputs" / "q" / "figures" / "figure_01_y" / "figure_01.provenance.json",
                {"inputs": [{"path": "raw_data/other/motif_hits_v1.csv", "sha256": "b"}]})]
    (row,) = ev.ledger(tmp_path, ev.load_requests(tmp_path), records)
    assert row["integrated"] == ["outputs/p/figures/figure_01_x"]
    assert row["mentioned_by"] == ["outputs/q/figures/figure_01_y"]
    assert row["missing"] == ["raw_data/s/anchor/gsea_v2/", "raw_data/s/anchor/ora_v2/"]   # not on disk here
