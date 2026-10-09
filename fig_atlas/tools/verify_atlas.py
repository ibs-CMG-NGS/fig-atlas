"""Verify that all figure folders, format files, and panel READMEs are present."""

from __future__ import annotations

import sys
from pathlib import Path
from fig_atlas.tools import project_root  # noqa: E402  (the project repository, not this package)

sys.path.insert(0, str(project_root()))

from fig_atlas import get_config, verify_atlas, write_report

CONFIG = get_config()


def _display(path: Path) -> str:
    """Path relative to the project root when possible, else absolute."""
    try:
        return str(path.relative_to(CONFIG.project_root))
    except ValueError:
        return str(path)


def main() -> int:
    rows = verify_atlas(CONFIG)
    out_path = CONFIG.manifests_root / "clean_atlas_verification.csv"
    failures = write_report(rows, out_path)
    total = len(rows)
    warnings = [row for row in rows if row["status"] == "WARN"]

    if failures:
        print(f"FAIL: {failures}/{total} checks failed - see {_display(out_path)}")
        for row in rows:
            if row["status"] != "PASS":
                print(f"  [{row['kind']}] {row['id']}: {row['detail']}")
        return 1

    passed = total - len(warnings)
    print(f"PASS: {passed}/{total} checks passed"
          + (f", {len(warnings)} warning(s)" if warnings else "") + f" - {_display(out_path)}")
    for row in warnings:
        print(f"  WARN [{row['kind']}] {row['id']}: {row['detail']} ({row['path']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
