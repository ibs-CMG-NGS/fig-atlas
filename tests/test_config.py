"""ProjectConfig path resolution: defaults, namespacing, env overrides."""

from __future__ import annotations

from pathlib import Path


def test_output_root_defaults_to_outputs(make_config):
    config = make_config()
    assert config.output_root == config.project_root / "outputs"


def test_unset_env_placeholder_falls_back_to_outputs(make_config):
    # A literal ${OUTPUT_ROOT} with no such env var must not leak through.
    config = make_config(extra_paths={"output_root": "${OUTPUT_ROOT}"})
    assert config.output_root == config.project_root / "outputs"


def test_output_root_env_override(make_config, monkeypatch, tmp_path):
    external = tmp_path / "elsewhere"
    monkeypatch.setenv("OUTPUT_ROOT", str(external))
    config = make_config()
    assert config.output_root == external


def test_figures_and_manifests_are_namespaced_by_project(make_config):
    config = make_config(project={"name": "myproj"})
    base = config.project_root / "outputs" / "myproj"
    assert config.figures_root == base / "figures"
    assert config.manifests_root == base / "manifests"
    assert config.supplementary_root == base / "supplementary_tables"


def test_explicit_roots_win_over_defaults(make_config):
    config = make_config(extra_paths={"figures_root": "custom/figs"})
    assert config.figures_root == config.project_root / "custom" / "figs"


def test_resolve_keeps_absolute_and_anchors_relative(make_config):
    config = make_config()
    abs_path = Path.cwd().resolve().anchor + "abs_dir"
    assert config._resolve(abs_path) == Path(abs_path)
    assert config._resolve("rel/dir") == config.project_root / "rel" / "dir"


def test_raw_root_relative_is_anchored_at_project_root(make_config):
    # No project_root / raw_root double-join needed by callers.
    config = make_config(extra_paths={"raw_root": "raw_data/foo"})
    assert config.raw_root == config.project_root / "raw_data" / "foo"


def test_raw_root_env_override_absolute(make_config, monkeypatch, tmp_path):
    external = tmp_path / "external_raw"
    monkeypatch.setenv("RAW_ROOT", str(external))
    config = make_config(extra_paths={"raw_root": "raw_data/foo"})
    assert config.raw_root == external
