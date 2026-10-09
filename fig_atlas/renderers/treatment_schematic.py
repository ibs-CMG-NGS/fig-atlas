"""Treatment regimen and multi-omics sampling schematic diagram renderer.

Visualizes experimental timelines, treatment exposure periods (duration bars),
assay sampling timepoints (markers with assay-specific encodings), and grouped
regimen labels with bracket indicators.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("treatment_schematic", params=[
    # [Canvas, data coords: x = hours, y = regimen rows]
    Param("xlim", list, [-1, 76], unit="hours [min, max]", role="x range of the timeline axes"),
    Param("ylim", list, [-2.5, 5.2], unit="data coords [min, max]", role="y range shared by both axes"),
    # [Regimen labels and brackets, left axes]
    Param("regimen_labels", list, [
        {"text": "Acute", "x": 0.75, "y": 1.5, "fontsize": 14.0, "fontweight": "bold", "color": "#0F172A"},
        {"text": "Chronic", "x": 0.75, "y": 3.3, "fontsize": 14.0, "fontweight": "bold", "color": "#0F172A",
         "bracket": {"draw": True, "y_top": 3.9, "y_bot": 2.7, "x_tip": 0.95, "x_corner": 0.88, "x_stem": 0.82,
                     "color": "#475569", "lw": 1.8}}],
          role="Regimen names left of the bars: text, x/y (axes data coords), fontsize (pt), colour, optional bracket"),
    Param("label_fontsize", float, 13.0, unit="pt", range=(0, None), role="Default size of the regimen labels"),
    # [Timeline axis]
    Param("timeline_range", list, [0, 74], unit="hours [start, end]", role="Extent of the timeline line"),
    Param("timeline_ticks", list, [0, 3, 24, 48, 72], unit="hours", role="Tick positions on the timeline"),
    Param("timeline_labels", list, ["0", "3", "24", "48", "72"], role="Tick labels"),
    Param("timeline_linewidth", float, 3.2, unit="pt", range=(0, None), role="Timeline line width"),
    Param("y_axis", float, 0.2, unit="data coords", role="Height of the timeline line", tune="lower to move it away from the bars"),
    Param("tick_len", float, 0.40, unit="data coords", range=(0, None), role="Tick length on the timeline"),
    Param("tick_fontsize", float, 15.0, unit="pt", range=(0, None), role="Timeline tick label size"),
    Param("tick_label_offset", float, 0.75, unit="data coords", role="Gap between timeline and its tick labels"),
    # [Treatment bars and sampling circles]
    Param("treatment_bars", list, [{"start": 0, "end": 3, "y": 1.5}, {"start": 0, "end": 24, "y": 2.7},
                                   {"start": 0, "end": 48, "y": 3.9}],
          unit="hours (start, end) and data coords (y)", role="One exposure bar per regimen"),
    Param("bar_color", "color", "#FF0000", unit="hex color", role="Exposure bar fill"),
    Param("bar_edgecolor", "color", "#000000", unit="hex color", role="Exposure bar outline"),
    Param("bar_height", float, 0.56, unit="data coords", range=(0, None), role="Exposure bar thickness"),
    Param("bar_linewidth", float, 2.4, unit="pt", range=(0, None), role="Exposure bar outline width"),
    Param("samplings", list, [{"x": 24, "y": 1.5, "label": "1D"}, {"x": 72, "y": 1.5, "label": "3D"},
                              {"x": 72, "y": 2.7, "label": "24H"}, {"x": 72, "y": 3.9, "label": "48H"}],
          unit="hours (x) and data coords (y)", role="Sampling time points (circle per sample, with label)"),
    Param("color_rna", "color", "#8CE04F", unit="hex color", role="Fill of the RNA-seq half of a sampling circle"),
    Param("color_atac", "color", "#00C5FF", unit="hex color", role="Ring colour marking ATAC-seq"),
    Param("circle_size", float, 1700, unit="pt^2 (marker area)", range=(0, None), role="Sampling circle size"),
    Param("circle_linewidth", float, 3.5, unit="pt", range=(0, None), role="Sampling circle ring width"),
    # [Legend under the timeline]
    Param("legend", dict, {}, role="Legend layout: y, bar_x, bar_w, bar_label_x, bar_height, circle_size, circle_linewidth, "
                                   "rna_x, rna_label_x, rna_edgecolor, atac_x, atac_label_x, atac_circle_linewidth"),
    Param("y_legend", float, -1.8, unit="data coords", role="Legend row height (legend.y takes precedence)"),
    Param("legend_fontsize", float, 14.5, unit="pt", range=(0, None), role="Legend text size"),
])


@uses_schema(SCHEMA)
def render_treatment_schematic(ax_labels, ax_bars, params: dict) -> None:
    """Render treatment regimen and sampling schematic diagram across two coordinated axes.

    Parameters
    ----------
    ax_labels : matplotlib.axes.Axes
        Left axis for regimen category labels (e.g. 'Acute', 'Chronic') and brackets.
    ax_bars : matplotlib.axes.Axes
        Right axis for timeline axis, treatment duration bars, sampling points, and legend.
    params : dict
        Configuration parameters for the schematic diagram.
    """
    ylim = params.get("ylim", [-2.5, 5.2])

    # Left Axis: Regimen Labels (Acute & Chronic) and Brackets
    ax_labels.axis("off")
    ax_labels.set_xlim([0, 1])
    ax_labels.set_ylim(ylim)

    reg_labels = params.get("regimen_labels", [
        {"text": "Acute", "x": 0.75, "y": 1.5, "fontsize": 14.0, "fontweight": "bold", "color": "#0F172A"},
        {"text": "Chronic", "x": 0.75, "y": 3.3, "fontsize": 14.0, "fontweight": "bold", "color": "#0F172A",
         "bracket": {"draw": True, "y_top": 3.9, "y_bot": 2.7, "x_tip": 0.95, "x_corner": 0.88, "x_stem": 0.82, "color": "#475569", "lw": 1.8}}
    ])
    for r in reg_labels:
        txt = r.get("text", "")
        rx = float(r.get("x", 0.75))
        ry = float(r.get("y", 1.5))
        r_fs = float(r.get("fontsize", 14.0))
        r_fw = r.get("fontweight", "bold")
        r_col = r.get("color", "#0F172A")
        ax_labels.text(rx, ry, txt, ha="right", va="center", fontsize=r_fs, fontweight=r_fw, color=r_col)

        brk = r.get("bracket", {})
        if brk and brk.get("draw", False):
            y_t = float(brk.get("y_top", 3.9))
            y_b = float(brk.get("y_bot", 2.7))
            x_tip = float(brk.get("x_tip", 0.95))
            x_c = float(brk.get("x_corner", 0.88))
            x_s = float(brk.get("x_stem", 0.82))
            b_col = brk.get("color", "#475569")
            b_lw = float(brk.get("lw", 1.8))
            ax_labels.plot([x_tip, x_c, x_c, x_s], [y_t, y_t, ry, ry], color=b_col, lw=b_lw)
            ax_labels.plot([x_tip, x_c, x_c, x_s], [y_b, y_b, ry, ry], color=b_col, lw=b_lw)

    # Right Axis: Timeline Axis, Treatment Bars, Samplings, and Legend
    ax_bars.axis("off")
    xlim = params.get("xlim", [-1, 76])
    ax_bars.set_xlim(xlim)
    ax_bars.set_ylim(ylim)

    # 1. Timeline Axis
    y_axis = float(params.get("y_axis", 0.2))
    tl_range = params.get("timeline_range", [0, 74])
    tl_lw = float(params.get("timeline_linewidth", 3.2))
    ax_bars.plot(tl_range, [y_axis, y_axis], color="black", lw=tl_lw, zorder=2)

    # Ticks
    ticks = params.get("timeline_ticks", [0, 3, 24, 48, 72])
    tick_labels = params.get("timeline_labels", ["0", "3", "24", "48", "72"])
    tick_len = float(params.get("tick_len", 0.40))
    tick_fs = float(params.get("tick_fontsize", 15.0))
    tick_lbl_off = float(params.get("tick_label_offset", 0.75))
    for t, lbl in zip(ticks, tick_labels):
        ax_bars.plot([t, t], [y_axis - tick_len, y_axis + tick_len], color="black", lw=tl_lw, zorder=2)
        ax_bars.text(t, y_axis - tick_lbl_off, lbl, ha="center", va="top", fontsize=tick_fs, fontweight="bold", color="black")

    # 2. Treatment Duration Bars
    bar_h = float(params.get("bar_height", 0.56))
    c_red = params.get("bar_color", "#FF0000")
    edge_c = params.get("bar_edgecolor", "#000000")
    lw_bar = float(params.get("bar_linewidth", 2.4))

    bars = params.get("treatment_bars", [
        {"start": 0, "end": 3, "y": 1.5},
        {"start": 0, "end": 24, "y": 2.7},
        {"start": 0, "end": 48, "y": 3.9},
    ])
    for b in bars:
        x0, x1, y = float(b["start"]), float(b["end"]), float(b["y"])
        rect = mpatches.Rectangle((x0, y - bar_h / 2), x1 - x0, bar_h,
                                  facecolor=c_red, edgecolor=edge_c, linewidth=lw_bar, zorder=3)
        ax_bars.add_patch(rect)

    # 3. Sequencing Sampling Points (Circles)
    c_green = params.get("color_rna", "#8CE04F")
    c_cyan = params.get("color_atac", "#00C5FF")
    circle_s = float(params.get("circle_size", 1700))
    circle_lw = float(params.get("circle_linewidth", 3.5))
    lbl_fs = float(params.get("label_fontsize", 13.0))

    samplings = params.get("samplings", [
        {"x": 24, "y": 1.5, "label": "1D"},
        {"x": 72, "y": 1.5, "label": "3D"},
        {"x": 72, "y": 2.7, "label": "24H"},
        {"x": 72, "y": 3.9, "label": "48H"},
    ])
    for s in samplings:
        x, y, txt = float(s["x"]), float(s["y"]), str(s["label"])
        ax_bars.scatter(x, y, s=circle_s, facecolor=c_green, edgecolor=c_cyan,
                        linewidth=circle_lw, zorder=5)
        ax_bars.text(x, y, txt, ha="center", va="center", fontsize=lbl_fs, fontweight="bold",
                     color="black", zorder=6)

    # 4. Legend at bottom
    leg_cfg = params.get("legend", {})
    y_leg = float(leg_cfg.get("y", params.get("y_legend", -1.8)))
    leg_fs = float(params.get("legend_fontsize", 14.5))

    bar_x = float(leg_cfg.get("bar_x", 0.0))
    bar_w = float(leg_cfg.get("bar_w", 6.0))
    bar_lbl_x = float(leg_cfg.get("bar_label_x", 7.5))
    leg_bar_h = float(leg_cfg.get("bar_height", 0.45))
    leg_circle_s = float(leg_cfg.get("circle_size", 900))
    leg_circle_lw = float(leg_cfg.get("circle_linewidth", 2.8))
    rect_leg = mpatches.Rectangle((bar_x, y_leg - leg_bar_h / 2), bar_w, leg_bar_h,
                                  facecolor=c_red, edgecolor=edge_c, linewidth=lw_bar, zorder=3)
    ax_bars.add_patch(rect_leg)
    ax_bars.text(bar_lbl_x, y_leg, r"$\mathbf{H_2O_2\ treatment}$", ha="left", va="center",
                 fontsize=leg_fs, color="black")

    # RNA-seq circle legend
    x_rna = float(leg_cfg.get("rna_x", 28.0))
    x_rna_lbl = float(leg_cfg.get("rna_label_x", 31.0))
    ax_bars.scatter(x_rna, y_leg, s=leg_circle_s, facecolor=c_green, edgecolor=leg_cfg.get("rna_edgecolor", "#1B382B"),
                    linewidth=leg_circle_lw, zorder=5)
    ax_bars.text(x_rna_lbl, y_leg, "RNA Seq", ha="left", va="center",
                 fontsize=leg_fs, fontweight="bold", color="black")

    # ATAC-seq circle legend
    x_atac = float(leg_cfg.get("atac_x", 50.0))
    x_atac_lbl = float(leg_cfg.get("atac_label_x", 53.0))
    ax_bars.scatter(x_atac, y_leg, s=leg_circle_s, facecolor="white", edgecolor=c_cyan,
                    linewidth=float(leg_cfg.get("atac_circle_linewidth", 3.2)), zorder=5)
    ax_bars.text(x_atac_lbl, y_leg, "ATAC Seq", ha="left", va="center",
                 fontsize=leg_fs, fontweight="bold", color="black")
