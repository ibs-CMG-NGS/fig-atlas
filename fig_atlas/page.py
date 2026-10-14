"""Final-print-size page geometry.

A page preset (``styles/page_*.yaml``, or a journal preset later) declares the
printed canvas a figure is drawn at 1:1, so point sizes set in config are the
sizes that actually print. Two equivalent YAML shapes are accepted:

    page:                          page:
      name: "a4_portrait_narrow"     name: "nature_double"
      paper_mm: [210, 297]           content_width_mm: 183
      margin_mm: 12.7                content_height_mm: 247

The first (paper + uniform margin) suits generic paper sizes; the second
(explicit content box) suits journal column widths. A journal preset also
names its column widths (``columns_mm: {"1": 89, "1.5": 120, "2": 183}``), so a
figure states how many columns it spans (``figures.page_columns: 1``) and
gets that journal's width for it; switching journal keeps the span.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

MM_PER_INCH = 25.4


@dataclass(frozen=True)
class PageSpec:
    """The printed area a figure is drawn at 1:1 (mm), from the config's
    ``page:`` block (``ProjectConfig.page``). ``figure_size_in`` gives the
    figure size in inches for ``plt.figure(figsize=...)``."""
    name: str
    content_width_mm: float
    content_height_mm: float
    columns_mm: tuple = ()                 # ((span, width_mm), ...) named column widths, e.g. (("1", 89.0), ...)

    @classmethod
    def from_dict(cls, d: dict) -> "PageSpec":
        name = str(d.get("name", "page"))
        cols = tuple((_span(k), float(v)) for k, v in (d.get("columns_mm") or {}).items())
        if "content_width_mm" in d:
            return cls(name, float(d["content_width_mm"]), float(d["content_height_mm"]), cols)
        paper_w, paper_h = (float(v) for v in d["paper_mm"])
        margin = float(d.get("margin_mm", 0.0))
        return cls(name, paper_w - 2 * margin, paper_h - 2 * margin, cols)

    def column_width_mm(self, span) -> float:
        """Width in mm of a figure spanning ``span`` columns (1, 1.5, 2, ...)
        on this page, from its ``columns_mm``."""
        widths = dict(self.columns_mm)
        key = _span(span)
        if key not in widths:
            named = ", ".join(widths) or "none"
            raise ValueError(f"page '{self.name}' names no {key}-column width (it names: {named}); "
                             f"set figures.page_columns to one of them, or give width_mm instead")
        return widths[key]

    def spanning(self, span) -> "PageSpec":
        """This page narrowed to ``span`` columns: the content width becomes
        that column width, so code sizing a figure to the page's full width
        draws it at the column width instead."""
        return PageSpec(f"{self.name}/{_span(span)}col", self.column_width_mm(span), self.content_height_mm,
                        self.columns_mm)

    @property
    def content_width_in(self) -> float:
        """Width of the printed area, inches."""
        return self.content_width_mm / MM_PER_INCH

    @property
    def content_height_in(self) -> float:
        """Height of the printed area, inches."""
        return self.content_height_mm / MM_PER_INCH

    def figure_size_in(
        self,
        height_mm: float | None = None,
        height_frac: float | None = None,
        width_frac: float = 1.0,
    ) -> tuple[float, float]:
        """(width, height) in inches for a figure drawn on this page.

        Width defaults to the full content width. Height comes from an
        absolute ``height_mm`` or a ``height_frac`` of the content height
        (default: the full content height). A height taller than the page is
        rejected rather than silently allowed: such a figure can only be
        printed by shrinking it (breaking the 1:1 point sizes) or by splitting
        it across pages, and that choice belongs to the figure, not here.
        """
        width_mm = self.content_width_mm * width_frac
        if height_mm is None:
            height_mm = self.content_height_mm * (1.0 if height_frac is None else height_frac)
        if height_mm > self.content_height_mm + 1e-6:
            raise ValueError(
                f"Figure height {height_mm:.1f} mm exceeds page '{self.name}' content "
                f"height {self.content_height_mm:.1f} mm -- split the figure across "
                f"pages or reduce its content."
            )
        return width_mm / MM_PER_INCH, height_mm / MM_PER_INCH


def _span(v) -> str:
    """A column span as a key: 1, 1.0 and "1" -> "1"; 1.5 -> "1.5"."""
    return f"{float(v):g}"


def save_page_figure(fig, path, pad_mm: float = 0.5, **kwargs) -> None:
    """Save ``fig`` at exactly its canvas width, trimmed only vertically.

    ``bbox_inches="tight"`` crops each figure to its own drawn extent, so
    figures drawn on the same page preset come out a few millimetres wider or
    narrower than one another (and than the page's content width). This keeps
    the full canvas width -- every figure on a page preset saves at the same
    width, ready to place 1:1 in the page's content box -- and trims only the
    empty space above and below the content (plus ``pad_mm``).

    Anything drawn outside the canvas horizontally would be cut off, so that
    is reported as a warning (the print audit flags it too).
    """
    from matplotlib.transforms import Bbox

    fig.canvas.draw()
    tb = fig.get_tightbbox(fig.canvas.get_renderer())
    w, _ = fig.get_size_inches()
    tol = 0.1 / MM_PER_INCH
    if tb.x0 < -tol or tb.x1 > w + tol:
        warnings.warn(
            f"{path}: content extends {max(-tb.x0, 0) * MM_PER_INCH:.1f} mm left / "
            f"{max(tb.x1 - w, 0) * MM_PER_INCH:.1f} mm right of the canvas and will be cut off; "
            f"adjust the figure's margins in its config.")
    pad = pad_mm / MM_PER_INCH
    kwargs.pop("bbox_inches", None)
    kwargs.pop("pad_inches", None)
    fig.savefig(path, bbox_inches=Bbox([[0.0, tb.y0 - pad], [w, tb.y1 + pad]]), **kwargs)
