"""Renderer for motif architecture and statistics table with graphical sequence logos."""

from __future__ import annotations

FAMILY = "field"    # gallery family (fig_atlas/family.py): the shape this module draws

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
import numpy as np


_NT_COLORS = {
    "A": "#00BB00",  # Green
    "C": "#0000EE",  # Blue
    "G": "#F9A500",  # Orange
    "T": "#DD0000",  # Red
}
_DEFAULT_NT_COLOR = "#546e7a"
_FONT_PROP = FontProperties(family="DejaVu Sans", weight="bold")


from fig_atlas.schema import Param, Schema, uses_schema

SCHEMA = Schema("motif_table", params=[
    Param("table_title", str, "Key Transcriptional Driver Motifs: Sequence Logos, Statistics & Known Binding Partners",
          role="Title above the motif table"),
    Param("font_family", str, "DejaVu Sans", role="Font of the table text"),
    Param("title_size", float, 11.5, unit="pt", range=(0, None), role="Table title size"),
    Param("header_size", float, 9.5, unit="pt", range=(0, None), role="Column header size"),
    Param("text_size", float, 8.5, unit="pt", range=(0, None), role="Cell text size"),
])


def _draw_logo_letter(ax: plt.Axes, letter: str, x: float, y: float, width: float, height: float, color: str):
    """Draw a scaled, squished letter patch at exact normalized position."""
    if height <= 0.001 or width <= 0.001:
        return
    tp = TextPath((0, 0), letter, size=1.0, prop=_FONT_PROP)
    bb = tp.get_extents()
    w_orig = bb.width if bb.width > 0 else 1.0
    h_orig = bb.height if bb.height > 0 else 1.0

    sx = width / w_orig
    sy = height / h_orig

    trans = Affine2D().translate(-bb.x0, -bb.y0).scale(sx, sy).translate(x, y) + ax.transAxes
    patch = PathPatch(tp, facecolor=color, edgecolor="none", transform=trans, zorder=3)
    ax.add_patch(patch)


def draw_sequence_logo_box(
    ax: plt.Axes,
    consensus_seq: str,
    box_x: float,
    box_y: float,
    box_w: float,
    box_h: float,
) -> None:
    """Draw a graphical sequence logo matching HOMER/MEME bit-stack styling.

    Dominant consensus letters stand tall (70-85% height), while secondary/minority
    letters stack squished underneath, creating publication-grade motif logos.
    """
    n_chars = len(consensus_seq)
    if n_chars == 0:
        return

    col_w = box_w / n_chars
    char_w = col_w * 0.92

    for i, char in enumerate(consensus_seq):
        c = char.upper()
        x = box_x + i * col_w

        if c in ("A", "C", "G", "T"):
            # Strong dominant single nucleotide (82% tall)
            main_color = _NT_COLORS[c]
            h_main = box_h * 0.82
            _draw_logo_letter(ax, c, x, box_y + box_h * 0.18, char_w, h_main, main_color)

            # Secondary minor base squished at bottom (6% each)
            other_bases = [b for b in ("A", "C", "G", "T") if b != c]
            curr_y = box_y
            h_sub = (box_h * 0.18) / len(other_bases)
            for ob in other_bases:
                _draw_logo_letter(ax, ob, x, curr_y, char_w, h_sub, _NT_COLORS[ob])
                curr_y += h_sub

        elif c in ("S", "W", "R", "Y", "M", "K", "B", "D", "H", "V", "N"):
            # Degenerate IUPAC bases (split heights)
            # S: C/G, W: A/T, R: A/G, Y: C/T, M: A/C, K: G/T
            iupac_map = {
                "S": ["G", "C"],
                "W": ["A", "T"],
                "R": ["G", "A"],
                "Y": ["T", "C"],
                "M": ["A", "C"],
                "K": ["G", "T"],
                "N": ["A", "C", "G", "T"],
                "B": ["C", "G", "T"],
                "H": ["A", "C", "T"],
            }
            sub_bases = iupac_map.get(c, ["A", "C", "G", "T"])
            curr_y = box_y
            h_each = (box_h * 0.95) / len(sub_bases)
            for sb in sub_bases:
                _draw_logo_letter(ax, sb, x, curr_y, char_w, h_each, _NT_COLORS.get(sb, _DEFAULT_NT_COLOR))
                curr_y += h_each


@uses_schema(SCHEMA)
def render_motif_architecture_table(ax: plt.Axes, motifs_data: list[dict], params: dict | None = None) -> None:
    """Render a publication-grade motif sequence logo and statistics table.

    Columns:
      1. Rank & Motif Name (with family tag)
      2. Graphical Sequence Logo (vector letter stacks)
      3. Consensus Text
      4. P-value
      5. % Target (Background)
      6. Similar Known Motifs
    """
    params = params or {}
    ax.clear()
    ax.axis("off")

    n_rows = len(motifs_data)
    if n_rows == 0:
        return

    # Coordinates setup
    y_header = 0.94
    y_start = 0.84
    row_height = (y_start - 0.04) / max(n_rows, 1)

    # Column x positions (fraction of width)
    x_rank = 0.02
    x_name = 0.07
    x_logo = 0.28
    logo_w = 0.23
    x_seq = 0.53
    x_pval = 0.65
    x_pct = 0.75
    x_similar = 0.86

    font_family = params.get("font_family", "DejaVu Sans")
    title_size = float(params.get("title_size", 11.5))
    header_size = float(params.get("header_size", 9.5))
    text_size = float(params.get("text_size", 8.5))

    # Header title
    header_title = params.get("table_title", "Key Transcriptional Driver Motifs: Sequence Logos, Statistics & Known Binding Partners")
    ax.text(
        0.02, 0.99, header_title,
        fontsize=title_size, fontweight="bold", fontfamily=font_family,
        va="top", ha="left", color="#111827"
    )

    # Header line
    headers = [
        (x_rank, "#"),
        (x_name, "Motif / Family"),
        (x_logo, "Sequence Logo"),
        (x_seq, "Consensus"),
        (x_pval, "P-value"),
        (x_pct, "% Targets (Bg)"),
        (x_similar, "Similar Known Motifs"),
    ]
    for x_pos, text in headers:
        ax.text(
            x_pos, y_header, text,
            fontsize=header_size, fontweight="bold", fontfamily=font_family,
            va="center", ha="left", color="#374151"
        )

    # Horizontal divider under headers
    ax.axhline(y=y_header - 0.035, xmin=0.01, xmax=0.99, color="#9ca3af", linewidth=1.2)

    # Rows
    for i, row in enumerate(motifs_data):
        y = y_start - i * row_height

        # Alternating background shading
        if i % 2 == 1:
            rect = plt.Rectangle(
                (0.01, y - row_height * 0.45), 0.98, row_height * 0.92,
                facecolor="#f9fafb", edgecolor="none", zorder=0,
                transform=ax.transAxes
            )
            ax.add_patch(rect)

        # 1. Rank
        rank_str = str(row.get("rank", i + 1))
        ax.text(x_rank, y, rank_str, fontsize=text_size, fontweight="bold",
                color="#6b7280", va="center", ha="left", fontfamily=font_family)

        # 2. Motif Name & Family
        name = row.get("name", "")
        family = row.get("family", "")
        ax.text(x_name, y + 0.012, name, fontsize=text_size, fontweight="bold",
                color="#111827", va="center", ha="left", fontfamily=font_family)
        if family:
            ax.text(x_name, y - 0.018, f"({family})", fontsize=text_size - 1.5,
                    color="#4b5563", va="center", ha="left", fontfamily=font_family)

        # 3. Graphical Sequence Logo (HOMER/MEME vector stack)
        consensus = row.get("consensus", "")
        logo_h = row_height * 0.68
        draw_sequence_logo_box(
            ax=ax,
            consensus_seq=consensus,
            box_x=x_logo,
            box_y=y - logo_h * 0.5,
            box_w=logo_w,
            box_h=logo_h,
        )

        # 4. Consensus text
        ax.text(x_seq, y, consensus, fontsize=text_size - 0.5,
                color="#374151", va="center", ha="left", fontfamily="monospace", fontweight="bold")

        # 5. P-value
        pval_str = row.get("pvalue", "")
        ax.text(x_pval, y, pval_str, fontsize=text_size,
                color="#111827", va="center", ha="left", fontfamily=font_family)

        # 6. % Target (Bg)
        pct_target = row.get("pct_target", "")
        pct_bg = row.get("pct_bg", "")
        pct_display = f"{pct_target} ({pct_bg})" if pct_bg else pct_target
        ax.text(x_pct, y, pct_display, fontsize=text_size,
                color="#111827", va="center", ha="left", fontfamily=font_family)

        # 7. Similar known motifs
        similar = row.get("similar", "")
        ax.text(x_similar, y, similar, fontsize=text_size - 1.0,
                color="#374151", va="center", ha="left", fontfamily=font_family)

    # Bottom border
    ax.axhline(y=y_start - n_rows * row_height + row_height * 0.45, xmin=0.01, xmax=0.99,
               color="#d1d5db", linewidth=0.8)
