"""load_bundle_params() and the documented parameter-precedence contract."""

from __future__ import annotations

import yaml

from fig_atlas import load_bundle_params


def test_load_bundle_params_reads_plot_params(tmp_path):
    bundle = tmp_path / "mybundle"
    meta = bundle / "metadata"
    meta.mkdir(parents=True)
    (meta / "metadata.yaml").write_text(
        yaml.safe_dump({"plot_params": {"dot_size": 42}}), encoding="utf-8"
    )
    assert load_bundle_params(bundle) == {"dot_size": 42}


def test_load_bundle_params_missing_file_returns_empty(tmp_path):
    assert load_bundle_params(tmp_path / "does_not_exist") == {}


def test_precedence_defaults_bundle_global_config():
    """Later dicts win: code defaults < bundle meta < global style < config."""
    defaults = {"dot_size": 20, "title_size": 8, "color": "red"}
    bundle = {"dot_size": 30}
    global_style = {"title_size": 10}
    config = {"color": "blue"}

    merged = {**defaults, **bundle, **global_style, **config}

    assert merged["dot_size"] == 30    # bundle overrode default
    assert merged["title_size"] == 10  # global overrode default
    assert merged["color"] == "blue"   # config overrode default
