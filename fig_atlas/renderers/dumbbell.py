"""Paired dumbbell (dot-and-whisker gap) comparison renderer.

Visualizes cross-species or cross-condition quantitative comparisons (e.g. DEG/DA count
magnitudes, effect sizes) across multiple assays and directions in a unified hierarchical facet.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("dumbbell", params=[
    # [Colours and marks]
    Param("c_human", "color", "#2563EB", unit="hex color", role="Human marker colour"),
    Param("c_mouse", "color", "#DC2626", unit="hex color", role="Mouse marker colour"),
    Param("c_link", "color", "#94A3B8", unit="hex color", role="Line joining the two species of a condition"),
    Param("marker_size", float, 90, unit="pt^2 (marker area)", range=(0, None), role="Marker size"),
    Param("marker_edgewidth", float, 0.8, unit="pt", range=(0, None), role="Marker outline width"),
    Param("link_linewidth", float, 2.0, unit="pt", range=(0, None), role="Width of the joining line"),
    Param("grid_linewidth", float, 0.8, unit="pt", range=(0, None), role="Grid line width"),
    # [x axes: symlog counts per assay]
    Param("linthresh", float, 10.0, unit="count (data coords)", range=(0, None),
          role="symlog x: counts within +/- linthresh are drawn linearly"),
    Param("rna_xlim", list, [-1.5, 1200], unit="data coords [min, max]", role="x range of the RNA (DEG) column"),
    Param("rna_xticks", list, [0, 10, 100, 1000], unit="data coords", role="RNA tick positions"),
    Param("rna_xticklabels", list, ["0", "$10^1$", "$10^2$", "$10^3$"], role="RNA tick labels"),
    Param("atac_xlim", list, [-1.5, 25000], unit="data coords [min, max]", role="x range of the ATAC (DA) column"),
    Param("atac_xticks", list, [0, 10, 100, 1000, 10000], unit="data coords", role="ATAC tick positions"),
    Param("atac_xticklabels", list, ["0", "$10^1$", "$10^2$", "$10^3$", "$10^4$"], role="ATAC tick labels"),
    Param("xlabel", str, "Significant Features (Count)", role="x-axis title"),
    Param("shared_xlabel", bool, False, role="One x title under both columns instead of one per column"),
    Param("shared_xlabel_y", float, -0.14, unit="figure fraction below the axes", role="Position of the shared x title"),
    Param("y_margin", float, None, unit="rows (data coords)", role="Empty room above and below the condition rows"),
    # [Count annotations at the markers]
    Param("annot_fontsize", float, 8.0, unit="pt", range=(0, None), role="Count label size"),
    Param("annot_offset_pts", float, 7, unit="pt", role="Distance of the count labels from their marker"),
    Param("mouse_annot_below", bool, False, role="Put mouse counts below their marker (human stays above)"),
    # [Text]
    Param("header_fontsize", float, 12.5, unit="pt", range=(0, None), role="Assay column header size"),
    Param("header_pad", float, 8, unit="pt", role="Gap between header and plot"),
    Param("ylabel_fontsize", float, 11.0, unit="pt", range=(0, None), role="Row title (up/down-regulated) size"),
    Param("ylabel_pad", float, 8, unit="pt", role="Gap between row title and tick labels"),
    Param("ytick_fontsize", float, 9.8, unit="pt", range=(0, None), role="Condition label size"),
    Param("xtick_fontsize", float, 9.0, unit="pt", range=(0, None), role="x tick label size"),
    Param("xlabel_fontsize", float, 9.5, unit="pt", range=(0, None), role="x title size"),
    Param("hide_inner_yticklabels", bool, False, role="Show condition labels only on the left column"),
    Param("show_right_row_label", bool, True, role="Repeat the row title, rotated, right of the right column"),
    # [Legend and layout]
    Param("facet_layout", ("2x2", "4x1"), "2x2",
          role="Facet arrangement: 2x2 = directions in rows, assays in columns; 4x1 = all four stacked in "
               "one column (assay by assay), for a single journal column",
          tune="4x1 when the figure spans one column and the 2x2 facets crowd"),
    Param("legend_fontsize", float, 9.5, unit="pt", range=(0, None), role="Legend text size"),
    Param("legend_markersize", float, 9, unit="pt", range=(0, None), role="Legend marker size"),
    Param("legend_edgecolor", "color", "#cbd5e1", unit="hex color", role="Legend frame colour"),
    Param("legend_row_ratio", float, 0.08, unit="x a plot row's height", role="Height of the legend row under the plots"),
    Param("hspace", float, 0.35, unit="fraction of a row's height", role="Gap between the up and down rows"),
    Param("wspace", float, 0.28, unit="fraction of a column's width", role="Gap between the RNA and ATAC columns"),
    Param("left_inset", float, 0.0, unit="[0-1] fraction of the slot width", range=(0, 1),
          role="Empty strip on the left of the slot", tune="raise if the row titles clip at the left"),
    Param("extend_right", float, 0.0, unit="fraction of the plot width",
          role="Stretch the plots rightwards by this share (to end where a neighbouring panel ends)"),
])


@uses_schema(SCHEMA)
def render_paired_dumbbell(
    fig: plt.Figure,
    gs_target,
    counts: dict,
    conditions: list[str],
    params: dict,
    cond_rename: dict | None = None,
    facets: list[tuple[str, str, str]] | None = None,
) -> dict:
    """Render a multi-assay paired dumbbell plot into a GridSpec slot.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Parent figure.
    gs_target : SubplotSpec or GridSpec slice
        Target grid slot for the dumbbell composite.
    counts : dict
        Hierarchical counts dict mapping {series_key: {cond: (n_up, n_down)}}.
    conditions : list[str]
        List of condition identifiers (e.g. ['Acute_1D', 'Acute_3D', ...]).
    params : dict
        Dumbbell visualization parameters.
    cond_rename : dict | None
        Mapping from condition key to display label.
    facets : list[tuple[str, str, str]] | None
        List of (column_title, human_key, mouse_key) tuples.
        Defaults to [("mRNA-seq (DEG)", "human_rna", "mouse_rna"), ("ATAC-seq (DA)", "human_atac", "mouse_atac")].

    Returns
    -------
    dict
        Dictionary of created subplots and legend axis.
    """
    if cond_rename is None:
        cond_rename = {}
    if facets is None:
        facets = [
            ("mRNA-seq (DEG)", "human_rna", "mouse_rna"),
            ("ATAC-seq (DA)", "human_atac", "mouse_atac"),
        ]

    c_human = params.get("c_human", "#2563EB")
    c_mouse = params.get("c_mouse", "#DC2626")
    c_link = params.get("c_link", "#94A3B8")
    linthresh = float(params.get("linthresh", 10.0))

    rna_xlim = params.get("rna_xlim", [-1.5, 1200])
    atac_xlim = params.get("atac_xlim", [-1.5, 25000])
    rna_xticks = params.get("rna_xticks", [0, 10, 100, 1000])
    rna_xticklabels = params.get("rna_xticklabels", ["0", "$10^1$", "$10^2$", "$10^3$"])
    atac_xticks = params.get("atac_xticks", [0, 10, 100, 1000, 10000])
    atac_xticklabels = params.get("atac_xticklabels", ["0", "$10^1$", "$10^2$", "$10^3$", "$10^4$"])

    db_marker_s = float(params.get("marker_size", 90))
    db_marker_ew = float(params.get("marker_edgewidth", 0.8))
    db_link_lw = float(params.get("link_linewidth", 2.0))
    db_annot_fs = float(params.get("annot_fontsize", 8.0))
    db_hdr_fs = float(params.get("header_fontsize", 12.5))
    db_hdr_pad = float(params.get("header_pad", 8))
    db_ylabel_fs = float(params.get("ylabel_fontsize", 11.0))
    db_xlabel_fs = float(params.get("xlabel_fontsize", 9.5))
    db_ytick_fs = float(params.get("ytick_fontsize", 9.8))
    db_xtick_fs = float(params.get("xtick_fontsize", 9.0))
    db_hspace = float(params.get("hspace", 0.35))
    db_wspace = float(params.get("wspace", 0.28))
    db_leg_fs = float(params.get("legend_fontsize", 9.5))
    db_leg_edge = params.get("legend_edgecolor", "#cbd5e1")
    db_annot_off = float(params.get("annot_offset_pts", 7))
    db_labelpad = float(params.get("ylabel_pad", 8))
    db_leg_ms = float(params.get("legend_markersize", 9))
    db_leg_row = float(params.get("legend_row_ratio", 0.08))
    db_grid_lw = float(params.get("grid_linewidth", 0.8))
    # Put the mouse count under its marker so close human/mouse values don't
    # print on top of each other.
    mouse_below = bool(params.get("mouse_annot_below", False))
    # Every facet column lists the same conditions; showing them only on the
    # leftmost column frees the inner gutter for the data.
    hide_inner_ylabels = bool(params.get("hide_inner_yticklabels", False))
    # One x-axis title centred under all facet columns instead of one per
    # column (per-column titles collide once the facets are narrow).
    shared_xlabel = bool(params.get("shared_xlabel", False))
    shared_xlabel_y = float(params.get("shared_xlabel_y", -0.14))
    # Extra row padding (in row units) so above/below count callouts clear
    # the column header and the x axis; None keeps matplotlib's auto margin.
    y_margin = params.get("y_margin")
    xlabel_text = params.get("xlabel", "Significant Features (Count)")
    # The rightmost column repeats the UP/DOWN row title already on the left.
    show_right_row_label = bool(params.get("show_right_row_label", True))
    # Stretch the facet area rightward by this fraction of its own width
    # (e.g. to use space freed by dropping the right row title).
    extend_right = float(params.get("extend_right", 0.0))

    n_cols = len(facets)
    stacked = params.get("facet_layout", "2x2") == "4x1"
    # Reserve a label slot inside the target column so the left facets' tick
    # labels and row titles stay within the panel's own bounds (its outer box
    # then starts at the column edge, where the panel tag sits) instead of
    # hanging into the gutter toward the neighbouring panel.
    left_inset = float(params.get("left_inset", 0.0))
    if left_inset > 0:
        gs_target = gs_target.subgridspec(1, 2, width_ratios=[left_inset, 1.0 - left_inset], wspace=0.0)[0, 1]
    # Grid cell of each facet: 2x2 puts direction in rows and assay in columns;
    # 4x1 stacks them in one column, assay by assay (UP above DOWN).
    if stacked:
        n_rows = 2 * n_cols
        gs_sub = gs_target.subgridspec(n_rows + 1, 1, height_ratios=[1.0] * n_rows + [db_leg_row], hspace=db_hspace)
    else:
        gs_sub = gs_target.subgridspec(3, n_cols, height_ratios=[1.0, 1.0, db_leg_row], hspace=db_hspace,
                                       wspace=db_wspace)
    axes = {}                                     # keyed (direction row, assay column) in either layout

    for col_idx, (assay_label, h_key, m_key) in enumerate(facets):
        for row_idx, direction in enumerate(["UP", "DOWN"]):
            cell = gs_sub[2 * col_idx + row_idx, 0] if stacked else gs_sub[row_idx, col_idx]
            grid_col = 0 if stacked else col_idx
            ax = fig.add_subplot(cell)
            axes[(row_idx, col_idx)] = ax

            for yi, cond in enumerate(conditions):
                h_counts = counts.get(h_key, {}).get(cond, (0, 0))
                m_counts = counts.get(m_key, {}).get(cond, (0, 0))
                h_up, h_down = h_counts if h_counts else (0, 0)
                m_up, m_down = m_counts if m_counts else (0, 0)
                h_val = (h_up if direction == "UP" else h_down) or 0
                m_val = (m_up if direction == "UP" else m_down) or 0

                # Connecting line between paired species
                ax.plot([h_val, m_val], [yi, yi], color=c_link, lw=db_link_lw, zorder=1)
                # Human marker (circle)
                ax.scatter(h_val, yi, s=db_marker_s, color=c_human, zorder=3, edgecolors="white", linewidths=db_marker_ew)
                # Mouse marker (diamond)
                ax.scatter(m_val, yi, s=db_marker_s, color=c_mouse, zorder=3, edgecolors="white", linewidths=db_marker_ew, marker="D")

                # Count annotations (above marker, colored by species)
                if h_val > 0:
                    ax.annotate(f"{h_val:,}", (h_val, yi), textcoords="offset points",
                                xytext=(0, db_annot_off), ha="center", fontsize=db_annot_fs, fontweight="bold",
                                color=c_human)
                if m_val > 0:
                    ax.annotate(f"{m_val:,}", (m_val, yi), textcoords="offset points",
                                xytext=(0, -db_annot_off if mouse_below else db_annot_off), ha="center",
                                va="top" if mouse_below else "baseline",
                                fontsize=db_annot_fs, fontweight="bold", color=c_mouse)
                if h_val == 0 and m_val == 0:
                    ax.annotate("0", (0, yi), textcoords="offset points",
                                xytext=(0, db_annot_off), ha="center", fontsize=db_annot_fs - 0.5, color="#94A3B8")

            ax.set_yticks(range(len(conditions)))
            ax.set_yticklabels([cond_rename.get(c, c) for c in conditions], fontsize=db_ytick_fs, fontweight="bold")
            if hide_inner_ylabels and grid_col > 0:
                ax.tick_params(axis="y", labelleft=False)
            if y_margin is not None:
                ax.set_ylim(-float(y_margin), len(conditions) - 1 + float(y_margin))
            ax.invert_yaxis()
            ax.set_xscale("symlog", linthresh=linthresh)

            if col_idx == 0:
                ax.set_xlim(left=rna_xlim[0], right=rna_xlim[1])
                ax.set_xticks(rna_xticks)
                ax.set_xticklabels(rna_xticklabels, fontsize=db_xtick_fs)
            else:
                ax.set_xlim(left=atac_xlim[0], right=atac_xlim[1])
                ax.set_xticks(atac_xticks)
                ax.set_xticklabels(atac_xticklabels, fontsize=db_xtick_fs)

            # Headers & Labels
            if row_idx == 0:
                ax.set_title(assay_label, fontsize=db_hdr_fs, fontweight="bold", pad=db_hdr_pad)
            if grid_col == 0:
                ax.set_ylabel(f"{direction}-regulated", fontsize=db_ylabel_fs, fontweight="bold", labelpad=db_labelpad)
            elif not show_right_row_label:
                ax.set_ylabel("")
            else:
                ax.set_ylabel("")
                ax.annotate(f"{direction}-regulated", xy=(1.03, 0.5), xycoords="axes fraction",
                            fontsize=db_ylabel_fs - 0.5, fontweight="bold", color="#334155", rotation=-90,
                            va="center", ha="left")

            last_row = (col_idx == n_cols - 1) if stacked else True     # stacked: one x title, under the bottom facet
            if row_idx == 1 and last_row and not (shared_xlabel and not stacked):
                ax.set_xlabel(xlabel_text, fontsize=db_xlabel_fs, fontweight="bold")
            else:
                ax.set_xlabel("")

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(axis="x", alpha=0.25, ls="--", lw=db_grid_lw)

    if extend_right:
        area_axes = list(axes.values())
        left = min(a.get_position().x0 for a in area_axes)
        right = max(a.get_position().x1 for a in area_axes)
        scale = 1.0 + extend_right
        for a in area_axes:
            p = a.get_position()
            a.set_position([left + (p.x0 - left) * scale, p.y0, p.width * scale, p.height])
        ext_right = left + (right - left) * scale
    else:
        ext_right = None

    if shared_xlabel and not stacked:
        ax_l, ax_r = axes[(1, 0)], axes[(1, n_cols - 1)]
        pos_l, pos_r = ax_l.get_position(), ax_r.get_position()
        x_mid = ((pos_l.x0 + pos_r.x1) / 2 - pos_l.x0) / pos_l.width  # in ax_l axes coords
        ax_l.set_xlabel(xlabel_text, fontsize=db_xlabel_fs, fontweight="bold")
        ax_l.xaxis.set_label_coords(x_mid, shared_xlabel_y)

    # Legend dedicated bottom row
    ax_leg = fig.add_subplot(gs_sub[-1, :])
    if ext_right is not None:
        p = ax_leg.get_position()
        ax_leg.set_position([p.x0, p.y0, ext_right - p.x0, p.height])
    ax_leg.axis("off")
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=c_human, markersize=db_leg_ms, label="Human"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor=c_mouse, markersize=db_leg_ms * 0.9, label="Mouse"),
        Line2D([0], [0], color=c_link, lw=db_link_lw, label="Species Difference (Gap)"),
    ]
    ax_leg.legend(handles=legend_elements, loc="center",
                  ncol=3, fontsize=db_leg_fs, frameon=True, facecolor="white", edgecolor=db_leg_edge)

    return {"axes": axes, "legend_ax": ax_leg}
