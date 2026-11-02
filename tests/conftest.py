"""Shared fixtures: build a throwaway project on disk for the atlas library,
and a figure plus drawing kit for the layout tests (tests/layouts/)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# Make the in-repo fig_atlas package importable without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fig_atlas import ProjectConfig  # noqa: E402


def _write_config(project_root: Path, extra_paths: dict | None = None,
                  project: dict | None = None) -> Path:
    """Write configs/config.yaml under ``project_root`` and return its path."""
    cfg = {
        "project": {"name": "testproj", "figure_count": 1, **(project or {})},
        "paths": {"raw_root": "raw", **(extra_paths or {})},
        "figures": {"dpi": 100, "formats": ["png", "pdf", "svg"]},
    }
    cfg_dir = project_root / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return cfg_path


@pytest.fixture
def make_config(tmp_path, monkeypatch):
    """Factory returning a ProjectConfig rooted at an isolated tmp project.

    Clears RAW_ROOT/OUTPUT_ROOT so tests exercise config-derived defaults unless
    they set the env vars themselves.
    """
    monkeypatch.delenv("RAW_ROOT", raising=False)
    monkeypatch.delenv("OUTPUT_ROOT", raising=False)

    def _factory(extra_paths=None, project=None) -> ProjectConfig:
        cfg_path = _write_config(tmp_path, extra_paths, project)
        return ProjectConfig(cfg_path)

    _factory.root = tmp_path
    return _factory


def make_sources(config, stem: str) -> None:
    """Create non-empty {output_root}/{stem}.{fmt} files a spec can publish."""
    src_stem = config.output_root / stem
    src_stem.parent.mkdir(parents=True, exist_ok=True)
    for fmt in config.formats:
        src_stem.with_suffix(f".{fmt}").write_bytes(b"%stub-" + fmt.encode())


class Kit:
    """Draw into layout cells and inspect what came out (tests/layouts/)."""

    @staticmethod
    def draw(layout, title: str = "panel") -> None:
        """One axes per cell, with a title so the tag has something above it."""
        for cell in layout.cells.values():
            ax = cell.add_subplot(1, 1, 1)
            ax.plot([0, 1], [1, 0])
            ax.set_title(title)

    @staticmethod
    def tags(fig) -> list:
        from fig_atlas.renderers.panels import PANEL_TAG_GID

        return sorted(t.get_text() for t in fig.texts if t.get_gid() == PANEL_TAG_GID)

    @staticmethod
    def bounds(cell) -> list:
        return [cell.bbox.x0, cell.bbox.y0, cell.bbox.width, cell.bbox.height]

    @staticmethod
    def overlap(a, b) -> float:
        """Overlapping area of two cells' bounding boxes (0.0 when apart)."""
        width = min(a.bbox.x1, b.bbox.x1) - max(a.bbox.x0, b.bbox.x0)
        height = min(a.bbox.y1, b.bbox.y1) - max(a.bbox.y0, b.bbox.y0)
        return max(width, 0.0) * max(height, 0.0)


@pytest.fixture
def fig():
    """A blank figure the layout tests draw into (cleaned up afterwards)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(6, 5))
    yield figure
    plt.close(figure)


@pytest.fixture
def kit():
    return Kit
