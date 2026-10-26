"""Renderer for Genome-Wide RNA-ATAC Cis-Regulatory Linkage and Distance Decay."""

from __future__ import annotations

FAMILY = "field"    # gallery family (fig_atlas/family.py): the shape this module draws

from typing import Any, Mapping
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("cis_linkage", params=[
    # [Layout]
    Param("wspace", float, 0.35, unit="fraction of the mean panel width", range=(0, None),
          role="Gap between the decay bars and the scatter", tune="raise if the scatter's y label touches the bars"),
    # [Distance decay bars]
    Param("distance_bins", list, ["<2kb", "2-10kb", "10-50kb", "50-100kb"], role="Distance bins, in order"),
    Param("bar_colors", list, ["#991B1B", "#E11D48", "#F87171", "#CBD5E1"], unit="hex colors", role="One colour per distance bin"),
    Param("decay_title", str, "Spatial Distance Decay", role="Title of the decay bar panel"),
    Param("bar_label_size", float, 8.5, unit="pt", range=(0, None), role="Count label size on the bars"),
    # [Correlation scatter]
    Param("scatter_title", str, CODE_DEFAULT, role="Title of the scatter (default shows the pair count)"),
    Param("r_threshold", float, 0.5, unit="Pearson r", range=(-1, 1), role="Significance line; pairs above it are highlighted"),
    Param("bg_color", "color", "#94A3B8", unit="hex color", role="Colour of pairs below the threshold"),
    Param("bg_size", float, 13, unit="pt^2 (marker area)", range=(0, None), role="Marker size of pairs below the threshold"),
    Param("bg_alpha", float, 0.28, unit="alpha [0-1]", range=(0, 1), role="Opacity of pairs below the threshold"),
    Param("sig_color", "color", "#E11D48", unit="hex color", role="Colour of pairs above the threshold and of the threshold line"),
    Param("sig_edge", "color", "#881337", unit="hex color", role="Outline of pairs above the threshold"),
    Param("sig_size", float, 28, unit="pt^2 (marker area)", range=(0, None), role="Marker size of pairs above the threshold"),
    Param("sig_alpha", float, 0.85, unit="alpha [0-1]", range=(0, 1), role="Opacity of pairs above the threshold"),
    Param("callouts", list, [
        ("FOSB", 5.5, 0.993, (20, 0.94)),
        ("TUBB4B", 0.5, 0.964, (20, 0.81)),
        ("IDH2", 1.0, 0.964, (20, 0.68)),
        ("PDCD10", 0.5, 0.939, (20, 0.55)),
    ], unit="data coords", role="Labelled genes: [gene, x, y, [text_x, text_y]] each"),
    Param("callout_size", float, 8.5, unit="pt", range=(0, None), role="Callout label size"),
    Param("badge_size", float, 8.5, unit="pt", range=(0, None), role="Size of the summary badge text"),
    Param("legend_size", float, 9.0, unit="pt", range=(0, None), role="Legend font size"),
    # [Typography]
    Param("title_size", float, 13.0, unit="pt", range=(0, None), role="Panel title font size"),
    Param("axes_label_size", float, 11.5, unit="pt", range=(0, None), role="Axis title font size"),
])


@uses_schema(SCHEMA)
def render_cis_linkage_panel(
    container: Any,
    df: pd.DataFrame,
    params: Mapping[str, Any] | None = None,
) -> tuple[plt.Axes, plt.Axes]:
    """Render a dual-subplot cis-linkage panel (Scatter + Distance Decay Bar).

    Parameters
    ----------
    container : matplotlib.figure.SubFigure or matplotlib.figure.Figure
        Container on which to lay out the two subplots.
    df : pd.DataFrame
        Table with distance_to_tss, pearson_r, is_cis_linked, distance_bin, human_symbol.
    params : Mapping[str, Any], optional
        Visual configuration dictionary.
    """
    if params is None:
        params = {}

    # Grid layout within container
    gs = container.add_gridspec(1, 2, width_ratios=[1.25, 0.75], wspace=params.get("wspace", 0.35))
    ax_scatter = container.add_subplot(gs[0, 0])
    ax_bar = container.add_subplot(gs[0, 1])

    # 1. Scatter: Distance vs Pearson r
    bg = df[~df["is_cis_linked"]]
    sig = df[df["is_cis_linked"]]

    ax_scatter.scatter(
        bg["distance_to_tss"] / 1000.0,
        bg["pearson_r"],
        color=params.get("bg_color", "#94A3B8"),
        alpha=float(params.get("bg_alpha", 0.28)),
        s=float(params.get("bg_size", 13)),
        label=f"Background (n={len(bg):,})",
        edgecolors="none",
    )
    ax_scatter.scatter(
        sig["distance_to_tss"] / 1000.0,
        sig["pearson_r"],
        color=params.get("sig_color", "#E11D48"),
        alpha=float(params.get("sig_alpha", 0.85)),
        s=float(params.get("sig_size", 28)),
        label=f"Cis-linked (n={len(sig):,})",
        edgecolors=params.get("sig_edge", "#881337"),
        linewidths=0.5,
    )

    r_thresh = float(params.get("r_threshold", 0.5))
    ax_scatter.axhline(r_thresh, color=params.get("sig_color", "#E11D48"), linestyle="--", linewidth=1.2, alpha=0.8)
    ax_scatter.set_xlabel("Distance to TSS (kb)", fontsize=params.get("axes_label_size", 11.5), fontweight="bold")
    ax_scatter.set_ylabel("Pearson Correlation (r)", fontsize=params.get("axes_label_size", 11.5), fontweight="bold")
    ax_scatter.set_title(params.get("scatter_title", f"Peak-to-Gene Cis Coupling (N={len(df):,})"),
                         fontsize=params.get("title_size", 13.0), fontweight="bold", pad=8)
    ax_scatter.set_ylim(-1.05, 1.05)
    ax_scatter.set_xlim(-2, 70)
    ax_scatter.grid(True, linestyle=":", alpha=0.45)
    ax_scatter.legend(loc="lower left", fontsize=params.get("legend_size", 9.0), framealpha=0.9)

    # Callout key target genes
    callouts = params.get("callouts", [
        ("FOSB", 5.5, 0.993, (20, 0.94)),
        ("TUBB4B", 0.5, 0.964, (20, 0.81)),
        ("IDH2", 1.0, 0.964, (20, 0.68)),
        ("PDCD10", 0.5, 0.939, (20, 0.55)),
    ])
    for gene, x, y, (tx, ty) in callouts:
        ax_scatter.annotate(
            f"{gene} (r={y:.2f})",
            xy=(x, y),
            xytext=(tx, ty),
            fontsize=float(params.get("callout_size", 8.5)),
            fontweight="bold",
            color="#881337",
            arrowprops=dict(arrowstyle="->", color="#881337", lw=0.8),
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFF1F2", edgecolor="#FDA4AF", alpha=0.92),
        )

    # 2. Bar: Spatial distance decay
    bin_order = params.get("distance_bins", ["<2kb", "2-10kb", "10-50kb", "50-100kb"])
    counts = [sig[sig["distance_bin"] == b].shape[0] for b in bin_order]
    total_sig = max(1, len(sig))
    pcts = [c / total_sig * 100.0 for c in counts]
    bar_colors = params.get("bar_colors", ["#991B1B", "#E11D48", "#F87171", "#CBD5E1"])

    bars = ax_bar.bar(bin_order, counts, color=bar_colors, edgecolor="#475569", linewidth=0.8, width=0.65)
    ax_bar.set_xlabel("Distance Bin", fontsize=params.get("axes_label_size", 11.5), fontweight="bold")
    ax_bar.set_ylabel("Cis-Linked Pairs (Count)", fontsize=params.get("axes_label_size", 11.5), fontweight="bold")
    ax_bar.set_title(params.get("decay_title", "Spatial Distance Decay"),
                     fontsize=params.get("title_size", 13.0), fontweight="bold", pad=8)
    max_c = max(counts) if counts else 100
    ax_bar.set_ylim(0, max_c * 1.22)
    ax_bar.grid(axis="y", linestyle=":", alpha=0.45)
    ax_bar.tick_params(axis="x", rotation=25)

    for bar, c, pct in zip(bars, counts, pcts):
        h = bar.get_height()
        ax_bar.text(bar.get_x() + bar.get_width() / 2.0, h + (max_c * 0.02),
                    f"{c}\n({pct:.1f}%)", ha="center", va="bottom",
                    fontsize=float(params.get("bar_label_size", 8.5)), fontweight="bold")

    # Median summary badge
    ax_bar.text(
        0.95, 0.92,
        "Median r:\n<2kb: +0.22\n>10kb: -0.10",
        transform=ax_bar.transAxes,
        ha="right", va="top",
        fontsize=float(params.get("badge_size", 8.5)),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#F8FAFC", edgecolor="#CBD5E1", alpha=0.92)
    )

    return ax_scatter, ax_bar
