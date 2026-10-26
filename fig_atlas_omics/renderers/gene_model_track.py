"""gene_model_track: gene models over a genomic window -- exons as boxes, introns
as a line with strand chevrons -- packed into rows so neither the models nor
their names overlap.

Data: one row per exon, with the columns named by gene_col, transcript_col,
strand_col, exon_start_col and exon_end_col (e.g. a GENCODE/UCSC genePred split
into exons). ``collapse: longest`` keeps each gene's longest transcript.
Returns one row per drawn transcript (gene, transcript, start, end, row),
ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

FAMILY = "field"    # gallery family (fig_atlas/family.py): the shape this module draws

import re

import numpy as np
from matplotlib.patches import Rectangle

from fig_atlas.schema import Param, Schema, uses_schema

from ._tracks import pack_rows, text_span

SCHEMA = Schema("gene_model_track", params=[
    # [Data]
    Param("gene_col", str, "gene_name", role="Column with the gene name"),
    Param("transcript_col", str, "transcript_id", role="Column with the transcript id"),
    Param("strand_col", str, "strand", role="Column with + / -"),
    Param("exon_start_col", str, "exon_start", role="Column with the exon start (bp, 1-based)"),
    Param("exon_end_col", str, "exon_end", role="Column with the exon end (bp)"),
    Param("collapse", ("longest", "all"), "longest", role="One transcript per gene (the longest), or all"),
    Param("hide_pattern", str, None, role="Regular expression; genes whose name matches are left out (none: keep all)",
          tune="e.g. '^(ENSMUSG|Gm\\d)' hides unnamed and predicted genes"),
    # [Window]
    Param("x_min", float, None, unit="bp", role="Left end of the window (both x_min and x_max; none: the data extent)"),
    Param("x_max", float, None, unit="bp", role="Right end of the window"),
    # [Rows]
    Param("max_rows", int, 3, unit="rows", range=(1, None), role="Most rows of genes", tune="raise if names are dropped onto busy rows"),
    Param("row_gap_frac", float, 0.01, unit="fraction of the window", range=(0, None),
          role="Smallest gap between two genes (with their names) on one row"),
    # [Marks]
    Param("gene_color", "color", "#1e3a8a", unit="hex color", role="Colour of exons, introns and chevrons"),
    Param("highlight_colors", dict, {}, open_keys=True, unit="hex color", role="Colour per gene name to pick out"),
    Param("exon_height", float, 0.5, unit="fraction of a row", range=(0, 1), role="Exon box height"),
    Param("intron_width", float, 0.6, unit="pt", range=(0, None), role="Intron line width"),
    Param("chevron_spacing_frac", float, 0.025, unit="fraction of the window", range=(0, None),
          role="Distance between strand chevrons (0: none)", tune="raise for fewer chevrons"),
    Param("chevron_edge_width", float, 0.0, unit="pt", range=(0, None), role="Chevron outline width (0: filled only)"),
    Param("chevron_size", float, 2.5, unit="pt", range=(0, None), role="Chevron marker size"),
    # [Names]
    Param("show_labels", bool, True, role="Write gene names"),
    Param("label_size", float, 6.0, unit="pt", range=(0, None), role="Gene name size"),
    Param("label_style", str, "italic", role="Gene name font style"),
    Param("label_position", ("below", "left"), "below", role="Names under the model, or left of it"),
    Param("label_pad", float, 0.08, unit="fraction of a row", range=(0, None), role="Gap between a model and its name"),
    Param("label_char_em", float, 0.6, unit="em per character", range=(0, None),
          role="Estimated text width per character (packing only)", tune="raise if names on one row touch"),
    Param("text_color", "color", "#111827", unit="hex color", role="Gene name colour"),
])


@uses_schema(SCHEMA)
def render_gene_model_track(ax, df, params):
    """Draw the gene models onto ``ax``; returns the transcripts drawn."""
    g_col, t_col = params.get("gene_col", "gene_name"), params.get("transcript_col", "transcript_id")
    s_col = params.get("strand_col", "strand")
    a_col, b_col = params.get("exon_start_col", "exon_start"), params.get("exon_end_col", "exon_end")
    data = df.copy()
    pat = params.get("hide_pattern")
    if pat:
        data = data[~data[g_col].astype(str).str.contains(re.compile(pat))]
    tx = data.groupby(t_col, sort=False).agg(gene=(g_col, "first"), strand=(s_col, "first"),
                                             start=(a_col, "min"), end=(b_col, "max"))
    tx["span"] = tx["end"] - tx["start"]
    if params.get("collapse", "longest") == "longest":
        tx = tx.sort_values("span", ascending=False).groupby("gene", sort=False).head(1)
    lo, hi = params.get("x_min"), params.get("x_max")
    x0, x1 = (float(lo), float(hi)) if lo is not None and hi is not None \
        else (float(tx["start"].min()) - 1, float(tx["end"].max()))
    tx = tx[(tx["end"] >= x0) & (tx["start"] <= x1)].sort_values("start")
    span = x1 - x0

    size = float(params.get("label_size", 6.0))
    em = float(params.get("label_char_em", 0.6))
    left = params.get("label_position", "below") == "left"
    show = params.get("show_labels", True)
    extents = []
    for t_id, t in tx.iterrows():
        a, b = max(float(t["start"]), x0), min(float(t["end"]), x1)
        w = text_span(ax, str(t["gene"]), size, em, span) if show else 0.0
        extents.append((a - w, b) if left else (min(a, (a + b - w) / 2), max(b, (a + b + w) / 2)))
    rows = pack_rows(extents, float(params.get("row_gap_frac", 0.01)) * span, int(params.get("max_rows", 3)))
    tx = tx.assign(row=rows)
    n_rows = max(rows) + 1 if rows else 1

    eh = float(params.get("exon_height", 0.5))
    base = params.get("gene_color", "#1e3a8a")
    hl = params.get("highlight_colors", {})
    spacing = float(params.get("chevron_spacing_frac", 0.025)) * span
    for t_id, t in tx.iterrows():
        y = n_rows - 1 - t["row"] + 0.5
        color = hl.get(t["gene"], base)
        a, b = max(float(t["start"]), x0), min(float(t["end"]), x1)
        ax.plot([a, b], [y, y], color=color, linewidth=float(params.get("intron_width", 0.6)), solid_capstyle="butt")
        ex = data[data[t_col] == t_id]
        for _, e in ex.iterrows():
            ea, eb = max(float(e[a_col]) - 1, x0), min(float(e[b_col]), x1)
            if eb > ea:
                ax.add_patch(Rectangle((ea, y - eh / 2), eb - ea, eh, facecolor=color, edgecolor="none"))
        if spacing > 0:
            xs = np.arange(a + spacing / 2, b, spacing)
            in_exon = np.zeros(xs.size, dtype=bool)
            for _, e in ex.iterrows():
                in_exon |= (xs >= float(e[a_col])) & (xs <= float(e[b_col]))
            xs = xs[~in_exon]
            ax.plot(xs, np.full(xs.size, y), linestyle="none", marker=">" if t["strand"] == "+" else "<",
                    markersize=float(params.get("chevron_size", 2.5)), color=color,
                    markeredgewidth=float(params.get("chevron_edge_width", 0.0)))
        if show:
            pad = float(params.get("label_pad", 0.08))
            kw = dict(color=params.get("text_color", "#111827"), fontsize=size, style=params.get("label_style", "italic"))
            if left:
                ax.text(a - pad * span * eh, y, str(t["gene"]), ha="right", va="center", **kw)
            else:
                ax.text((a + b) / 2, y - eh / 2 - pad, str(t["gene"]), ha="center", va="top", **kw)

    ax.set_xlim(x0, x1)
    ax.set_ylim(0, n_rows)
    ax.set_axis_off()
    return tx.reset_index()[[t_col, "gene", "strand", "start", "end", "row"]]
