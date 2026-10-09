"""fig_atlas.render(name, ...): draw a plot by name wherever its renderer lives."""
from __future__ import annotations

import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

import fig_atlas  # noqa: E402
from fig_atlas import recipes, renderer_registry  # noqa: E402


def test_a_core_name_does_not_load_any_pack():
    code = ("import sys\n"
            "from fig_atlas import renderer_registry\n"
            "where, fn = renderer_registry.find('venn')\n"
            "print(where, fn.__name__, 'fig_atlas_omics' in sys.modules)\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.split() == ["core", "render_venn", "False"]


def test_pack_renderer_by_name():
    rng = np.random.default_rng(0)
    lfc = rng.normal(0, 1.5, 50)
    df = pd.DataFrame({"log2FC": lfc, "padj": 10 ** (-np.abs(lfc) * 3)})
    fig, ax = plt.subplots()
    try:
        out = fig_atlas.render("volcano", ax, df, {"log2fc_threshold": 1.0})
    finally:
        plt.close(fig)
    assert "regulation" in out
    assert renderer_registry.find("render_volcano")[0] == "fig_atlas_omics.renderers"


def test_prefix_and_unknown_names():
    assert renderer_registry.find("render_threshold_scatter")[0] == "core"
    with pytest.raises(KeyError, match="fa renderers"):
        renderer_registry.find("no_such_plot")


def test_a_recipe_only_name_is_drawn_through_its_recipe(monkeypatch):
    r = recipes.recipe("effect_p", "fig_atlas.renderers.threshold_scatter:render_threshold_scatter",
                       defaults={"x_col": "d", "y_col": "p", "effect_col": "d", "sig_col": "p",
                                 "y_transform": "neg_log10"})
    monkeypatch.setattr(recipes, "all_recipes", lambda: {"effect_p": r})
    where, fn = renderer_registry.find("effect_p")
    assert where == "recipe"
    fig, ax = plt.subplots()
    try:
        out = fn(ax, pd.DataFrame({"d": [-2.0, 0.1, 2.0], "p": [0.001, 0.5, 0.001]}), params={})
    finally:
        plt.close(fig)
    assert list(out["regulation"]) == ["down", "ns", "up"]


def test_available_lists_core_pack_and_recipes():
    rows = renderer_registry.available()
    sources = {(r["name"], r["source"]) for r in rows}
    assert ("venn", "core") in sources and ("volcano", "fig_atlas_omics.renderers") in sources
    assert ("volcano", "recipe (also a pack renderer)") in sources
