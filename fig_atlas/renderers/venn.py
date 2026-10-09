"""Venn diagram renderer (2- or 3-set), ported from venn_diagram_bundle."""

from __future__ import annotations

import pandas as pd


from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("venn", params=[
    Param("set_labels", list, [], role="Sets to draw (2 or 3): values of the long table's dataset column"),
    Param("display_labels", list, [], role="Names printed for the sets (default: set_labels)"),
    Param("unit", str, "Gene", role="What is counted, used in the title (e.g. Gene, Peak)"),
    Param("filter_name", str, "All Genes", role="Name of the filter, used in the title"),
    Param("title_size", float, 12, unit="pt", role="Panel title font size"),
])


@uses_schema(SCHEMA)
def render_venn(ax, df, params):
    """Draw a 2- or 3-set Venn diagram on ``ax``.

    params: set_labels(list, 2 or 3), unit('Gene'|'Peak'), filter_name(str)
    Requires matplotlib_venn; falls back to an inline message if unavailable.
    """
    def _as_list(v):
        if isinstance(v, str):
            import ast
            try:
                return list(ast.literal_eval(v))
            except Exception:
                return []
        return list(v) if v else []

    labels = _as_list(params.get('set_labels', []))
    # Short labels for display only; set_labels must match the 'dataset' column.
    display = _as_list(params.get('display_labels', [])) or labels
    unit = params.get('unit', 'Gene')
    filter_name = params.get('filter_name', 'All Genes')
    title_sz = params.get('title_size', 12)

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or 'dataset' not in df.columns or 'item' not in df.columns or len(labels) < 2:
        ax.text(0.5, 0.5, "No overlap data to plot.", ha='center', va='center',
                transform=ax.transAxes, color='#888888')
        return None

    gene_sets = [set(df[df['dataset'] == lbl]['item'].dropna().unique()) for lbl in labels]

    try:
        from matplotlib_venn import venn2, venn3, venn2_circles, venn3_circles
    except ImportError:
        ax.text(0.5, 0.5, "matplotlib_venn is required to render this figure.\n"
                          "Install it with:  pip install matplotlib-venn",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        return gene_sets

    if len(gene_sets) == 2:
        venn = venn2(gene_sets, set_labels=display, ax=ax, alpha=0.6)
        venn2_circles(gene_sets, ax=ax, linewidth=1.5)
        for rid, color in (('10', '#ff9999'), ('01', '#9999ff'), ('11', '#cc99cc')):
            patch = venn.get_patch_by_id(rid)
            if patch:
                patch.set_color(color)
    elif len(gene_sets) == 3:
        venn = venn3(gene_sets, set_labels=display, ax=ax, alpha=0.6)
        venn3_circles(gene_sets, ax=ax, linewidth=1.5)
        colors = {
            '100': '#ff9999', '010': '#9999ff', '001': '#99ff99',
            '110': '#ffcc99', '101': '#ffff99', '011': '#99ffff', '111': '#cccccc',
        }
        for rid, color in colors.items():
            patch = venn.get_patch_by_id(rid)
            if patch:
                patch.set_color(color)
    else:
        ax.text(0.5, 0.5, "Venn diagram requires 2-3 datasets.", ha='center', va='center',
                transform=ax.transAxes, color='#888888')
        return gene_sets

    title = f"{unit} Overlap — {filter_name}\n"
    if len(gene_sets) == 2:
        common = gene_sets[0] & gene_sets[1]
        unique_0 = gene_sets[0] - gene_sets[1]
        unique_1 = gene_sets[1] - gene_sets[0]
        title += (f"Common: {len(common)}   |   {display[0]}-only: {len(unique_0)}"
                  f"   |   {display[1]}-only: {len(unique_1)}")
    else:
        common = gene_sets[0] & gene_sets[1] & gene_sets[2]
        title += f"Common to all: {len(common)}"

    ax.set_title(title, fontsize=title_sz, fontweight='bold', pad=14)
    return gene_sets
