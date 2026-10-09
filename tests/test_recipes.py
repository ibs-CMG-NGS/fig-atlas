"""Recipes (roadmap 6a.3): a domain plot as a generic renderer + settings."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from fig_atlas import config_usage, plugins, recipes  # noqa: E402
from fig_atlas.renderers.threshold_scatter import SCHEMA as GENERIC  # noqa: E402
from fig_atlas_omics.renderers import render_volcano  # noqa: E402


def _df(n=60):
    rng = np.random.default_rng(1)
    lfc = rng.normal(0, 1.5, n)
    return pd.DataFrame({"log2FC": lfc, "padj": 10 ** (-np.abs(lfc) * 3), "symbol": [f"G{i}" for i in range(n)]})


def test_the_pack_registers_volcano_and_ma_plot():
    assert {"volcano", "ma_plot"} <= set(recipes.all_recipes())
    assert recipes.get("volcano").function().__name__ == "render_threshold_scatter"


@pytest.mark.parametrize("name", ["volcano", "ma_plot"])
def test_recipe_names_only_generic_parameters(name):
    """A typo in a recipe's defaults or aliases would silently do nothing."""
    r = recipes.get(name)
    known = set(GENERIC.all())
    assert set(r.defaults) <= known, set(r.defaults) - known
    assert set(r.aliases.values()) <= known, set(r.aliases.values()) - known
    assert set(r.aliases) <= set(r.surface), "an alias for a key the recipe never reads"


@pytest.mark.parametrize("name", ["volcano", "ma_plot"])
def test_recipe_defaults_equal_the_domain_schema_defaults(name):
    """Drawn through the recipe with nothing set, every domain key has the value
    the domain renderer documents -- so recipes.render() alone draws the same plot."""
    from fig_atlas.schema import CODE_DEFAULT
    import fig_atlas_omics.renderers as pack
    r = recipes.get(name)
    domain = getattr(pack, f"render_{name}").SCHEMA.all()
    effective = r.params({})
    for k in r.surface:
        d = domain[k].default
        if d is CODE_DEFAULT:
            continue
        assert effective.get(r.aliases.get(k, k)) == d, f"{name}.{k}: recipe gives {effective.get(r.aliases.get(k, k))!r}, schema says {d!r}"


def test_params_translate_names_and_keep_out_unused_keys():
    r = recipes.get("volcano")
    p = r.params({"log2fc_threshold": 2.0, "annotation_mode": "top_n", "tick_label_size": 7, "dot_size": 5})
    assert p["effect_threshold"] == 2.0 and p["label_mode"] == "top_n" and p["dot_size"] == 5
    assert p["tick_label_size"] is None and "log2fc_threshold" not in p   # the volcano never used the 7
    assert p["x_col"] == "log2FC" and p["y_transform"] == "neg_log10"      # recipe defaults


def test_a_recipe_without_surface_passes_everything():
    r = recipes.recipe("free", "fig_atlas.renderers.threshold_scatter:render_threshold_scatter",
                       defaults={"x_col": "a"}, aliases={"thr": "effect_threshold"})
    p = r.params({"thr": 3, "y_col": "b"})
    assert {k: p[k] for k in ("x_col", "effect_threshold", "y_col")} == {"x_col": "a", "effect_threshold": 3, "y_col": "b"}
    assert p["sig_threshold"] == 0.05                     # the generic schema default fills the rest


def test_reads_are_tracked_and_attributed_to_the_domain_renderer():
    owner = "test:recipes"
    for store in (config_usage.READ, config_usage.MISSED, config_usage.DEFAULTS, config_usage.READERS):
        store.pop(owner, None)
    fig, ax = plt.subplots()
    try:
        render_volcano(ax, _df(), config_usage.TrackingDict({"log2fc_threshold": 0.5}, owner))
    finally:
        plt.close(fig)
    assert "log2fc_threshold" in config_usage.READ[owner]
    assert "annotation_mode" in config_usage.MISSED[owner]
    assert config_usage.READERS[owner]["annotation_mode"] == "volcano"
    assert "tick_label_size" not in config_usage.MISSED[owner]


def test_render_by_name_returns_the_classes():
    fig, ax = plt.subplots()
    try:
        out = recipes.render("volcano", ax, _df(), params={"log2fc_threshold": 1.0})
    finally:
        plt.close(fig)
    assert set(out["regulation"]) <= {"up", "down", "ns"} and (out["regulation"] != "ns").any()


def test_two_recipes_with_one_name_is_an_error(monkeypatch):
    a = recipes.recipe("x", "m:f", defaults={"a": 1})
    b = recipes.recipe("x", "m:f", defaults={"a": 2})
    p = plugins.Plugin("recipes", "p", "m:R", "d")
    monkeypatch.setattr(plugins, "load_all", lambda group: [(p, [a]), (p, [b])])
    with pytest.raises(ValueError, match="defined twice"):
        recipes.all_recipes()
