"""Renderer for TF gene expression profile bar + scatter charts with ANOVA and asterisks."""

from __future__ import annotations

FAMILY = "column"    # gallery family (fig_atlas/family.py): the shape this module draws

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fig_atlas import stats as fa_stats
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("tf_expression_bars", params=[
    # [Grid of genes]
    Param("n_cols", int, CODE_DEFAULT, unit="genes per row", range=(1, None), role="Columns of the gene grid (default: up to 7)"),
    Param("hspace", float, 0.40, unit="fraction of a panel's height", role="Gap between grid rows"),
    Param("wspace", float, 0.28, unit="fraction of a panel's width", role="Gap between grid columns"),
    Param("gene_family_map", dict, {}, open_keys=True, role="Family tag shown under each gene's name (gene -> text)"),
    Param("family_wrap_width", int, None, unit="characters", role="Wrap the family tag at this width"),
    # [Bars, points and error bars per condition]
    Param("condition_colors", list, CODE_DEFAULT, unit="hex colors in condition order",
          role="Colour per condition (default: grey, red, orange, purple, blue)"),
    Param("short_condition_labels", list, ["Cont", "D1", "D3", "24h", "48h"], role="x labels of the conditions"),
    Param("bar_width", float, 0.65, unit="data units (conditions are 1 apart)", range=(0, 1), role="Bar width"),
    Param("bar_alpha", float, 0.70, unit="[0-1] opacity", range=(0, 1), role="Bar opacity"),
    Param("bar_edgewidth", float, 0.8, unit="pt", range=(0, None), role="Bar outline width"),
    Param("errorbar_linewidth", float, 0.8, unit="pt", range=(0, None), role="Error bar and cap line width"),
    Param("capsize", float, 2.5, unit="pt", range=(0, None), role="Error bar cap length"),
    Param("show_points", bool, True, role="Overlay each replicate as a point"),
    Param("point_size", float, 24.0, unit="pt^2 (marker area)", range=(0, None), role="Replicate point size"),
    Param("point_edgewidth", float, 0.6, unit="pt", range=(0, None), role="Replicate point outline width"),
    Param("point_jitter", float, 0.12, unit="data units", range=(0, None), role="Horizontal scatter of the points"),
    Param("point_seed", int, 42, unit="random seed", role="Seed for the jitter, so the layout is reproducible"),
    # [Statistics]
    Param("show_anova", bool, True, role="Print the one-way ANOVA P above each gene"),
    Param("anova_font_size", float, 7.5, unit="pt", range=(0, None), role="ANOVA text size"),
    Param("show_asterisks", bool, True, role="Mark conditions that differ from control with stars"),
    Param("star_font_size", float, 9.5, unit="pt", range=(0, None), role="Star size"),
    Param("stat_test", ("welch", "student", "mannwhitney"), "welch",
          role="Test of each condition against control (Welch t-test, Student t-test, Mann-Whitney U)"),
    Param("stat_correction", ("none", "bonferroni", "holm", "bh"), "none",
          role="Multiple-testing correction applied before the stars (bh = Benjamini-Hochberg FDR)"),
    Param("stat_correction_scope", ("gene", "figure"), "gene",
          role="Correction family: each gene's comparisons, or every comparison in this grid"),
    Param("star_thresholds", list, [[0.001, "***"], [0.01, "**"], [0.05, "*"]], unit="P (adjusted)",
          role="[threshold, symbol] pairs, ascending; a star needs P below the threshold"),
    Param("record_statistics", bool, True,
          role="Save the test table with the figure (published as figure_NN_statistics/)"),
    Param("stats_table_name", str, "tf_expression_tests", role="File name (no extension) of the saved test table"),
    Param("y_headroom", float, 1.35, unit="x the tallest bar", range=(1, None), role="y range above the bars",
          tune="raise if stars or the ANOVA text clip at the top"),
    # [Text and axes]
    Param("gene_title_size", float, 10.5, unit="pt", range=(0, None), role="Gene name (panel title) size"),
    Param("title_pad", float, 4, unit="pt", role="Gap between gene name and plot"),
    Param("show_ylabel", bool, True, role="Show the y-axis title"),
    Param("ylabel", str, "Norm. Counts", role="y-axis title"),
    Param("ylabel_size", float, 9.0, unit="pt", range=(0, None), role="y-axis title size"),
    Param("tick_label_size", float, 8.0, unit="pt", range=(0, None), role="Tick label size"),
    Param("xtick_rotation", float, 0, unit="degrees", role="Condition label rotation"),
    Param("spine_width", float, 0.8, unit="pt", range=(0, None), role="Axis line width"),
])


_DEFAULT_COND_COLORS = [
    "#4b5563",  # Control (Slate Gray)
    "#dc2626",  # Acute 1D (Vibrant Red)
    "#ea580c",  # Acute 3D (Orange)
    "#7c3aed",  # Chronic 24H (Purple)
    "#2563eb",  # Chronic 48H (Blue)
]


@uses_schema(SCHEMA)
def gene_tests(gene_symbol: str, cond_names: list[str], replicate_groups: list, params: dict) -> pd.DataFrame:
    """One gene's tests (fig_atlas.stats): each condition against the first
    (control), plus the one-way ANOVA over all conditions, as table rows.
    ``p_adj`` and ``stars`` are filled per correction family by the caller."""
    n = min(len(cond_names), len(replicate_groups))
    groups = {cond_names[i]: replicate_groups[i] for i in range(n)}
    t = fa_stats.compare_to_control(groups, control=cond_names[0], test=params.get("stat_test", "welch"))
    f, p_anova = fa_stats.anova([g for g in replicate_groups if len(g) > 0])
    t.insert(0, "gene", gene_symbol)
    t["anova_F"], t["anova_p"] = f, p_anova
    return t


def _correct(table: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Add p_adj (correction over ``table`` as one family) and stars."""
    table = table.copy()
    table["correction"] = params.get("stat_correction", "none")
    table["p_adj"] = fa_stats.adjust(table["p"], params.get("stat_correction", "none"))
    thresholds = params.get("star_thresholds", [[0.001, "***"], [0.01, "**"], [0.05, "*"]])
    table["stars"] = [fa_stats.stars(p, thresholds) for p in table["p_adj"]]
    return table


def describe_stars(params: dict) -> str:
    """Legend phrase for the stars this renderer draws with ``params``, e.g.
    "Welch's t-test versus control (*P < 0.05, **P < 0.01, ***P < 0.001)".
    Record it as a live claim so the legend follows the config."""
    scope = params.get("stat_correction_scope", "gene")
    return fa_stats.describe(params.get("stat_test", "welch"), params.get("stat_correction", "none"),
                             params.get("star_thresholds", [[0.001, "***"], [0.01, "**"], [0.05, "*"]]),
                             family="within each gene" if scope == "gene" else "across all genes in the panel")


def render_single_tf_expression_scatter_bar(
    ax: plt.Axes,
    gene_symbol: str,
    cond_names: list[str],
    replicate_groups: list[list[float]],
    params: dict | None = None,
    tests: pd.DataFrame | None = None,
) -> None:
    """Render a single TF gene expression chart as Scatter + Bar plot with ANOVA and Asterisks.

    Args:
        ax: Matplotlib Axes.
        gene_symbol: Gene identifier (e.g. 'KLF10').
        cond_names: List of condition names (e.g. ['Control', 'Acute 1D', ...]).
        replicate_groups: List of replicate arrays/lists corresponding to each condition.
        params: Config parameters dict.
        tests: This gene's rows of the test table (gene_tests + correction);
            computed here, corrected per gene, when not given.
    """
    params = params or {}
    if tests is None:
        tests = _correct(gene_tests(gene_symbol, cond_names, replicate_groups, params), params)
    colors = params.get("condition_colors", _DEFAULT_COND_COLORS)
    if len(colors) < len(cond_names):
        colors = colors * (len(cond_names) // len(colors) + 1)

    n_conds = len(cond_names)
    x = np.arange(n_conds)
    width = float(params.get("bar_width", 0.65))

    # Calculate statistics
    means = [float(np.mean(g)) if len(g) > 0 else 0.0 for g in replicate_groups]
    sems = [
        float(np.std(g, ddof=1) / np.sqrt(len(g))) if len(g) > 1 else 0.0
        for g in replicate_groups
    ]

    # One-way ANOVA (from the test table)
    p_anova = float(tests["anova_p"].iloc[0]) if len(tests) else np.nan

    # 1. Bars (semi-transparent filled)
    bar_alpha = float(params.get("bar_alpha", 0.70))
    ax.bar(
        x, means, yerr=sems, width=width,
        color=colors[:n_conds], alpha=bar_alpha,
        edgecolor="#1f2937", linewidth=float(params.get("bar_edgewidth", 0.8)),
        capsize=float(params.get("capsize", 2.5)),
        error_kw={"elinewidth": float(params.get("errorbar_linewidth", 0.8)), "ecolor": "#111827",
                  "capthick": float(params.get("errorbar_linewidth", 0.8))},
        zorder=2
    )

    # 2. Overlaid Replicate Scatter Points
    show_points = params.get("show_points", True)
    if show_points:
        rng = np.random.default_rng(params.get("point_seed", 42))
        point_size = float(params.get("point_size", 24.0))
        jitter_range = float(params.get("point_jitter", 0.12))
        for gi, grp in enumerate(replicate_groups):
            vals = np.array(grp)[~np.isnan(grp)]
            if len(vals) == 0:
                continue
            jitter = rng.uniform(-jitter_range, jitter_range, len(vals))
            ax.scatter(
                x[gi] + jitter, vals,
                s=point_size, color="#111827", edgecolors="white",
                linewidths=float(params.get("point_edgewidth", 0.6)), alpha=0.90, zorder=4
            )

    # 3. Asterisks vs Control (index 0)
    show_asterisks = params.get("show_asterisks", True)
    c_ctrl = np.array(replicate_groups[0])[~np.isnan(replicate_groups[0])]
    all_vals = [v for g in replicate_groups for v in g if not np.isnan(v)]
    data_max = max(all_vals) if all_vals else 1.0
    bar_tops = [m + s for m, s in zip(means, sems)]
    gap = data_max * 0.07 if data_max > 0 else 0.1

    star_of = dict(zip(tests["group"], tests["stars"]))
    if show_asterisks and len(c_ctrl) > 1:
        for gi in range(1, n_conds):
            grp = np.array(replicate_groups[gi])[~np.isnan(replicate_groups[gi])]
            if len(grp) < 1:
                continue
            star = star_of.get(cond_names[gi], "")
            if star:
                y_pos = max(bar_tops[gi], max(grp) if len(grp) > 0 else bar_tops[gi]) + gap * 0.3
                ax.text(
                    x[gi], y_pos, star,
                    ha="center", va="bottom",
                    fontsize=float(params.get("star_font_size", 9.5)),
                    fontweight="bold", color="#b91c1c", zorder=5
                )

    # Titles & ANOVA badge
    title_size = float(params.get("gene_title_size", 10.5))
    family_tag = params.get("gene_family_map", {}).get(gene_symbol, "")
    display_title = f"${gene_symbol}$"
    if family_tag:
        # family_wrap_width (optional) wraps long family tags so neighbouring
        # panel titles don't run into each other in narrow grids.
        wrap_w = params.get("family_wrap_width")
        tag = f"({family_tag})"
        if wrap_w:
            import textwrap
            tag = textwrap.fill(tag, width=int(wrap_w), break_long_words=False)
        display_title += f"\n{tag}"
    ax.set_title(display_title, fontsize=title_size, fontweight="bold", pad=float(params.get("title_pad", 4)))

    show_anova = params.get("show_anova", True)
    if show_anova and not np.isnan(p_anova):
        anova_str = f"ANOVA P < 0.001" if p_anova < 0.001 else f"ANOVA P = {p_anova:.3f}"
        ax.text(
            0.96, 0.95, anova_str, transform=ax.transAxes,
            fontsize=float(params.get("anova_font_size", 7.5)),
            ha="right", va="top", color="#4b5563",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#f3f4f6", edgecolor="none", alpha=0.85),
            zorder=6
        )

    # Axes setup
    tick_label_size = float(params.get("tick_label_size", 8.0))
    ylabel_size = float(params.get("ylabel_size", 9.0))

    ax.set_xticks(x)
    short_labels = params.get("short_condition_labels", ["Cont", "D1", "D3", "24h", "48h"])
    # Condition label rotation (deg); tilt narrow mini-panels whose labels
    # would otherwise run together. 0 keeps them horizontal and centred.
    rot = float(params.get("xtick_rotation", 0))
    ax.set_xticklabels(short_labels[:n_conds], fontsize=tick_label_size, rotation=rot,
                       ha="center" if rot in (0, 90) else "right",
                       rotation_mode="default" if rot in (0, 90) else "anchor")
    ax.tick_params(axis="y", labelsize=tick_label_size)

    if params.get("show_ylabel", True):
        ax.set_ylabel(params.get("ylabel", "Norm. Counts"), fontsize=ylabel_size, fontweight="bold")

    # Grid & Spines
    ax.yaxis.grid(True, linestyle="--", alpha=0.4, color="#e5e7eb", zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(float(params.get("spine_width", 0.8)))
    ax.spines["bottom"].set_linewidth(float(params.get("spine_width", 0.8)))

    y_headroom = float(params.get("y_headroom", 1.35))
    y_max_limit = max(data_max, max(bar_tops) if bar_tops else 1.0) * y_headroom
    ax.set_ylim(0, max(y_max_limit, 1.0))


@uses_schema(SCHEMA)
def render_tf_expression_scatter_grid(
    sf_or_fig,
    genes_data: list[dict],
    cond_names: list[str],
    params: dict | None = None,
) -> list[plt.Axes]:
    """Render a grid of mini scatter + bar charts for a list of TF genes.

    genes_data format:
      [
        {"symbol": "JUN", "family": "bZIP", "replicates": [[...], [...], ...]},
        ...
      ]
    """
    params = params or {}
    n_genes = len(genes_data)
    if n_genes == 0:
        return []

    n_cols = int(params.get("n_cols", min(n_genes, 7)))
    n_rows = int(np.ceil(n_genes / n_cols))

    wspace = float(params.get("wspace", 0.28))
    hspace = float(params.get("hspace", 0.40))

    # Tests first (fig_atlas.stats), corrected per gene or over the whole grid,
    # then saved with the figure; the panels draw their stars from this table.
    per_gene = [gene_tests(g["symbol"], cond_names, g["replicates"], params) for g in genes_data]
    if params.get("stat_correction_scope", "gene") == "figure":
        table = _correct(pd.concat(per_gene, ignore_index=True), params)
    else:
        table = pd.concat([_correct(t, params) for t in per_gene], ignore_index=True)
    starts = np.concatenate([[0], np.cumsum([len(t) for t in per_gene])[:-1]]).astype(int)  # each gene's first row
    if params.get("record_statistics", True):
        fa_stats.record(table, name=params.get("stats_table_name", "tf_expression_tests"),
                        title="Each condition vs control per gene, with one-way ANOVA")

    gs = sf_or_fig.add_gridspec(n_rows, n_cols, wspace=wspace, hspace=hspace)
    axes = []

    for i, ginfo in enumerate(genes_data):
        row = i // n_cols
        col = i % n_cols
        ax = sf_or_fig.add_subplot(gs[row, col])
        render_single_tf_expression_scatter_bar(
            ax=ax,
            gene_symbol=ginfo["symbol"],
            cond_names=cond_names,
            replicate_groups=ginfo["replicates"],
            params={
                **params,
                "gene_family_map": {ginfo["symbol"]: ginfo.get("family", "")},
                "show_ylabel": (col == 0),
                "point_seed": 42 + i,
            },
            tests=table.iloc[starts[i]:starts[i] + len(per_gene[i])],
        )
        axes.append(ax)

    return axes
