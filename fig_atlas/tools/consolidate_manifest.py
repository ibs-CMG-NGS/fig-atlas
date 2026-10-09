"""Consolidate all per-project clean_atlas_manifest.csv files into outputs/clean_atlas_manifest.csv."""

import csv
import sys
from pathlib import Path
from fig_atlas.tools import project_root  # noqa: E402  (the project repository, not this package)

ROOT = project_root()
OUTPUTS = ROOT / "outputs"
sys.path.insert(0, str(ROOT))

from fig_atlas.provenance import build_index  # noqa: E402

# Columns added from each figure's provenance record (outputs/provenance_index.json).
PROVENANCE_COLUMNS = ["provenance", "built", "commit", "inputs", "bundles", "statistics_tables", "fresh"]


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: set[str]) -> None:
    fields = ["project"] + [f for f in sorted(fieldnames) if f != "project"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def active_projects() -> set[str]:
    """Projects that still have a live config: configs/**/config_<name>.yaml,
    excluding anything under an archive/ folder (retired per CLAUDE.md §5.3)."""
    return {
        p.stem[len("config_"):]
        for p in (ROOT / "configs").rglob("config_*.yaml")
        if "archive" not in p.relative_to(ROOT / "configs").parts
    }


def main() -> None:
    # Recursive: finds per-project manifests whether the project's output dir
    # sits flat under outputs/<project>/ or namespaced under
    # outputs/<domain>/<category>/<project>/.
    manifest_files = sorted(OUTPUTS.glob("**/manifests/clean_atlas_manifest.csv"))
    all_rows: list[dict[str, str]] = []
    fieldnames: set[str] = set()
    by_domain: dict[str, list[dict[str, str]]] = {}
    # Output folders outlive their projects (outputs/ is never pruned), so a
    # retired or renamed project's old manifest would otherwise keep showing up
    # here with stale paths. Only projects with a live config are listed.
    active = active_projects()
    orphans: list[str] = []
    index = build_index(ROOT)["figures"]

    for mf in manifest_files:
        # Project dir is always exactly 2 levels above its own manifest file,
        # regardless of how deeply that project dir itself is nested.
        project_dir = mf.parent.parent
        project_name = project_dir.name
        if project_name not in active:
            orphans.append(str(project_dir.relative_to(ROOT)).replace("\\", "/"))
            continue
        rel_parts = project_dir.relative_to(OUTPUTS).parts
        domain = rel_parts[0] if len(rel_parts) > 1 else None

        with mf.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                fieldnames.update(reader.fieldnames)
            for row in reader:
                row.pop(None, None)
                row["project"] = project_name
                rec = index.get((row.get("folder") or "").replace("\\", "/"))
                row.update(dict.fromkeys(PROVENANCE_COLUMNS, ""))
                if rec:
                    row.update(provenance=rec["record"], built=rec["built"] or "", commit=rec["commit"],
                               inputs=str(len(rec["inputs"])), bundles=str(len(rec["bundles"])),
                               statistics_tables=str(len(rec["statistics_tables"])),
                               fresh="yes" if not rec["stale_reasons"] else "no: " + "; ".join(rec["stale_reasons"][:3]))
                fieldnames.update(PROVENANCE_COLUMNS)
                all_rows.append(row)
                if domain:
                    by_domain.setdefault(domain, []).append(row)

    if not all_rows:
        print("No per-project manifests found.")
        return

    master_path = OUTPUTS / "clean_atlas_manifest.csv"
    _write_csv(master_path, all_rows, fieldnames)
    print(f"Successfully consolidated {len(all_rows)} figure entries across "
          f"{len(manifest_files) - len(orphans)} projects into:")
    print(f"  {master_path}")
    # Every number a published figure recorded for its legend (fig_atlas.claims):
    # one place to check the manuscript text against.
    claim_rows = [{"figure": folder, "name": name, "value": v.get("value"), "source": v.get("source", "")}
                  for folder, rec in sorted(index.items())
                  if folder.split("/figures/")[0].rsplit("/", 1)[-1] in active
                  for name, v in sorted(rec.get("claims", {}).items())]
    claims_path = OUTPUTS / "claims_index.csv"
    with claims_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure", "name", "value", "source"])
        w.writeheader()
        w.writerows(claim_rows)
    print(f"  {claims_path.relative_to(ROOT)}: {len(claim_rows)} recorded number(s) in "
          f"{len({r['figure'] for r in claim_rows})} figure(s)")
    with_rec = sum(1 for r in all_rows if r.get("provenance"))
    stale = sum(1 for r in all_rows if r.get("fresh", "").startswith("no"))
    print(f"  provenance: {with_rec}/{len(all_rows)} figures recorded, {stale} stale "
          f"(index: {OUTPUTS.relative_to(ROOT) / 'provenance_index.json'})")
    if orphans:
        print(f"Skipped {len(orphans)} orphaned output folder(s) with no live config (retired/renamed):")
        for o in orphans:
            print(f"  {o}")

    for domain, rows in sorted(by_domain.items()):
        domain_path = OUTPUTS / domain / "manifest.csv"
        _write_csv(domain_path, rows, fieldnames)
        print(f"  {domain_path} ({len(rows)} entries)")


if __name__ == "__main__":
    main()
