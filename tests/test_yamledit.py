"""Comment-preserving YAML edits (fig_atlas.yamledit, roadmap 2.0)."""
from __future__ import annotations

from pathlib import Path

import pytest

from fig_atlas import yamledit

REPO = Path(__file__).resolve().parents[1]

# Configs that do not round-trip; tools refuse to edit them. Never grow this list:
# write YAML without trailing spaces and lists/maps spanning lines as block style.
KNOWN_NOT_ROUND_TRIPPABLE = {
    "configs/config.yaml",          # sandbox default config; often carries uncommitted local edits
}


def test_repository_configs_round_trip_unchanged():
    files = sorted((REPO / "configs").rglob("*.yaml")) + sorted((REPO / "styles").glob("*.yaml"))
    new_failures = []
    for f in files:
        rel = f.relative_to(REPO).as_posix()
        try:
            doc = yamledit.load(f)
        except yamledit.NotRoundTrippable:
            if rel not in KNOWN_NOT_ROUND_TRIPPABLE:
                new_failures.append(rel)
            continue
        assert doc.text().encode("utf-8") == f.read_bytes(), rel
    assert new_failures == [], "configs that tools could no longer edit losslessly"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_edit_keeps_comments_order_and_line_endings(tmp_path, newline):
    src = ("# [Panel a] volcano\n"
           "plots:\n"
           "  volcano:\n"
           "    lfc_min: 0.585      # |log2FC| cut-off (data coords); raise to show fewer peaks\n"
           "    colors:\n"
           "      - \"#d62728\"\n"
           "      - \"#1f77b4\"\n"
           "    note: null\n").replace("\n", newline)
    f = tmp_path / "config_x.yaml"
    f.write_bytes(src.encode())
    doc = yamledit.load(f)
    doc.data["plots"]["volcano"]["fdr_max"] = 0.05
    doc.save()
    out = f.read_bytes().decode()
    assert out == src + "    fdr_max: 0.05" + newline


def test_refuses_files_that_would_be_reformatted(tmp_path):
    f = tmp_path / "config_y.yaml"
    f.write_text("plots:\n  order: [\n    a, b]\n  x: 1   \n")
    with pytest.raises(yamledit.NotRoundTrippable):
        yamledit.load(f)
