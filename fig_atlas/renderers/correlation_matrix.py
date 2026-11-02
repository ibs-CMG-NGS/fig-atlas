"""correlation_matrix: the correlations among a set of variables -- a lower,
upper or full triangle of cells coloured by r, as squares or as circles whose
area follows |r|, with the values and significance stars written in them.

The r and P of every pair are results, so they come from the analysis script
(fig-atlas docs/howto/analysis_recipes.md, section 4) as a long table -- one
row per pair, the two variable names in row_col and col_col, r in r_col and P
in p_col. A pair given once is drawn on both sides of the diagonal; the
diagonal is 1 unless the table gives it. This renderer never computes a
correlation (ADR 0007).

Returns the cells drawn (row, col, r, p), ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Circle, Rectangle

from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema
from fig_atlas.stats import stars

from ._basic import Signed
from .text_color import readable_text_color

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

SCHEMA = Schema("correlation_matrix", params=[
    # [Data] one row per pair, from the analysis
    Param("row_col", str, "var1", role="Column with the first variable of each pair"),
    Param("col_col", str, "var2", role="Column with the second variable of each pair"),
    Param("r_col", str, "r", role="Column with the pair's correlation, from the analysis"),
    Param("p_col", str, None, role="Column with the pair's P value, from the analysis (default: no stars)"),
    Param("variable_order", list, None, role="Variables in order, top to bottom and left to right (default: data)"),
    Param("variable_labels", dict, {}, open_keys=True, role="Shown name per variable (default: the name)"),
    # [Cells]
    Param("triangle", ("lower", "upper", "full"), "lower", role="Which cells to draw"),
    Param("show_diagonal", bool, False, role="Draw the diagonal (r = 1 unless the table gives it)"),
    Param("mark", ("square", "circle"), "square", role="square: filled cell; circle: area proportional to |r|"),
    Param("circle_scale", float, 0.95, unit="fraction of the cell", range=(0, 1),
          role="Diameter of a circle with |r| = 1"),
    Param("cmap", "cmap", "RdBu_r", role="Diverging colormap of r"),
    Param("r_min", float, -1.0, unit="r", role="r at the low end of the colormap"),
    Param("r_max", float, 1.0, unit="r", role="r at the high end of the colormap"),
    Param("cell_edge_color", "color", "#ffffff", unit="hex color", role="Line between cells"),
    Param("cell_edge_width", float, 0.8, unit="pt", range=(0, None), role="Width of the line between cells"),
    Param("hide_above_p", float, None, unit="P value", range=(0, 1),
          role="Leave a cell blank when its P is at or above this (default: draw every cell)"),
    Param("blank_color", "color", "#f3f4f6", unit="hex color", role="Fill of a blank cell"),
    # [Values]
    Param("show_values", bool, True, role="Write r (and the stars) in each cell"),
    Param("value_format", str, "{r:.2f}\n{stars}",
          role="Cell text; fields r, p and stars (a newline puts the stars under r; empty lines are dropped)"),
    Param("value_size", float, CODE_DEFAULT, unit="pt", range=(0, None), role="Cell text size (default: tick_label_size)"),
    Param("value_line_spacing", float, 1.0, unit="multiple of the font size", range=(0, None),
          role="Spacing of the lines of a cell text"),
    Param("value_light_color", "color", "#ffffff", unit="hex color", role="Text colour on dark cells"),
    Param("value_dark_color", "color", "#111827", unit="hex color", role="Text colour on light cells"),
    Param("sig_thresholds", list, [[0.001, "***"], [0.01, "**"], [0.05, "*"]], unit="P value",
          role="[threshold, symbol] pairs for the stars field (state the rule in the legend)"),
    # [Colourbar]
    Param("show_colorbar", bool, True, role="Show the colourbar"),
    Param("colorbar_label", str, "r", role="Colourbar title"),
    Param("colorbar_loc", ("right", "left", "top", "bottom"), "right", role="Side of the colourbar"),
    Param("colorbar_shrink", float, 0.8, unit="fraction of the axes", range=(0, 1), role="Colourbar length"),
    Param("colorbar_fraction", float, 0.05, unit="fraction of the axes", range=(0, 1), role="Colourbar thickness"),
    Param("colorbar_pad", float, 0.04, unit="fraction of the axes", range=(0, None), role="Gap to the colourbar"),
    Param("colorbar_ticks", list, [-1, -0.5, 0, 0.5, 1], unit="r", role="Colourbar ticks"),
    # [Text]
    Param("labels_title", str, None, role="Panel title (none: no title)"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("axes_label_size", float, None, unit="pt", range=(0, None), role="Colourbar title size (default: rcParams)"),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Variable name size (default: rcParams)"),
    Param("tick_length", float, 0.0, unit="pt", range=(0, None), role="Tick mark length beside the names (0: none)"),
    Param("xtick_rotation", float, 45.0, unit="degrees", role="Rotation of the column names", tune="90 for long names"),
])


def _wanted(i: int, j: int, triangle: str, diagonal: bool) -> bool:
    if i == j:
        return diagonal
    return triangle == "full" or (i > j if triangle == "lower" else i < j)


@uses_schema(SCHEMA)
def render_correlation_matrix(ax, df, params):
    """Draw the correlation matrix onto ``ax``; returns the cells drawn."""
    a_col, b_col, r_col = params.get("row_col", "var1"), params.get("col_col", "var2"), params.get("r_col", "r")
    p_col = params.get("p_col")
    empty = pd.DataFrame(columns=["row", "col", "r", "p"])
    for col in (a_col, b_col, r_col, p_col):
        if col and col not in df.columns:
            raise ValueError(f"correlation_matrix: column {col!r} is missing; the analysis script writes one row "
                             "per pair with r and P (docs/howto/analysis_recipes.md, section 4)")
    pairs = df.dropna(subset=[a_col, b_col, r_col])
    if pairs.empty:
        return empty
    seen = list(dict.fromkeys(list(pairs[a_col]) + list(pairs[b_col])))
    given = params.get("variable_order")
    names = [v for v in given if v in seen] if given else seen
    pos = {v: k for k, v in enumerate(names)}
    r_of, p_of = {}, {}
    for a, b, r, p in zip(pairs[a_col], pairs[b_col], pairs[r_col],
                          pairs[p_col] if p_col else [np.nan] * len(pairs)):
        if a in pos and b in pos:
            for key in ((pos[a], pos[b]), (pos[b], pos[a])):
                r_of[key], p_of[key] = float(r), float(p)
    triangle, diagonal = params.get("triangle", "lower"), bool(params.get("show_diagonal", False))
    given_diagonal = {k for (k, m) in r_of if k == m}       # the rest of the diagonal is an implied 1
    for k in range(len(names)):
        r_of.setdefault((k, k), 1.0)
        p_of.setdefault((k, k), np.nan)
    cells = [(i, j) for i in range(len(names)) for j in range(len(names))
             if (i, j) in r_of and _wanted(i, j, triangle, diagonal)]
    if not cells:
        return empty

    cmap = params.get("cmap", "RdBu_r")
    norm = Normalize(float(params.get("r_min", -1.0)), float(params.get("r_max", 1.0)))
    cutoff = params.get("hide_above_p")
    blank = [c for c in cells if cutoff is not None and not np.isnan(p_of[c]) and p_of[c] >= float(cutoff)]
    shown = [c for c in cells if c not in blank]
    edge, edge_w = params.get("cell_edge_color", "#ffffff"), float(params.get("cell_edge_width", 0.8))
    if params.get("mark", "square") == "circle":
        frame = PatchCollection([Rectangle((j - 0.5, i - 0.5), 1, 1) for i, j in cells], facecolor="none",
                                edgecolor=params.get("blank_color", "#f3f4f6"), linewidth=edge_w, zorder=1)
        ax.add_collection(frame)
        scale = float(params.get("circle_scale", 0.95))
        patches = [Circle((j, i), 0.5 * scale * np.sqrt(abs(r_of[(i, j)]))) for i, j in shown]
    else:
        patches = [Rectangle((j - 0.5, i - 0.5), 1, 1) for i, j in shown]
        if blank:
            ax.add_collection(PatchCollection([Rectangle((j - 0.5, i - 0.5), 1, 1) for i, j in blank],
                                              facecolor=params.get("blank_color", "#f3f4f6"), edgecolor=edge,
                                              linewidth=edge_w, zorder=1))
    coll = PatchCollection(patches, cmap=cmap, norm=norm, edgecolor=edge, linewidth=edge_w, zorder=2)
    coll.set_array(np.array([r_of[c] for c in shown], dtype=float))
    ax.add_collection(coll)

    tick_sz = params.get("tick_label_size")
    if params.get("show_values", True):
        fmt = params.get("value_format", "{r:.2f}\n{stars}")
        thresholds = sorted((float(t), str(s)) for t, s in params.get(
            "sig_thresholds", [[0.001, "***"], [0.01, "**"], [0.05, "*"]]))
        size = params.get("value_size", tick_sz)
        light, dark = params.get("value_light_color", "#ffffff"), params.get("value_dark_color", "#111827")
        circle = params.get("mark", "square") == "circle"
        for (i, j), color in zip(shown, coll.to_rgba(np.array([r_of[c] for c in shown], dtype=float))):
            if i == j and i not in given_diagonal:
                continue                                   # an implied 1 needs no text
            p = p_of[(i, j)]
            text = fmt.format(r=Signed(r_of[(i, j)]), p=p, stars="" if np.isnan(p) else stars(p, thresholds, "")).strip()
            ax.text(j, i, text, ha="center", va="center", linespacing=float(params.get("value_line_spacing", 1.0)),
                    zorder=3,
                    color=dark if circle else readable_text_color(color, light, dark),
                    **({} if size is None else {"fontsize": size}))

    rows = sorted({i for i, _ in cells})
    cols = sorted({j for _, j in cells})
    ax.set_xlim(cols[0] - 0.5, cols[-1] + 0.5)
    ax.set_ylim(rows[-1] + 0.5, rows[0] - 0.5)                 # first variable at the top
    ax.set_aspect("equal")
    labels = params.get("variable_labels", {})
    rot = float(params.get("xtick_rotation", 45.0))
    ax.set_xticks(cols, [str(labels.get(names[j], names[j])) for j in cols], rotation=rot,
                  ha="right" if rot % 180 else "center", rotation_mode="anchor")
    ax.set_yticks(rows, [str(labels.get(names[i], names[i])) for i in rows])
    ax.tick_params(length=float(params.get("tick_length", 0.0)), **({} if tick_sz is None else {"labelsize": tick_sz}))
    for spine in ax.spines.values():
        spine.set_visible(False)
    if params.get("show_colorbar", True):
        cbar = ax.figure.colorbar(coll, ax=ax, location=params.get("colorbar_loc", "right"),
                                  shrink=float(params.get("colorbar_shrink", 0.8)),
                                  fraction=float(params.get("colorbar_fraction", 0.05)),
                                  pad=float(params.get("colorbar_pad", 0.04)),
                                  ticks=params.get("colorbar_ticks", [-1, -0.5, 0, 0.5, 1]))
        cbar.set_label(params.get("colorbar_label", "r"), fontsize=params.get("axes_label_size"))
        cbar.outline.set_visible(False)
        if tick_sz is not None:
            cbar.ax.tick_params(labelsize=tick_sz)
    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=params.get("title_size", 8.0))
    return pd.DataFrame([{"row": names[i], "col": names[j], "r": r_of[(i, j)],
                          "p": None if np.isnan(p_of[(i, j)]) else p_of[(i, j)]} for i, j in cells],
                        columns=empty.columns)
