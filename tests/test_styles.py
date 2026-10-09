"""Style presets: deep-merged under the config, config wins, list layering."""

from __future__ import annotations

import pytest
import yaml


def _write_preset(root, name, data):
    d = root / "styles"
    d.mkdir(exist_ok=True)
    (d / f"{name}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_preset_fills_missing_and_config_wins(make_config):
    root = make_config.root
    _write_preset(root, "base", {"figures": {"dpi": 300, "tick_label_size": 5,
                                             "font_family": "Arial"}})
    config = make_config(project={"style": "base"})
    fig = config._raw["figures"]
    assert fig["dpi"] == 100          # config's own value wins over the preset
    assert fig["tick_label_size"] == 5  # preset-only key is inherited
    assert fig["font_family"] == "Arial"


def test_preset_list_later_wins(make_config):
    root = make_config.root
    _write_preset(root, "base", {"figures": {"title_size": 10, "font_size": 8}})
    _write_preset(root, "compact", {"figures": {"font_size": 7}})
    config = make_config(project={"style": ["base", "compact"]})
    fig = config._raw["figures"]
    assert fig["title_size"] == 10   # inherited from base
    assert fig["font_size"] == 7     # compact overrides base


def test_missing_preset_raises(make_config):
    with pytest.raises(FileNotFoundError):
        make_config(project={"style": "does_not_exist"})


def test_no_style_key_is_noop(make_config):
    config = make_config()
    assert "style" not in config._raw.get("project", {})
