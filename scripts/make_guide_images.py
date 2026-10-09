"""Regenerate the pictures of the researcher guide (docs/guide/img/).

    python scripts/make_guide_images.py

Builds the example project of docs/tutorials/first_figure.md in a temporary
copy of the repository and keeps what the guide shows: the first figure, the
same figure after a config change, and the preflight overlay. Run it again
whenever the renderers or the skeleton change, so the guide never shows an
outdated picture.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "guide" / "img"
WIDTH = 1400                                   # px; the pages show them at column width


def _repo_copy(dest: Path) -> None:
    """A new project repository as `fa init` makes it, plus the example bundles."""
    from fig_atlas.repo_commands import plan_init
    plan_init(dest).apply()
    shutil.copytree(ROOT / "examples", dest / "examples", ignore=shutil.ignore_patterns("__pycache__"))


def _fa(repo: Path, *args: str, check: bool = True) -> None:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    res = subprocess.run([sys.executable, "-m", "fig_atlas", *args], cwd=repo, env=env, capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise SystemExit(f"fa {' '.join(args)} failed:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")


def _keep(src: Path, name: str) -> None:
    from PIL import Image
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > WIDTH:
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(IMG / name, optimize=True)
    print(f"wrote docs/guide/img/{name}")


def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _repo_copy(repo)
        _fa(repo, "new", "project", "first-figure")
        for bundle in ("dose_response", "screen_hits"):
            _fa(repo, "ingest", "bundle", f"examples/{bundle}", "--project", "first-figure", "--no-build")
        _fa(repo, "build", "first-figure", "--preflight")
        figure = repo / "outputs" / "first-figure" / "figures" / "figure_01_main" / "figure_01.png"
        _keep(figure, "first-figure.png")
        # Chapter 7: a problem preflight can point at -- a panel title too long for its panel, on purpose.
        cfg = repo / "configs" / "config_first-figure.yaml"
        original = cfg.read_text(encoding="utf-8")
        cfg.write_text(original.replace('labels_title: "Viability after 48 h"',
                                        'labels_title: "Viability of three compounds after 48 h of continuous exposure"',
                                        1), encoding="utf-8")
        _fa(repo, "build", "first-figure", "--preflight", check=False)
        overlay = sorted((repo / "outputs" / "preflight" / "first-figure").glob("*.png"))
        if overlay:
            _keep(overlay[0], "preflight-overlay.png")
        cfg.write_text(original, encoding="utf-8")

        # The config change chapter 5 walks through: colour-blind-safe colours, panel b's title at
        # panel a's size, fewer point labels.
        text = cfg.read_text(encoding="utf-8")
        text = text.replace("    group_colors: {}", '    group_colors: {"compound A": "#0072B2", '
                                                 '"compound B": "#E69F00", vehicle: "#999999"}', 1)
        text = text.replace("    label_top_n: 6 ", "    label_top_n: 3 ", 1)
        text = text.replace("    title_size: 10 ", "    title_size: 8 ", 1)    # panel b, matched to panel a
        cfg.write_text(text, encoding="utf-8")
        _fa(repo, "build", "first-figure", "--preflight")
        _keep(figure, "after-config.png")


if __name__ == "__main__":
    main()
