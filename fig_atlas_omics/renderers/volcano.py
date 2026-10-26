"""Volcano plot renderer.

Draws a differential-expression volcano plot onto a Matplotlib Axes. All visual
attributes are read from a ``params`` dict via ``.get()`` so nothing is hardcoded.
"""

from __future__ import annotations

FAMILY = "xy"    # gallery family (fig_atlas/family.py): the shape this module draws

from fig_atlas.recipes import recipe
from fig_atlas.recipes import render as render_recipe
from fig_atlas.schema import Param, Schema, uses_schema

SCHEMA = Schema("volcano", params=[
    # [Significance and colours]
    Param("log2fc_threshold", float, 1.0, unit="log2 fold change", range=(0, None),
          role="|log2FC| cut-off for up / down points", tune="raise to call only stronger changes"),
    Param("padj_threshold", float, 0.05, unit="adjusted P", range=(0, 1), role="padj cut-off for up / down points"),
    Param("up_color", "color", "#ff0000", unit="hex color", role="Colour of up-regulated points"),
    Param("down_color", "color", "#0000ff", unit="hex color", role="Colour of down-regulated points"),
    Param("ns_color", "color", "#808080", unit="hex color", role="Colour of non-significant points"),
    Param("dot_size", float, 20, unit="pt^2 (marker area)", range=(0, None), role="Point size", tune="lower for dense plots"),
    # [Cut-off lines]
    Param("show_cutoff_lines", bool, True, role="Draw the dashed cut-off lines"),
    Param("cutoff_line_color", "color", "black", unit="color", role="Cut-off line colour"),
    Param("cutoff_line_style", str, "--", role="Cut-off line style (matplotlib)"),
    Param("cutoff_line_width", float, 1, unit="pt", range=(0, None), role="Cut-off line width"),
    Param("cutoff_line_alpha", float, 0.5, unit="[0-1] opacity", range=(0, 1), role="Cut-off line opacity"),
    # [Gene labels]
    Param("annotation_mode", ("none", "top_n", "custom"), "none",
          role="Label genes: none, the top_n strongest (|log2FC| x -log10 padj), or annotation_custom_genes"),
    Param("annotation_top_n", int, 10, unit="genes", range=(0, None), role="Genes labelled in top_n mode"),
    Param("annotation_custom_genes", list, None, role="Genes labelled in custom mode (matched case-insensitively)"),
    Param("annotation_label_size", int, 8, unit="pt", range=(0, None), role="Gene label size"),
    Param("annotation_iter_lim", int, 1000, unit="iterations", range=(1, None),
          role="Label-placement steps (a fixed count, so every build places the labels the same way)",
          tune="raise if labels still overlap; lower for a faster build"),
    # [Axes and text]
    Param("x_min", float, None, unit="log2 fold change", role="Lower x limit (both x_min and x_max needed)"),
    Param("x_max", float, None, unit="log2 fold change", role="Upper x limit"),
    Param("y_min", float, None, unit="-log10 padj", role="Lower y limit (both y_min and y_max needed)"),
    Param("y_max", float, None, unit="-log10 padj", role="Upper y limit"),
    Param("labels_title", str, None, role="Panel title"),
    Param("labels_xlabel", str, "Log2 Fold Change", role="x-axis title"),
    Param("labels_ylabel", str, "-Log10(Padj)", role="y-axis title"),
    Param("title_size", float, 10, unit="pt", role="Panel title font size"),
    Param("show_xticklabels", bool, True, role="Show x tick labels"),
    Param("show_yticklabels", bool, True, role="Show y tick labels"),
    Param("show_legend", bool, True, role="Show the up / down / ns legend"),
    Param("legend_position", str, "best", role="Legend anchor (matplotlib loc)"),
])


# The volcano plot as a recipe of the generic threshold scatter (roadmap 6a.3):
# effect = log2 fold change on x, significance = padj shown as -log10 on y.
RECIPE = recipe(
    "volcano", "fig_atlas.renderers.threshold_scatter:render_threshold_scatter",
    defaults={
        "x_col": "log2FC", "y_col": "padj", "y_transform": "neg_log10",
        "effect_col": "log2FC", "sig_col": "padj",
        "missing_text": "Required columns not found:\nlog2FC and padj", "missing_text_size": 14,
        "ns_alpha": 0.6, "sig_alpha": 0.6,
        "cutoff_lines": [{"axis": "h", "at": "sig"}, {"axis": "v", "at": "effect"},
                         {"axis": "v", "at": "-effect"}],
        "grid": True, "legend_fontsize": "small", "fit_axes_width": True,
        "labels_xlabel": "Log2 Fold Change", "labels_ylabel": "-Log10(Padj)",
    },
    surface=SCHEMA.all(),
    aliases={"log2fc_threshold": "effect_threshold", "padj_threshold": "sig_threshold",
             "annotation_mode": "label_mode", "annotation_top_n": "label_top_n",
             "annotation_custom_genes": "label_custom", "annotation_label_size": "label_size",
             "annotation_iter_lim": "label_iter_lim"},
    doc="fig_atlas_omics/contracts/de_go_bundle_contract.md",
)


@uses_schema(SCHEMA)
def render_volcano(ax, df, params):
    """Volcano plot: the ``volcano`` recipe of render_threshold_scatter. Returns
    the table with a ``regulation`` column (up / down / ns)."""
    return render_recipe(RECIPE, ax, df, params=params)
