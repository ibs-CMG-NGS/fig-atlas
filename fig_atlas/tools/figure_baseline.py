"""Record and check output hashes of the storyline compendium figures.

Builds are reproducible (./matplotlibrc + SOURCE_DATE_EPOCH), so an unchanged
figure rebuilds to byte-identical files. This keeps a baseline of every file
the compendium projects publish and reports which ones changed after a
rebuild -- the regression check for refactors, dependency upgrades and
renderer changes (roadmap Phase 0).

Hashes depend on the local environment (fonts, FreeType, library versions)
and on the private raw data, so the baseline is a per-machine record: commit
it as the reference for this environment, and re-record it after an intended
change or an environment upgrade.

Reading a report: PNGs are compared by decoded pixels as well as file bytes.
VISIBLE = a PNG whose pixels changed (the figure looks different; exit 1).
FILE = bytes changed but pixels did not -- e.g. matplotlib writes its version
into every PNG and PDF, so a library upgrade alone changes all file hashes --
or a PDF/SVG beside an unchanged PNG (exit 0, re-record when intended).

Usage:
    python scripts/figure_baseline.py record [--build]   # write docs/baselines/compendium_outputs.json
    python scripts/figure_baseline.py check  [--build]   # compare current outputs with it (exit 1 on change)
    fa baseline check --build --projects <project>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path
from fig_atlas.tools import project_root  # noqa: E402  (the project repository, not this package)

ROOT = project_root()
sys.path.insert(0, str(ROOT))

from fig_atlas.projects import ProjectError, build_project, find_project  # noqa: E402
BASELINE = ROOT / "docs" / "baselines" / "compendium_outputs.json"
STORYLINES = sorted((ROOT / "docs" / "storylines").glob("figure_plan_*.md"))


def compendium_projects() -> list[str]:
    spec = importlib.util.spec_from_file_location("compile_storyline_pdf", Path(__file__).with_name("compile_storyline_pdf.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seen: dict[str, None] = {}
    for md in STORYLINES:
        for f in mod.parse_storyline_md(md)["figures"]:
            seen.setdefault(f["project"], None)
    return list(seen)


def find_config(project: str) -> Path:
    try:
        return find_project(ROOT, project).config
    except ProjectError as exc:
        raise SystemExit(str(exc)) from exc


def build(project: str) -> None:
    """analysis -> publish -> verify (the same steps as `fa build`)."""
    r = build_project(ROOT, find_project(ROOT, project), capture=True)
    if not r.ok:
        raise SystemExit(f"[{project}] {r.failed_step} failed:\n{r.output_tail}")
    print(f"  built {project}")


def png_pixels_sha256(path: Path) -> str:
    """Hash of a PNG's decoded pixels, ignoring its metadata chunks (matplotlib
    writes its own version into the PNG, so the file hash changes on every
    upgrade even when not a single pixel does)."""
    import numpy as np
    from matplotlib.image import imread
    arr = np.ascontiguousarray(imread(path))
    return hashlib.sha256(str(arr.shape).encode() + arr.tobytes()).hexdigest()


def published_files(project: str) -> dict[str, dict]:
    """Relative path -> {"sha256", and "pixels" for PNGs} of every figure file the project published."""
    sys.path.insert(0, str(ROOT))
    from fig_atlas import get_config
    figures_root = get_config(find_config(project)).figures_root
    out = {}
    for p in sorted(figures_root.glob("figure_*/figure_*.*")):
        if p.suffix.lower() in {".png", ".pdf", ".svg"}:
            rec = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            if p.suffix.lower() == ".png":
                rec["pixels"] = png_pixels_sha256(p)
            out[p.relative_to(ROOT).as_posix()] = rec
    return out


def environment() -> dict:
    import matplotlib
    from matplotlib import ft2font
    return {"python": platform.python_version(), "platform": platform.platform(terse=True),
            "matplotlib": matplotlib.__version__,
            "freetype": getattr(ft2font, "__freetype_version__", "unknown")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["record", "check"])
    ap.add_argument("--build", action="store_true", help="rebuild the projects first")
    ap.add_argument("--projects", nargs="*", help="limit to these projects (default: the compendium)")
    args = ap.parse_args()

    projects = args.projects or compendium_projects()
    if args.build:
        print(f"Building {len(projects)} project(s)...")
        for p in projects:
            build(p)
    current = {p: published_files(p) for p in projects}

    if args.action == "record":
        data = {"note": "Per-machine reference; see scripts/figure_baseline.py.",
                "environment": environment(), "projects": current}
        if BASELINE.exists() and args.projects:   # partial record: keep the other projects
            old = json.loads(BASELINE.read_text(encoding="utf-8"))
            data["projects"] = {**old.get("projects", {}), **current}
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        n = sum(len(v) for v in current.values())
        print(f"Recorded {n} files from {len(projects)} project(s) -> {BASELINE.relative_to(ROOT)}")
        return 0

    if not BASELINE.exists():
        raise SystemExit(f"no baseline yet; run: python scripts/figure_baseline.py record --build")
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    env_now, env_then = environment(), base.get("environment", {})
    if env_now != env_then:
        print(f"[note] environment differs from the baseline's: {env_then} -> {env_now}; "
              f"hash changes may come from the environment rather than the code.")
    visible, file_only, missing, added = [], [], [], []
    for p in projects:
        old, new = base["projects"].get(p, {}), current[p]
        for f in old:
            if f not in new:
                missing.append(f)
                continue
            o, n = old[f], new[f]
            if isinstance(o, str):          # baseline written before pixel hashes existed
                o = {"sha256": o}
            if o["sha256"] == n["sha256"]:
                continue
            if "pixels" in o and o["pixels"] == n.get("pixels"):
                file_only.append(f)         # same pixels: only PNG metadata changed
            elif f.endswith(".png"):
                visible.append(f)
            else:
                file_only.append(f)         # PDF/SVG bytes; judge by the PNG beside it
        added += [f for f in new if f not in old]
    total = sum(len(v) for v in current.values())
    if not (visible or file_only or missing or added):
        print(f"OK: {total} files in {len(projects)} project(s) match the baseline.")
        return 0
    for label, items in (("VISIBLE", visible), ("FILE", file_only), ("MISSING", missing), ("NEW", added)):
        for f in items:
            print(f"{label:8} {f}")
    print(f"\n{len(visible)} PNG with changed pixels (visible change), {len(file_only)} changed in file "
          f"bytes only (metadata/encoding; PDF/SVG beside an unchanged PNG), "
          f"{len(missing)} missing, {len(added)} new.")
    return 1 if (visible or missing or added) else 0


if __name__ == "__main__":
    sys.exit(main())
