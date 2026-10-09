"""Live numbers (fig_atlas.claims, roadmap P.4): recording values, filling
placeholders, and finding numbers still typed by hand."""
from __future__ import annotations

import numpy as np
import pytest

from fig_atlas import claims


@pytest.fixture(autouse=True)
def _clean_registry():
    claims.REGISTRY.clear()
    yield
    claims.REGISTRY.clear()


def test_record_and_fill():
    assert claims.record("n_anchors", np.int64(4321), source="promoter DA") == 4321
    assert type(claims.REGISTRY["n_anchors"]["value"]) is int           # JSON-safe
    claims.record("share", 0.591)
    text, missing = claims.fill("{n_anchors:,} anchors ({share:.0%}); {n_unknown} more; {gene,atac}",
                                claims.REGISTRY)
    assert text == "4,321 anchors (59%); {n_unknown} more; {gene,atac}"   # unknown stays visible, prose braces untouched
    assert missing == ["n_unknown"]
    with pytest.raises(ValueError):
        claims.record("not an identifier", 1)


@pytest.mark.parametrize("text,number,kind", [
    ("defines 4,321 anchor genes", "4,321", "claim"),
    ("same direction (n = 1,354)", "1,354", "claim"),            # "n =" is a count, not a cut-off
    ("|log2FC| >= 0.585 (ATAC) / 1.0 (RNA)", None, "pair"),
    ("Promoters hold 59% of human peaks", "59%", "claim"),
    ("mouse opens only 63, leaving", "63", "claim"),             # trailing comma not part of the number
    ("significant (padj < 0.05)", "0.05", "threshold"),
    ("|log2FC| >= 0.585", "0.585", "threshold"),
    ("as in Main Figure 3", "3", "reference"),
    ("Supplementary Table S6", None, None),                     # S6 is an identifier, not a number
    ("at acute day 1 versus control", "1", "other"),
    ("chronic 24 h exposure", "24", "other"),
    ("odds ratios and 95% CIs", "95%", "other"),
    ("enriched in GO:0006979", "0006979", "other"),
    ("{n_anchors:,} anchors", None, None),                      # placeholders are not hand-typed
])
def test_scan_classifies(text, number, kind):
    hits = claims.scan(text)
    if kind == "pair":
        assert [h["kind"] for h in hits] == ["threshold", "other"]   # neither counts as a result
        return
    if number is None:
        assert hits == []
    else:
        assert [(h["number"], h["kind"]) for h in hits] == [(number, kind)]
