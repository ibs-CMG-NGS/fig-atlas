"""MA plot renderer (mean expression/accessibility vs log fold change).

Companion QC plot to the volcano plot: same UP/DOWN/NS significance
classification, but x-axis is magnitude (mean count/accessibility) instead
of significance (-log10 padj), showing whether fold-change calls are
biased toward low- or high-abundance features.
"""

from __future__ import annotations

FAMILY = "xy"    # gallery family (fig_atlas/family.py): the shape this module draws

from fig_atlas.recipes import recipe
from fig_atlas.recipes import render as render_recipe
from fig_atlas.schema import Param, Schema, uses_schema

SCHEMA = Schema("ma_plot", params=[
    # [Significance and colours]
    Param("padj_threshold", float, 0.05, unit="adjusted P", range=(0, 1), role="padj cut-off for up / down points"),
    Param("log2fc_threshold", float, 0.585, unit="log2 fold change", range=(0, None),
          role="|log2FC| cut-off for up / down points (0.585 = 1.5-fold)"),
    Param("up_color", "color", "#ff0000", unit="hex color", role="Colour of up points"),
    Param("down_color", "color", "#0000ff", unit="hex color", role="Colour of down points"),
    Param("ns_color", "color", "#808080", unit="hex color", role="Colour of non-significant points"),
    Param("dot_size", float, 10, unit="pt^2 (marker area)", range=(0, None), role="Point size"),
    Param("dot_alpha", float, 0.5, unit="[0-1] opacity", range=(0, 1), role="Point opacity"),
    # [Reference lines]
    Param("show_cutoff_lines", bool, True, role="Draw y = 0 and +/- log2fc_threshold lines"),
    Param("cutoff_line_color", "color", "black", unit="color", role="Reference line colour"),
    Param("cutoff_line_style", str, "--", role="Style of the threshold lines (matplotlib)"),
    Param("cutoff_line_width", float, 1, unit="pt", range=(0, None), role="Reference line width"),
    Param("cutoff_line_alpha", float, 0.5, unit="[0-1] opacity", range=(0, 1), role="Reference line opacity"),
    # [Axes and text]
    Param("x_min", float, None, unit="log10 mean (data coords)", role="Lower x limit"),
    Param("x_max", float, None, unit="log10 mean (data coords)", role="Upper x limit"),
    Param("y_min", float, None, unit="log2 fold change", role="Lower y limit"),
    Param("y_max", float, None, unit="log2 fold change", role="Upper y limit"),
    Param("labels_title", str, "MA Plot", role="Panel title"),
    Param("labels_xlabel", str, "log10(Mean Accessibility)", role="x-axis title"),
    Param("labels_ylabel", str, "Log2 Fold Change", role="y-axis title"),
    Param("title_size", float, 13, unit="pt", role="Panel title font size"),
    Param("axes_label_size", float, 11, unit="pt", role="Axis title font size"),
    Param("tick_label_size", float, 8, unit="pt", role="Tick and legend font size"),
    Param("show_legend", bool, True, role="Show the legend"),
    Param("legend_position", str, "best", role="Legend anchor (matplotlib loc)"),
])


# The MA plot as a recipe of the generic threshold scatter (roadmap 6a.3):
# x = log10(mean), effect = log2 fold change on y, significance = padj.
RECIPE = recipe(
    "ma_plot", "fig_atlas.renderers.threshold_scatter:render_threshold_scatter",
    defaults={
        "x_col": "baseMean", "x_transform": "log10", "y_col": "log2FoldChange",
        "effect_col": "log2FoldChange", "sig_col": "padj",
        "empty_is_missing": True, "missing_text": "No data to display",
        "ns_alpha": 0.5, "sig_alpha": 1.0, "ns_zorder": 2, "sig_zorder": 3,
        "cutoff_lines": [{"axis": "h", "at": 0},
                         {"axis": "h", "at": "effect", "width_scale": 0.6, "alpha_scale": 0.7, "style": ":"},
                         {"axis": "h", "at": "-effect", "width_scale": 0.6, "alpha_scale": 0.7, "style": ":"}],
        "legend_framealpha": 0.9,
        "effect_threshold": 0.585, "dot_size": 10,
        "labels_title": "MA Plot", "labels_xlabel": "log10(Mean Accessibility)", "labels_ylabel": "Log2 Fold Change",
        "title_size": 13, "axes_label_size": 11, "tick_label_size": 8,
    },
    surface=SCHEMA.all(),
    aliases={"log2fc_threshold": "effect_threshold", "padj_threshold": "sig_threshold",
             "dot_alpha": "ns_alpha"},
    doc="fig_atlas_omics/contracts/de_go_bundle_contract.md",
)


@uses_schema(SCHEMA)
def render_ma_plot(ax, df, params):
    """MA plot (mean vs log2 fold change): the ``ma_plot`` recipe of
    render_threshold_scatter. Expects DESeq2-style ``baseMean``,
    ``log2FoldChange`` and ``padj`` columns."""
    return render_recipe(RECIPE, ax, df, params=params)
