"""Pathway terms x enrichment tests dot matrix.

Rows are pathway terms (or term clusters), columns are the tests that judged
them (e.g. over-representation against a matched background, and a rank-based
GSEA). Each cell shows that test's result for that term: filled and coloured
by -log10 adjusted P when significant, hollow when tested but not significant,
blank when the test did not cover the term. Dot area = share of the class's
genes that are term members (ORA members or GSEA leading edge), so empty
columns -- a test that finds nothing -- read as a result, not a gap.
"""

from __future__ import annotations

import textwrap

import numpy as np
from matplotlib.lines import Line2D

from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("pathway_test_matrix", params=[
    # [Rows (terms) and columns (tests)]
    Param("term_order", list, None, role="Row order top to bottom (default: order of first appearance)"),
    Param("test_order", list, None, role="Column order (default: order of first appearance)"),
    Param("test_labels", dict, {}, open_keys=True, role="Column label per test key"),
    Param("min_rows", int, 0, unit="rows", range=(0, None),
          role="Keep the row spacing of this many rows for short lists (empty slots at the bottom)"),
    Param("term_fontsize", float, 6, unit="pt", range=(0, None), role="Term label size"),
    Param("ylabel_wrap_width", int, 42, unit="characters", range=(1, None), role="Wrap term labels at this width"),
    Param("xtick_fontsize", float, 6, unit="pt", range=(0, None), role="Column label size"),
    Param("xtick_rotation", float, 30, unit="degrees", role="Column label rotation"),
    Param("column_header", str, None, role="Text over the test columns"),
    Param("column_header_pad", float, 0.02, unit="axes fraction", role="Gap between the matrix and the column header"),
    Param("column_header_fontsize", float, 5.5, unit="pt", range=(0, None), role="Column header size"),
    Param("column_header_color", "color", "#334155", unit="hex color", role="Column header colour"),
    # [Dots]
    Param("cmap", "cmap", "viridis", role="Colormap for -log10 adjusted P"),
    Param("vmin", float, CODE_DEFAULT, unit="-log10 adjusted P", role="Colour floor (default -log10(0.05))"),
    Param("vmax", float, CODE_DEFAULT, unit="-log10 adjusted P", role="Colour ceiling (default: from the data)"),
    Param("size_per_share", float, 600.0, unit="pt^2 per unit share", range=(0, None), role="Dot area per share of class genes",
          tune="lower if dots overlap"),
    Param("size_min", float, 4.0, unit="pt^2 (marker area)", range=(0, None), role="Smallest dot"),
    Param("hollow_color", "color", "#ffffff", unit="hex color", role="Fill of tested but not significant dots"),
    Param("hollow_label", str, "n.s.", role="Legend text for hollow dots"),
    Param("dot_edgecolor", "color", "#333333", unit="hex color", role="Dot outline colour"),
    Param("dot_edgewidth", float, 0.4, unit="pt", range=(0, None), role="Dot outline width"),
    Param("dot_alpha", float, 0.9, unit="[0-1] opacity", range=(0, 1), role="Dot opacity"),
    Param("grid_linewidth", float, 0.4, unit="pt", range=(0, None), role="Grid line width"),
    # [Title]
    Param("labels_title", str, None, role="Panel title (none = no title)"),
    Param("title_size", float, 8, unit="pt", role="Panel title font size"),
    Param("title_pad", float, 5, unit="pt", role="Gap between title and matrix"),
    # [Colourbar and size legend]
    Param("cbar_label", str, "-log10(adjusted P)", role="Colourbar title"),
    Param("cbar_label_size", float, 6, unit="pt", range=(0, None), role="Colourbar title size"),
    Param("cbar_tick_size", float, 5.5, unit="pt", range=(0, None), role="Colourbar tick size"),
    Param("cbar_outline_width", float, 0.5, unit="pt", range=(0, None), role="Colourbar outline width"),
    Param("size_legend_values", list, [0.05, 0.15], unit="share of class genes", role="Shares shown in the size legend"),
    Param("size_legend_title", str, "Share of class genes", role="Size legend title"),
    Param("legend_fontsize", float, 5.5, unit="pt", range=(0, None), role="Legend text size"),
    Param("legend_loc", str, "lower left", role="Legend anchor point (matplotlib loc)"),
    Param("legend_bbox", list, [1.04, 0.0], unit="axes fraction (x, y)", role="Where legend_loc is placed"),
    Param("legend_labelspacing", float, 0.8, unit="x font size", role="Vertical spacing of legend entries"),
    Param("legend_ncol", int, 1, unit="columns", range=(1, None), role="Legend columns"),
    Param("legend_columnspacing", float, 1.0, unit="x font size", role="Horizontal spacing of legend columns"),
    # [Empty slots note]
    Param("empty_note", str, None, role="Note shown in the empty slots when min_rows exceeds the term count"),
    Param("empty_note_x", float, -0.6, unit="data coords", role="x position of the empty-slot note"),
    Param("empty_note_wrap_width", int, 30, unit="characters", range=(1, None), role="Wrap the note at this width"),
    Param("empty_note_color", "color", "#6b7280", unit="hex color", role="Note colour"),
])


@uses_schema(SCHEMA)
def render_pathway_test_matrix(ax, cells, params: dict, cax=None):
    """Draw ``cells`` onto ``ax``; returns (mappable, size legend or None).

    cells: DataFrame with term (row label), test (column key), value
      (-log10 adjusted P; NaN = not tested), share (0-1, dot area), sig (bool).
    params: term_order (list, top to bottom), test_order (list), test_labels
      ({test: column label}), cmap ('viridis'), vmin (colour floor, e.g.
      -log10(0.05)), vmax (auto), size_per_share (pt^2 per unit share, 600),
      size_min (4), hollow_color ('#ffffff'), dot_edgecolor ('#333333'),
      dot_edgewidth (0.4), dot_alpha (0.9), term_fontsize (6), ylabel_wrap_width
      (42), min_rows (0: keep row spacing for short lists, empty slots at the
      bottom), xtick_fontsize (6), xtick_rotation (30), labels_title,
      title_size (8), title_pad (5), grid_linewidth (0.4), cbar_label,
      cbar_label_size (6), cbar_tick_size (5.5), size_legend_values ([0.05, 0.15]),
      size_legend_title ('Share of class genes'), legend_fontsize (5.5),
      legend_bbox ([1.04, 0.0]: lower-left corner in axes fraction), legend_loc
      ('lower left'), legend_labelspacing (0.8), legend_ncol (1), legend_columnspacing (1.0), column_header (text over the test
      columns; column_header_pad / _fontsize / _color), empty_note (shown in the
      empty slots left of the matrix when min_rows exceeds the term count;
      empty_note_x in data units, empty_note_wrap_width, empty_note_color)
    """
    terms = list(params.get("term_order") or dict.fromkeys(cells["term"]))
    tests = list(params.get("test_order") or dict.fromkeys(cells["test"]))
    labels = params.get("test_labels", {})
    n_rows = max(len(terms), int(params.get("min_rows", 0)))
    ypos = {t: i for i, t in enumerate(terms)}
    xpos = {t: i for i, t in enumerate(tests)}

    d = cells[cells["term"].isin(ypos) & cells["test"].isin(xpos) & cells["value"].notna()].copy()
    x = d["test"].map(xpos).to_numpy(dtype=float)
    y = d["term"].map(ypos).to_numpy(dtype=float)
    per, smin = float(params.get("size_per_share", 600.0)), float(params.get("size_min", 4.0))
    s = smin + d["share"].fillna(0).to_numpy(dtype=float) * per
    sig = d["sig"].to_numpy(dtype=bool)
    ec, ew = params.get("dot_edgecolor", "#333333"), float(params.get("dot_edgewidth", 0.4))
    alpha = float(params.get("dot_alpha", 0.9))

    vmin = float(params.get("vmin", -np.log10(0.05)))
    vals = d["value"].to_numpy(dtype=float)
    vmax = float(params.get("vmax", max(vals[sig].max() if sig.any() else vmin + 1, vmin + 0.5)))
    ax.scatter(x[~sig], y[~sig], s=s[~sig], c=params.get("hollow_color", "#ffffff"), edgecolors=ec,
               linewidths=ew, alpha=alpha, zorder=2)
    sc = ax.scatter(x[sig], y[sig], s=s[sig], c=vals[sig], cmap=params.get("cmap", "viridis"),
                    vmin=vmin, vmax=vmax, edgecolors=ec, linewidths=ew, alpha=alpha, zorder=3)

    wrap = int(params.get("ylabel_wrap_width", 42))
    ax.set_yticks(range(len(terms)))
    ax.set_yticklabels([textwrap.fill(str(t), width=wrap, break_long_words=False) for t in terms],
                       fontsize=float(params.get("term_fontsize", 6)))
    ax.set_xticks(range(len(tests)))
    rot = float(params.get("xtick_rotation", 30))
    ax.set_xticklabels([labels.get(t, t) for t in tests], fontsize=float(params.get("xtick_fontsize", 6)),
                       rotation=rot, ha="right" if rot else "center", rotation_mode="anchor")
    ax.set_xlim(-0.6, len(tests) - 0.4)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ax.grid(True, linestyle="--", alpha=0.4, linewidth=float(params.get("grid_linewidth", 0.4)))
    ax.set_axisbelow(True)
    if params.get("labels_title"):
        ax.set_title(params["labels_title"], fontsize=float(params.get("title_size", 8)), fontweight="bold",
                     pad=float(params.get("title_pad", 5)))
    if params.get("column_header"):
        # Shared header over the test columns (e.g. gene-set source and reference set)
        ax.text(0.5, 1.0 + float(params.get("column_header_pad", 0.02)), params["column_header"],
                transform=ax.transAxes, ha="center", va="bottom", linespacing=1.1,
                fontsize=float(params.get("column_header_fontsize", 5.5)),
                color=params.get("column_header_color", "#334155"))
    if len(terms) < n_rows and params.get("empty_note"):
        # Short lists keep their row spacing; the empty slots say why they are empty
        ax.text(float(params.get("empty_note_x", -0.6)), (len(terms) + n_rows - 1) / 2,
                textwrap.fill(params["empty_note"], width=int(params.get("empty_note_wrap_width", 30))),
                ha="right", va="center", fontsize=float(params.get("term_fontsize", 6)), style="italic",
                color=params.get("empty_note_color", "#6b7280"))

    if cax is not None:
        cb = ax.figure.colorbar(sc, cax=cax)
        cb.set_label(params.get("cbar_label", "-log10(adjusted P)"), fontsize=float(params.get("cbar_label_size", 6)),
                     fontweight="bold")
        cb.ax.tick_params(labelsize=float(params.get("cbar_tick_size", 5.5)))
        cb.outline.set_linewidth(float(params.get("cbar_outline_width", 0.5)))

    leg = None
    vals_leg = params.get("size_legend_values", [0.05, 0.15])
    if vals_leg:
        handles = [Line2D([], [], marker="o", ls="", markersize=float(np.sqrt(smin + v * per)),
                          markerfacecolor="#d1d5db", markeredgecolor=ec, markeredgewidth=ew,
                          label=f"{v:.0%}" if v < 1 else f"{v:g}") for v in vals_leg]
        handles.append(Line2D([], [], marker="o", ls="", markersize=float(np.sqrt(smin + 0.05 * per)),
                              markerfacecolor=params.get("hollow_color", "#ffffff"), markeredgecolor=ec,
                              markeredgewidth=ew, label=params.get("hollow_label", "n.s.")))
        fs = float(params.get("legend_fontsize", 5.5))
        leg = ax.legend(handles=handles, title=params.get("size_legend_title", "Share of class genes"),
                        loc=params.get("legend_loc", "lower left"),
                        bbox_to_anchor=tuple(params.get("legend_bbox", [1.04, 0.0])), fontsize=fs,
                        title_fontsize=fs, frameon=False, labelspacing=float(params.get("legend_labelspacing", 0.8)),
                        ncol=int(params.get("legend_ncol", 1)), columnspacing=float(params.get("legend_columnspacing", 1.0)),
                        handletextpad=0.3, borderaxespad=0.0, alignment="left")
    return sc, leg
