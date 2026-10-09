from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import ProjectConfig


def _display_path(path: Path, root: Path) -> str:
    """Path relative to ``root`` when possible, else the absolute path."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def verify_atlas(config: ProjectConfig) -> list[dict[str, str]]:
    """Check that all figure folders, format files, and README files exist and are non-empty."""
    rows: list[dict[str, str]] = []

    for number in range(1, config.figure_count + 1):
        matches = sorted(config.figures_root.glob(f"figure_{number:02d}_*"))
        if len(matches) != 1:
            rows.append({
                "kind": "figure_folder",
                "id": f"figure_{number:02d}",
                "status": "FAIL",
                "detail": f"{len(matches)} matching folders found (expected 1)",
                "path": "",
                "bytes": "",
            })
            continue

        folder = matches[0]
        for fmt in config.formats:
            path = folder / f"figure_{number:02d}.{fmt}"
            rows.append({
                "kind": "figure_file",
                "id": f"figure_{number:02d}.{fmt}",
                "path": _display_path(path, config.project_root),
                "bytes": str(path.stat().st_size if path.exists() else 0),
                "status": "PASS" if path.exists() and path.stat().st_size > 0 else "FAIL",
                "detail": "",
            })

        readme = folder / "README.md"
        text = readme.read_text(encoding="utf-8") if readme.exists() else ""
        has_notes = "Panel-level analysis notes" in text
        rows.append({
            "kind": "figure_readme",
            "id": f"figure_{number:02d}",
            "path": _display_path(readme, config.project_root) if readme.exists() else "",
            "bytes": str(readme.stat().st_size if readme.exists() else 0),
            "status": "PASS" if has_notes else "FAIL",
            "detail": "ok" if has_notes else "missing Panel-level analysis notes section",
        })
        # Live numbers: a {name} placeholder left in the legend text means the
        # build recorded no value for it (fig_atlas.claims).
        from .claims import placeholders
        legend = text.split("## Provenance")[0].split("## Published files")[0]
        for name in sorted(set(placeholders(legend))):
            rows.append({
                "kind": "live_number", "id": f"figure_{number:02d}:{name}",
                "path": _display_path(readme, config.project_root), "bytes": "", "status": "FAIL",
                "detail": f"placeholder {{{name}}} has no recorded value; record it in the analysis script with "
                          f"fig_atlas.claims.record('{name}', value) and rebuild",
            })
        record = folder / f"figure_{number:02d}.provenance.json"
        try:
            rec = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else {}
        except ValueError:
            rec = {}
        tables = rec.get("statistics_tables")
        if tables is not None:
            rows.extend(_recorded_table_rows(tables, number, config))
        else:
            rows.extend(_statistics_table_rows(text, number, config))
        rows.extend(_source_data_rows(rec.get("source_data") or [], number, config))
        rows.extend(_image_rows(rec.get("images") or [], number, config))

    rows.extend(_preflight_rows(config))
    rows.extend(_provenance_rows(config))
    return rows


def _provenance_rows(config: ProjectConfig) -> list[dict[str, str]]:
    """WARN for each published figure whose recorded inputs, code or config
    have changed since it was built (provenance record present only)."""
    from .provenance import HashCache, check_freshness, published_records
    rows = []
    cache = HashCache(config.project_root)
    for rec_path, rec in published_records(config.project_root, config.figures_root):
        reasons = check_freshness(config.project_root, rec, cache)
        if reasons:
            rows.append({"kind": "provenance", "id": rec_path.parent.name,
                         "path": _display_path(rec_path, config.project_root), "bytes": "", "status": "WARN",
                         "detail": "stale -- " + "; ".join(reasons[:3]) + (" ..." if len(reasons) > 3 else "")})
    cache.save()
    return rows


def _preflight_rows(config: ProjectConfig) -> list[dict[str, str]]:
    """Fold the project's last `fa preflight` results into the report.

    Nothing is added if preflight never ran for the project. Error findings
    become WARN rows (``preflight.mode: report``, the default) or FAIL rows
    (``preflight.mode: enforce``); warnings are summarised in one WARN row;
    results older than the published figures are flagged as stale.
    """
    path = config.manifests_root / "preflight.csv"
    if not path.is_file():
        return []
    mode = str((config._raw.get("preflight", {}) or {}).get("mode", "report")).lower()
    with path.open(encoding="utf-8", newline="") as fh:
        findings = list(csv.DictReader(fh))
    shown = _display_path(path, config.project_root)
    rows: list[dict[str, str]] = []
    figures = [f for f in config.figures_root.glob("figure_*/figure_*.*") if f.is_file()]
    if figures and max(f.stat().st_mtime for f in figures) > path.stat().st_mtime:
        rows.append({"kind": "preflight", "id": "stale", "path": shown, "bytes": "", "status": "WARN",
                     "detail": "preflight results are older than the published figures; run `fa preflight --projects "
                               f"{config.project_name}` (or `fa build --preflight`)"})
    for f in findings:
        if f.get("severity") == "error":
            rows.append({"kind": "preflight", "id": f"{f.get('figure', '')}:{f.get('check', '')}", "path": shown,
                         "bytes": "", "status": "FAIL" if mode == "enforce" else "WARN",
                         "detail": f.get("message", "")})
    n_warn = sum(1 for f in findings if f.get("severity") == "warn")
    if n_warn:
        rows.append({"kind": "preflight", "id": "warnings", "path": shown, "bytes": "", "status": "WARN",
                     "detail": f"{n_warn} preflight warning(s); see {shown}"})
    if not rows:
        rows.append({"kind": "preflight", "id": "summary", "path": shown, "bytes": "", "status": "PASS",
                     "detail": "no preflight errors or warnings"})
    return rows


def _source_data_rows(entries: list[dict], number: int, config: ProjectConfig) -> list[dict[str, str]]:
    """Each published source-data table (fig_atlas.source_data) must be there
    and match the hash the build recorded."""
    import hashlib
    rows = []
    for e in entries:
        path = config.project_root / e.get("published", e["path"])
        ok = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == e.get("sha256")
        rows.append({
            "kind": "source_data", "id": f"figure_{number:02d}:panel_{e['panel']}", "path": e.get("published", e["path"]),
            "bytes": str(path.stat().st_size if path.is_file() else 0), "status": "PASS" if ok else "FAIL",
            "detail": f"{e['rows']} rows" if ok else ("missing" if not path.is_file() else "differs from the recorded hash"),
        })
    return rows


def _image_rows(entries: list[dict], number: int, config: ProjectConfig) -> list[dict[str, str]]:
    """Image panels (fig_atlas.images): each source file must still be the one
    the figure was built from (FAIL if changed or gone), and a nonlinear
    adjustment (gamma != 1) is a WARN -- journals ask for it to be stated."""
    import hashlib
    rows = []
    for e in entries:
        ident = f"figure_{number:02d}:panel_{e.get('panel') or '?'}"
        for c in e.get("channels", []):
            p = config.project_root / c["path"]
            ok = p.is_file() and (c.get("sha256") is None or hashlib.sha256(p.read_bytes()).hexdigest() == c["sha256"])
            rows.append({"kind": "image", "id": ident, "path": c["path"],
                         "bytes": str(p.stat().st_size if p.is_file() else 0), "status": "PASS" if ok else "FAIL",
                         "detail": "source image unchanged" if ok else "source image missing or changed since the build"})
        if e.get("nonlinear"):
            rows.append({"kind": "image", "id": ident, "path": e["channels"][0]["path"] if e.get("channels") else "",
                         "bytes": "", "status": "WARN",
                         "detail": f"nonlinear adjustment (gamma {e.get('gamma'):g}); state it in the figure legend"})
    return rows


def _recorded_table_rows(tables: list[dict], number: int, config: ProjectConfig) -> list[dict[str, str]]:
    """Statistics tables from the published provenance record (declared in
    the spec + listed by the data bundles read). Present tables PASS; a
    declared one that is missing WARNs; tables a bundle's metadata lists but
    the upstream exporter never shipped are summarised in one WARN."""
    rows: list[dict[str, str]] = []
    undelivered = []
    for t in tables:
        if t.get("source") == "bundle" and not t.get("exists"):
            undelivered.append(t["path"])
            continue
        path = config.project_root / t["path"]
        if t.get("source") == "stats_layer":
            # Written by the build itself (fig_atlas.stats): missing means a broken publish.
            ok = path.is_file() and path.stat().st_size > 0
            rows.append({
                "kind": "statistics_table", "id": f"figure_{number:02d}", "path": t["path"],
                "bytes": str(path.stat().st_size if path.is_file() else 0),
                "status": "PASS" if ok else "FAIL",
                "detail": "ok (tests run by the build)" if ok else "test table written by the build is missing",
            })
            continue
        rows.append({
            "kind": "statistics_table", "id": f"figure_{number:02d}", "path": t["path"],
            "bytes": str(path.stat().st_size if path.is_file() else 0),
            "status": "PASS" if t.get("exists") else "WARN",
            "detail": ("ok" if t.get("exists") else "declared statistics table not found (or empty)")
            + ("" if t.get("source") == "declared" else " (from the data bundle)"),
        })
    if undelivered:
        rows.append({
            "kind": "statistics_table", "id": f"figure_{number:02d}", "path": undelivered[0], "bytes": "0",
            "status": "WARN",
            "detail": f"{len(undelivered)} statistics table(s) listed in data-bundle metadata were not delivered "
                      "with the bundle (upstream exporter); the figure's numbers come from the bundle inputs",
        })
    return rows


def _statistics_table_rows(readme_text: str, number: int, config: ProjectConfig) -> list[dict[str, str]]:
    """One row per statistics table the published README lists.

    Paths are FigureSpec.statistics_tables entries, relative to the repo root.
    A missing table is reported as WARN rather than FAIL for now: no paper
    project declares tables yet, so there is no settled contract for where
    they are written, and a hard failure would only break the example build.
    """
    rows: list[dict[str, str]] = []
    in_section = False
    for line in readme_text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Statistics and supplementary tables"
            continue
        if not (in_section and line.startswith("- `") and line.rstrip().endswith("`")):
            continue
        rel = line.strip()[3:-1]
        path = config.project_root / rel
        ok = path.is_file() and path.stat().st_size > 0
        rows.append({
            "kind": "statistics_table",
            "id": f"figure_{number:02d}",
            "path": rel,
            "bytes": str(path.stat().st_size if path.is_file() else 0),
            "status": "PASS" if ok else "WARN",
            "detail": "ok" if ok else "declared statistics table not found (or empty)",
        })
    return rows


def write_report(rows: list[dict[str, str]], out_path: Path) -> int:
    """Write CSV report and return the number of failures (WARN rows don't count)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["kind", "id", "path", "bytes", "status", "detail"]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return sum(1 for row in rows if row["status"] == "FAIL")
