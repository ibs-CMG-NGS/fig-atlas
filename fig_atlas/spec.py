from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FigureSpec:
    """Declarative description of one manuscript figure.

    Separates *what* a figure is (metadata, relationships, claim boundary)
    from *how* it is generated (analysis scripts) and *where* it lives (publish).
    """

    number: int
    slug: str
    title: str
    # Path to the source figure stem (without extension), relative to output_root
    # (i.e. OUTPUT_ROOT / paths.output_root, default "outputs"). The publish step
    # expects {output_root}/{source_stem}.png / .pdf / .svg to exist.
    source_stem: str
    # Relative path to the primary analysis script inside the project.
    primary_code: str
    panel_notes: list[str] = field(default_factory=list)
    statistics_tables: list[str] = field(default_factory=list)
    # Optional plain-text note on what this figure does and does not prove.
    claim_boundary: str = ""

    def out_dir(self, figures_root: Path) -> Path:
        return figures_root / f"figure_{self.number:02d}_{self.slug}"
