"""Publish all figures declared in figure_specs/ and write the atlas manifest."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from fig_atlas.tools import project_root  # noqa: E402  (the project repository, not this package)

sys.path.insert(0, str(project_root()))

from fig_atlas import FigureSpec, get_config, publish

CONFIG = get_config()
SPEC_DIR = CONFIG.project_root / "figure_specs"


def _display(path: Path) -> str:
    """Path relative to the project root when possible, else absolute."""
    try:
        return str(path.relative_to(CONFIG.project_root))
    except ValueError:
        return str(path)


def load_specs() -> list[FigureSpec]:
    specs: list[FigureSpec] = []
    pattern = CONFIG._raw.get("project", {}).get("spec_pattern", "figure_*.py")
    for path in sorted(SPEC_DIR.glob(f"**/{pattern}")):
        mod_spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(mod_spec)
        assert mod_spec.loader is not None
        mod_spec.loader.exec_module(module)
        if hasattr(module, "SPEC"):
            specs.append(module.SPEC)
    return specs


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({field for row in rows for field in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    specs = load_specs()
    if not specs:
        print("No FigureSpec found in figure_specs/")
        return 1

    rows: list[dict[str, str]] = []
    for spec in specs:
        rows.append(publish(spec, CONFIG))
        print(f"  Published Figure {spec.number}: {spec.title}")

    manifest = CONFIG.manifests_root / "clean_atlas_manifest.csv"
    write_csv(manifest, rows)
    print(f"Manifest: {_display(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
