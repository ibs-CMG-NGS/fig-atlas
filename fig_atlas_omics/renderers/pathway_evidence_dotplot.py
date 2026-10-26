"""Pathway dot plot coloured by the test that supports each term.

For term lists merged from different enrichment tests (e.g. over-representation
against a matched background and a rank-based GSEA), whose effect statistics
(fold enrichment, NES) are not on one scale: x is the -log10 adjusted P of the
supporting test (the smaller one when both pass), colour names the test(s),
dot area is the number of member genes. Terms are listed top to bottom by
significance; with fewer terms than ``min_rows`` the rows keep their spacing
and the empty slots stay at the bottom, so panels with few terms stay honest
rather than stretched.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import textwrap

import numpy as np
from matplotlib.lines import Line2D

DEFAULT_COLORS = {"ORA": "#2563eb", "GSEA": "#f59e0b", "ORA + GSEA": "#7c3aed"}


from fig_atlas.schema import Param, Schema, uses_schema

SCHEMA = Schema("pathway_evidence_dotplot", params=[
    # [Dots]
    Param("evidence_colors", dict, {}, open_keys=True, unit="hex color",
          role="Colour per evidence type, merged over the defaults (ORA, GSEA, ORA + GSEA)"),
    Param("evidence_labels", dict, {}, open_keys=True, role="Legend text per evidence type"),
    Param("size_per_gene", float, 0.6, unit="pt^2 per member gene", range=(0, None),
          role="Dot area added per member gene", tune="lower if large terms' dots overlap"),
    Param("size_offset", float, 4, unit="pt^2 (marker area)", range=(0, None), role="Dot area of a term with no genes"),
    Param("dot_alpha", float, 0.9, unit="alpha [0-1]", range=(0, 1), role="Dot opacity"),
    Param("dot_edgecolor", "color", "#333333", unit="hex color", role="Dot outline colour"),
    Param("dot_edgewidth", float, 0.4, unit="pt", range=(0, None), role="Dot outline width"),
    # [Rows]
    Param("min_rows", int, 0, unit="rows", range=(0, None), role="Reserve at least this many rows (keeps panels the same height)"),
    Param("empty_note", str, None, role="Text in the empty rows when there are fewer terms than min_rows; '{n}' = count"),
    Param("empty_note_color", "color", "#6b7280", unit="hex color", role="Empty-row note colour"),
    Param("empty_note_wrap_width", int, 40, unit="characters", range=(1, None), role="Wrap the empty-row note at this width"),
    Param("ylabel_wrap_width", int, 42, unit="characters", range=(1, None), role="Wrap term names at this width"),
    Param("term_fontsize", float, 6, unit="pt", range=(0, None), role="Term name size"),
    # [Axes]
    Param("xlabel", str, "-log10(adjusted P)", role="x-axis title"),
    Param("xlim_headroom", float, 0.12, unit="fraction of the largest x", range=(0, None),
          role="Space added past the largest dot", tune="raise if the right-most dot is clipped"),
    Param("grid_linewidth", float, 0.4, unit="pt", range=(0, None), role="Grid line width"),
    # [Legend]
    Param("legend_loc", str, "upper left", role="Legend location (matplotlib loc string)"),
    Param("legend_bbox", list, [1.02, 1.0], unit="axes fraction (x, y)", role="Legend anchor; default sits right of the axes"),
    Param("legend_fontsize", float, 5.5, unit="pt", range=(0, None), role="Legend font size"),
    Param("legend_labelspacing", float, 0.6, unit="font-size units", range=(0, None), role="Vertical space between legend entries"),
    Param("legend_marker_size", float, 4, unit="pt", range=(0, None), role="Marker size of the evidence entries"),
    Param("size_legend_values", list, [20, 100], unit="genes", role="Gene counts shown in the size legend"),
    Param("size_legend_title", str, "genes", role="Word after each size legend value"),
    # [Labels]
    Param("labels_title", str, None, role="Panel title"),
    Param("title_pad", float, 5, unit="pt", range=(0, None), role="Gap between title and axes"),
    Param("title_size", float, 8, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 7, unit="pt", range=(0, None), role="Axis title font size"),
    Param("tick_label_size", float, 6, unit="pt", range=(0, None), role="Tick label font size"),
])


@uses_schema(SCHEMA)
def render_pathway_evidence_dotplot(ax, terms, params: dict):
    """Draw ``terms`` (DataFrame: Description, p.adjust, evidence, Count; one row
    per term, already the ones to show) onto ``ax``. Returns the legend artist
    (or None).

    params: evidence_colors ({evidence: colour}), evidence_labels ({evidence:
      legend text}), size_per_gene (pt^2 per member gene, 0.6), size_offset (4),
      size_legend_values ([20, 100]), size_legend_title ('Genes'),
      dot_edgecolor ('#333333'), dot_edgewidth (0.4), dot_alpha (0.9),
      term_fontsize (6), ylabel_wrap_width (42), min_rows (0), xlabel,
      axes_label_size (7), tick_label_size (6), labels_title, title_size (8),
      title_pad (5), grid_linewidth (0.4), xlim_headroom (0.12: fraction added
      past the largest x), legend_fontsize (5.5), legend_loc ('upper left'),
      legend_bbox ([1.02, 1.0]), legend_labelspacing (0.6), empty_note (text shown
      in the empty rows when there are fewer terms than min_rows; '{n}' = count)
    """
    colors = {**DEFAULT_COLORS, **params.get("evidence_colors", {})}
    labels = params.get("evidence_labels", {})
    d = terms.sort_values("p.adjust").reset_index(drop=True)
    n = len(d)
    n_rows = max(n, int(params.get("min_rows", 0)))
    x = -np.log10(d["p.adjust"].clip(lower=1e-300).to_numpy(dtype=float))
    y = n_rows - 1 - np.arange(n)            # most significant on top
    per_gene, offset = float(params.get("size_per_gene", 0.6)), float(params.get("size_offset", 4))
    ax.scatter(x, y, s=d["Count"].to_numpy(dtype=float) * per_gene + offset,
               c=[colors.get(e, "#9ca3af") for e in d["evidence"]],
               edgecolors=params.get("dot_edgecolor", "#333333"),
               linewidths=float(params.get("dot_edgewidth", 0.4)),
               alpha=float(params.get("dot_alpha", 0.9)), zorder=3)

    wrap = int(params.get("ylabel_wrap_width", 42))
    ax.set_yticks(y)
    ax.set_yticklabels([textwrap.fill(str(t), width=wrap, break_long_words=False) for t in d["Description"]],
                       fontsize=float(params.get("term_fontsize", 6)))
    ax.set_ylim(-0.6, n_rows - 0.4)
    xmax = float(x.max()) if n else 1.0
    ax.set_xlim(0, xmax * (1 + float(params.get("xlim_headroom", 0.12))))
    tick_sz = float(params.get("tick_label_size", 6))
    ax.tick_params(axis="x", labelsize=tick_sz)
    ax.set_xlabel(params.get("xlabel", "-log10(adjusted P)"), fontsize=float(params.get("axes_label_size", 7)),
                  fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4, linewidth=float(params.get("grid_linewidth", 0.4)))
    ax.set_axisbelow(True)
    if params.get("labels_title"):
        ax.set_title(params["labels_title"], fontsize=float(params.get("title_size", 8)), fontweight="bold",
                     pad=float(params.get("title_pad", 5)))
    if n < n_rows and params.get("empty_note"):
        wrap_note = int(params.get("empty_note_wrap_width", 40))
        ax.text(float(np.mean(ax.get_xlim())), (n_rows - n - 1) / 2,
                textwrap.fill(params["empty_note"].format(n=n), width=wrap_note),
                ha="center", va="center", fontsize=float(params.get("term_fontsize", 6)),
                color=params.get("empty_note_color", "#6b7280"), style="italic")

    handles = [Line2D([], [], marker="o", ls="", markersize=float(params.get("legend_marker_size", 4)),
                      markerfacecolor=colors[e], markeredgecolor=params.get("dot_edgecolor", "#333333"),
                      markeredgewidth=float(params.get("dot_edgewidth", 0.4)), label=labels.get(e, e))
               for e in colors if (d["evidence"] == e).any()]
    for v in params.get("size_legend_values", [20, 100]):
        handles.append(Line2D([], [], marker="o", ls="", markersize=float(np.sqrt(v * per_gene + offset)),
                              markerfacecolor="#d1d5db", markeredgecolor=params.get("dot_edgecolor", "#333333"),
                              markeredgewidth=float(params.get("dot_edgewidth", 0.4)),
                              label=f"{v} {params.get('size_legend_title', 'genes')}"))
    if not handles:
        return None
    leg = ax.legend(handles=handles, loc=params.get("legend_loc", "upper left"),
                    bbox_to_anchor=tuple(params.get("legend_bbox", [1.02, 1.0])),
                    fontsize=float(params.get("legend_fontsize", 5.5)), frameon=False,
                    labelspacing=float(params.get("legend_labelspacing", 0.6)), handletextpad=0.3,
                    borderaxespad=0.0)
    return leg
