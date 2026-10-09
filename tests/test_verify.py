"""verify_atlas(): PASS after publish; FAIL on missing files / README."""

from __future__ import annotations

from fig_atlas import FigureSpec, publish, verify_atlas, write_report
from conftest import make_sources


def _spec() -> FigureSpec:
    return FigureSpec(
        number=1, slug="demo", title="Demo",
        source_stem="figures/fig1", primary_code="analysis/demo.py",
        panel_notes=["Panel a."],
    )


def test_verify_all_pass_after_publish(make_config):
    config = make_config()
    make_sources(config, "figures/fig1")
    publish(_spec(), config)

    rows = verify_atlas(config)
    assert rows and all(r["status"] == "PASS" for r in rows)


def test_verify_fails_when_nothing_published(make_config):
    config = make_config()
    rows = verify_atlas(config)
    # No figure folder exists yet -> the folder check must FAIL.
    assert any(r["kind"] == "figure_folder" and r["status"] == "FAIL" for r in rows)


def test_verify_flags_missing_readme_notes(make_config):
    config = make_config()
    make_sources(config, "figures/fig1")
    publish(_spec(), config)
    # Corrupt the README so the required section disappears.
    readme = config.figures_root / "figure_01_demo" / "README.md"
    readme.write_text("# Figure 1\n\nno notes here\n", encoding="utf-8")

    rows = verify_atlas(config)
    assert any(r["kind"] == "figure_readme" and r["status"] == "FAIL" for r in rows)


def test_write_report_counts_failures(make_config, tmp_path):
    config = make_config()
    rows = verify_atlas(config)  # nothing published -> failures present
    report = tmp_path / "report.csv"
    failures = write_report(rows, report)
    assert report.exists()
    assert failures == sum(1 for r in rows if r["status"] == "FAIL")
    assert failures > 0


def test_verify_warns_on_missing_statistics_table(make_config):
    config = make_config()
    make_sources(config, "figures/fig1")
    spec = FigureSpec(
        number=1, slug="demo", title="Demo",
        source_stem="figures/fig1", primary_code="analysis/demo.py",
        panel_notes=["Panel a."],
        statistics_tables=["tables/present.csv", "tables/absent.csv"],
    )
    present = config.project_root / "tables" / "present.csv"
    present.parent.mkdir(parents=True, exist_ok=True)
    present.write_text("a,b\n1,2\n", encoding="utf-8")
    publish(spec, config)

    rows = verify_atlas(config)
    stats = {r["path"]: r["status"] for r in rows if r["kind"] == "statistics_table"}
    assert stats == {"tables/present.csv": "PASS", "tables/absent.csv": "WARN"}
    # A missing table warns but does not fail the build.
    assert write_report(rows, config.project_root / "report.csv") == 0


# ------------------------------------------------- preflight results in verify --
def _published(make_config):
    config = make_config()
    make_sources(config, "figures/fig1")
    publish(_spec(), config)
    return config


def _write_preflight(config, rows):
    import csv
    path = config.manifests_root / "preflight.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["project", "figure", "n", "severity", "check", "message"])
        w.writeheader()
        w.writerows(rows)
    return path


ERROR_ROW = {"project": "testproj", "figure": "fig1", "n": 1, "severity": "error",
             "check": "tick_label_collision", "message": "'a' overlaps 'b'"}


def test_verify_ignores_projects_never_preflighted(make_config):
    rows = verify_atlas(_published(make_config))
    assert not [r for r in rows if r["kind"] == "preflight"]


def test_preflight_error_is_warn_in_report_mode(make_config):
    config = _published(make_config)
    _write_preflight(config, [ERROR_ROW])
    rows = [r for r in verify_atlas(config) if r["kind"] == "preflight"]
    assert [r["status"] for r in rows] == ["WARN"]
    assert write_report(verify_atlas(config), config.project_root / "r.csv") == 0


def test_preflight_error_fails_in_enforce_mode(make_config):
    config = _published(make_config)
    _write_preflight(config, [ERROR_ROW])
    config._raw["preflight"] = {"mode": "enforce"}
    rows = [r for r in verify_atlas(config) if r["kind"] == "preflight"]
    assert [r["status"] for r in rows] == ["FAIL"]
    assert write_report(verify_atlas(config), config.project_root / "r.csv") == 1


def test_stale_preflight_results_are_flagged(make_config):
    import os
    config = _published(make_config)
    path = _write_preflight(config, [])
    old = path.stat().st_mtime - 3600
    os.utime(path, (old, old))                 # results older than the figures
    ids = {r["id"]: r["status"] for r in verify_atlas(config) if r["kind"] == "preflight"}
    assert ids.get("stale") == "WARN"
