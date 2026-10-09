"""Renderer parameter schemas (fig_atlas.schema, roadmap 2.0)."""
from __future__ import annotations

import pytest

from fig_atlas.schema import BoundParams, Param, Schema, SchemaWarning, StyleRef, uses_schema

TYPO = Schema("typography", params=[
    Param("title_size", float, StyleRef("figures.title_size", 8.0), unit="pt", role="Panel title size", tune="lower if it wraps"),
])
VOLCANO = Schema("volcano", extends=[TYPO], params=[
    Param("fc_threshold", float, 1.0, unit="log2FC", role="cut-off lines", tune="raise for fewer", range=(0, None)),
    Param("up_color", "color", "#d62728", unit="hex color", role="up points", tune=""),
    Param("legend_loc", ("best", "upper left", "upper right"), "best", role="legend anchor"),
    Param("legend_fontsize", float, 6.0, unit="pt", aliases=("legend_font_size",)),
])


def test_defaults_come_from_the_schema_and_style():
    p = BoundParams({}, VOLCANO, style={"figures": {"title_size": 7.5}})
    assert p.get("fc_threshold", 0.5) == 1.0            # schema default wins over a stale code default
    assert p.get("title_size", 13) == 7.5               # StyleRef -> the style preset
    assert BoundParams({}, VOLCANO).get("title_size") == 8.0   # no preset: the fallback
    assert p.get("not_in_schema", "x") == "x"           # unknown keys behave like dict.get
    with pytest.warns(SchemaWarning, match="legend_font_size is deprecated; use legend_fontsize"):
        old_name = BoundParams({"legend_font_size": 5}, VOLCANO)
    assert old_name.get("legend_fontsize") == 5        # a config still using the deprecated name


def test_validation_warns_or_raises(monkeypatch):
    bad = {"fc_threshold": -1, "up_color": "reddish", "legend_loc": "middle", "title_size": "8pt"}
    with pytest.warns(SchemaWarning) as w:
        BoundParams(bad, VOLCANO)
    msg = str(w[0].message)
    for part in ("outside [0, None]", "is not a colour", "is not one of", "should be a number"):
        assert part in msg
    monkeypatch.setenv("FA_SCHEMA", "strict")
    with pytest.raises(ValueError):
        BoundParams(bad, VOLCANO)
    BoundParams({"fc_threshold": 2, "up_color": "#000000", "legend_loc": "best", "title_size": 7}, VOLCANO)


def test_whole_floats_and_tuples_are_accepted():
    """Exporters write 30 as 30.0, and scripts pass (lo, hi) pairs as tuples:
    both are what the renderers use, so neither warns; a real mismatch still does."""
    n = Param("top_n", int, 15, unit="terms", role="terms shown")
    assert n.check(30.0) is None and n.check(30) is None
    assert "should be an integer" in n.check(30.5) and "should be an integer" in n.check(True)
    lim = Param("xlim", list, None, unit="data coords", role="x range")
    assert lim.check((-3.2, 3.2)) is None and lim.check([0, 1]) is None
    assert "should be a list" in lim.check("0,1")


def test_decorator_binds_params_positionally_or_by_keyword():
    @uses_schema(VOLCANO)
    def render(ax, df, params):
        return params.get("fc_threshold", 0.1), type(params).__name__

    assert render(None, None, {}) == (1.0, "BoundParams")
    assert render(None, None, params={"fc_threshold": 2.0}) == (2.0, "BoundParams")
    assert render.SCHEMA is VOLCANO
