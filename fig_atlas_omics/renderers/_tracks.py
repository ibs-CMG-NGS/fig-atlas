"""Shared helpers of the genome-track renderers (gene_model_track, interval_track)."""
from __future__ import annotations


def axes_width_pt(ax) -> float:
    """Width of ``ax`` on the page, in points (layout as currently set)."""
    fig = ax.figure
    return ax.get_position().width * fig.get_figwidth() * 72.0


def text_span(ax, text: str, size_pt: float, char_em: float, x_span: float) -> float:
    """Approximate width of ``text`` at ``size_pt`` in x data units (x_span = shown width)."""
    width_pt = len(text) * size_pt * char_em
    return width_pt / max(axes_width_pt(ax), 1e-9) * x_span


def pack_rows(extents: list[tuple[float, float]], gap: float, max_rows: int) -> list[int]:
    """Greedy row per (start, end) in the given order: the first row whose last
    end + gap is left of start; past max_rows, the row that ends first."""
    ends: list[float] = []
    rows = []
    for a, b in extents:
        for r, e in enumerate(ends):
            if a >= e + gap:
                ends[r] = b
                rows.append(r)
                break
        else:
            if len(ends) < max_rows:
                ends.append(b)
                rows.append(len(ends) - 1)
            else:
                r = min(range(len(ends)), key=ends.__getitem__)
                ends[r] = max(ends[r], b)
                rows.append(r)
    return rows
