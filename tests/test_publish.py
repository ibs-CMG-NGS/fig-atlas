"""publish(): resolves source_stem under output_root, copies, writes README."""

from __future__ import annotations

import pytest

from fig_atlas import FigureSpec, publish
from conftest import make_sources


def _spec() -> FigureSpec:
    return FigureSpec(
        number=1,
        slug="demo",
        title="Demo figure",
        source_stem="figures/fig1",
        primary_code="analysis/demo.py",
        panel_notes=["Panel a: something."],
    )


def test_publish_raises_when_source_missing(make_config):
    config = make_config()
    with pytest.raises(FileNotFoundError):
        publish(_spec(), config)


def test_publish_copies_all_formats_and_writes_readme(make_config):
    config = make_config()
    make_sources(config, "figures/fig1")

    result = publish(_spec(), config)

    out_dir = config.figures_root / "figure_01_demo"
    for fmt in config.formats:
        published = out_dir / f"figure_01.{fmt}"
        assert published.exists() and published.stat().st_size > 0
    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    assert "Panel-level analysis notes" in readme
    assert "Panel a: something." in readme
    assert result["title"] == "Demo figure"


def test_publish_resolves_stem_under_external_output_root(make_config, monkeypatch, tmp_path):
    external = tmp_path / "ext_out"
    monkeypatch.setenv("OUTPUT_ROOT", str(external))
    config = make_config()
    make_sources(config, "figures/fig1")  # writes under external OUTPUT_ROOT

    result = publish(_spec(), config)

    assert (external / "testproj" / "figures" / "figure_01_demo" / "figure_01.png").exists()
    # Path outside the project root is reported as an absolute string, not a crash.
    assert result["png"]


def _bundle(root, rel: str, table_exists: bool) -> str:
    """A data bundle whose metadata lists inputs/statistics.csv; returns its data file."""
    b = root / rel
    (b / "inputs").mkdir(parents=True)
    (b / "metadata").mkdir()
    (b / "inputs" / "data.csv").write_text("x\n1\n")
    (b / "metadata" / "metadata.yaml").write_text(
        "app_version: exporter-1\nplot_type: volcano\nstatistics_tables:\n  - inputs/statistics.csv\n")
    if table_exists:
        (b / "inputs" / "statistics.csv").write_text("test,p\nwelch,0.01\n")
    return f"{rel}/inputs/data.csv"


def test_publish_adds_bundle_statistics_tables_and_upstream(make_config):
    import json
    from fig_atlas import verify_atlas
    config = make_config()
    root = config.project_root
    make_sources(config, "figures/fig1")
    shipped = _bundle(root, "raw_data/s/with_stats", True)
    unshipped = _bundle(root, "raw_data/s/without_stats", False)
    (root / "tables").mkdir()
    (root / "tables" / "declared.csv").write_text("a\n1\n")
    rec = {"inputs": [{"path": p, "sha256": "x", "bundle": {"bundle": p.rsplit("/inputs", 1)[0],
                                                             "app_version": "exporter-1", "plot_type": "volcano"}}
                      for p in (shipped, unshipped)],
           "run": {}, "git": {}, "config": {}, "environment": {}}
    (config.output_root / "figures" / "fig1.provenance.json").write_text(json.dumps(rec))
    spec = FigureSpec(number=1, slug="demo", title="Demo", source_stem="figures/fig1",
                      primary_code="analysis/demo.py", panel_notes=["a"], statistics_tables=["tables/declared.csv"])
    publish(spec, config)

    out = config.figures_root / "figure_01_demo"
    tables = {t["path"]: t for t in json.loads((out / "figure_01.provenance.json").read_text())["statistics_tables"]}
    assert tables["tables/declared.csv"]["source"] == "declared" and tables["tables/declared.csv"]["exists"]
    assert tables["raw_data/s/with_stats/inputs/statistics.csv"]["exists"]
    assert not tables["raw_data/s/without_stats/inputs/statistics.csv"]["exists"]
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "- `raw_data/s/with_stats/inputs/statistics.csv`  (from the data bundle)" in readme
    assert "Not delivered: 1 statistics table(s)" in readme
    assert "| `raw_data/s/with_stats` | exporter-1 | volcano |" in readme
    assert "\n\n\n" not in readme

    rows = [r for r in verify_atlas(config) if r["kind"] == "statistics_table"]
    assert sorted(r["status"] for r in rows) == ["PASS", "PASS", "WARN"]
    assert "1 statistics table(s) listed in data-bundle metadata were not delivered" in \
        next(r for r in rows if r["status"] == "WARN")["detail"]


def test_publish_uses_project_readme_template(make_config):
    config = make_config()
    make_sources(config, "figures/fig1")
    tpl = config.project_root / "templates" / "lab_README.md"
    tpl.parent.mkdir()
    tpl.write_text("# ${title} (lab format)\n\n${panel_notes}\n\n${statistics}\n\nFiles:\n${published_files}\n")
    config._raw["publish"] = {"readme_template": "templates/lab_README.md"}
    publish(_spec(), config)
    readme = (config.figures_root / "figure_01_demo" / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Demo figure (lab format)\n\n- Panel a: something.\n\nFiles:\n- `")
