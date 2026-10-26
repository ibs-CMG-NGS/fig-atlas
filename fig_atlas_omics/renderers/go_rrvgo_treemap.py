"""GO rrvgo cluster-treemap renderer, ported from R rrvgo::treemapPlot output.

Draws a two-level treemap from a ``reduceSimMatrix``-shaped data frame
(columns: go, cluster, parent, parentTerm, score, term, size, ...): the
outer blocks are ``parentTerm`` clusters (categorically colored), and each
cluster subdivides into its member GO ``term``s sized by gene-set ``size``.

``score`` is constant across every row of a cluster in the source export
(it's the cluster's own representative score, not a per-term value), so it
cannot drive sub-rectangle area -- ``size`` is the only column that varies
within a cluster and matches the area differences visible in the original
R renders, so it is what this renderer sizes rectangles by.

Layout uses squarify's squarified algorithm. R's treemap package defaults to
a different ("pivotSize") algorithm with a more staircase-like look; a
from-scratch approximation of it (place the largest remaining item as a full
strip, recurse into the leftover rect) was tried and produced a visibly
worse result -- degenerating into thin illegible slivers instead of the
reference's blocky staircase -- so it was reverted in favor of squarify.
"""

from __future__ import annotations

FAMILY = "multivariate"    # gallery family (fig_atlas/family.py): the shape this module draws

import textwrap

import numpy as np
import pandas as pd
import squarify
from matplotlib.patches import Rectangle

from fig_atlas.params import text_param


from fig_atlas.schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("go_rrvgo_treemap", params=[
    Param("size_floor_frac", float, 0.03, unit="fraction of the panel's largest term", range=(0, 1),
          role="Smallest cell size, so zero-size terms stay visible as slivers"),
    Param("cmap", str, "hue", role="Cluster colours: a qualitative colormap name, or 'hue' for an even hue sweep"),
    Param("canvas_width", float, 100.0, unit="treemap units", range=(0, None),
          role="Width of the layout canvas (height follows the axes' aspect)"),
    Param("edge_color", "color", "black", unit="color", role="Cell outline colour"),
    Param("edge_width", float, 1.0, unit="pt", range=(0, None), role="Cell outline width"),
    Param("cluster_border_color", "color", CODE_DEFAULT, unit="color", role="Outline around each cluster (default edge_color)"),
    Param("cluster_border_width", float, CODE_DEFAULT, unit="pt", role="Cluster outline width (default 2.5 x edge_width)"),
    Param("label_min_area_frac", float, 0.004, unit="fraction of the canvas area", range=(0, 1),
          role="Cells smaller than this get no label", tune="raise if small cells are crowded with text"),
    Param("label_wrap_width", int, 14, unit="characters", range=(1, None), role="Wrap cell labels at this width"),
    Param("hub_label_size", float, 11, unit="pt", range=(0, None), role="Cluster (parent term) label size"),
    Param("member_label_size", float, 7.5, unit="pt", range=(0, None), role="Member term label size"),
    Param("max_dispensability", float, None, unit="rrvgo dispensability [0-1]", role="Drop terms more dispensable than this"),
    Param("labels_title", str, "GO rrvgo Cluster Treemap", role="Panel title"),
    Param("title_size", float, 13, unit="pt", role="Panel title font size"),
])


@uses_schema(SCHEMA)
def render_go_rrvgo_treemap(ax, df, params):
    """Draw a GO rrvgo cluster treemap onto ``ax``.

    params: size_col('size'), size_floor_frac(0.03 of that panel's max term
            size -- keeps zero-size terms visible as thin slivers, matching
            the source R renders), cmap(qualitative colormap name or 'hue'
            for an evenly spaced hue sweep), canvas_width(100) -- canvas_height
            is derived automatically from this axes' actual on-figure box
            aspect ratio, not a config value, so the treemap always fills its
            panel with no letterboxing regardless of layout --,
            edge_color, edge_width, label_min_area_frac
            (skip labels below this fraction of canvas area), hub_label_size,
            member_label_size, label_wrap_width, labels_title, title_size,
            cluster_border_color, cluster_border_width (a second, thicker
            outline drawn around each cluster's full bounding rect on top of
            its member cells, so cluster grouping reads at a glance the way
            it does in the source R renders)
    """
    title_sz = params.get("title_size", 13)

    df = df.copy() if df is not None else pd.DataFrame()
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    required = ["term", "parentTerm", "size"]
    if df.empty or not all(c in df.columns for c in required):
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center",
                fontsize=14, transform=ax.transAxes)
        return None

    df["size"] = pd.to_numeric(df["size"], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["term", "parentTerm"])
    if df.empty:
        ax.text(0.5, 0.5, "No valid data to display", ha="center", va="center",
                fontsize=14, transform=ax.transAxes)
        return None

    max_dispensability = params.get("max_dispensability")
    if max_dispensability is not None and "termDispensability" in df.columns:
        disp = pd.to_numeric(df["termDispensability"], errors="coerce").fillna(0.0)
        df = df[disp <= float(max_dispensability)]

    floor_frac = float(params.get("size_floor_frac", 0.03))
    size_floor = df["size"].max() * floor_frac if df["size"].max() > 0 else 1.0
    df["_eff_size"] = df["size"].clip(lower=size_floor)

    canvas_w = float(params.get("canvas_width", 100.0))
    # canvas_height is auto-derived from this axes' actual on-figure box
    # aspect ratio (renderer-independent, same pattern go_dot.py's margin
    # sizing uses) rather than a fixed config value: with set_aspect('equal')
    # below, a canvas whose ratio doesn't match the box it's drawn into
    # letterboxes -- shrinks to fit the limiting dimension and leaves empty
    # space on the sides -- instead of filling the panel.
    try:
        fig_w_in, fig_h_in = ax.figure.get_size_inches()
    except AttributeError:
        fig_w_in, fig_h_in = ax.figure.bbox.width, ax.figure.bbox.height
    box = ax.get_position()
    box_aspect = (box.width * fig_w_in) / (box.height * fig_h_in) if box.height > 0 else 1.0
    canvas_h = canvas_w / box_aspect if box_aspect > 0 else canvas_w
    edge_color = params.get("edge_color", "black")
    edge_width = float(params.get("edge_width", 1.0))
    cluster_border_color = params.get("cluster_border_color", edge_color)
    cluster_border_width = float(params.get("cluster_border_width", edge_width * 2.5))
    wrap_w = int(params.get("label_wrap_width", 14))
    hub_fs = params.get("hub_label_size", 11)
    member_fs = params.get("member_label_size", 7.5)
    label_min_area_frac = float(params.get("label_min_area_frac", 0.004))
    canvas_area = canvas_w * canvas_h

    clusters = (df.groupby("parentTerm")["_eff_size"].sum()
                .sort_values(ascending=False))
    n_clusters = len(clusters)

    cmap_name = params.get("cmap", "hue")
    if cmap_name == "hue":
        hues = np.linspace(0, 1, n_clusters, endpoint=False)
        import colorsys
        colors = [colorsys.hsv_to_rgb(h, 0.55, 0.90) for h in hues]
    else:
        import matplotlib
        cmap = matplotlib.colormaps.get_cmap(cmap_name)
        colors = [cmap(i % cmap.N) for i in range(n_clusters)]
    color_map = dict(zip(clusters.index, colors))

    cluster_sizes = squarify.normalize_sizes(clusters.tolist(), canvas_w, canvas_h)
    cluster_rects = squarify.squarify(cluster_sizes, 0, 0, canvas_w, canvas_h)

    def _label_fits(dx, dy, fs):
        return (dx * dy) / canvas_area >= label_min_area_frac and min(dx, dy) > 0

    for parent_term, rect in zip(clusters.index, cluster_rects):
        sub = df[df["parentTerm"] == parent_term].sort_values("_eff_size", ascending=False)
        color = color_map[parent_term]

        if len(sub) == 1:
            member_rects = [{"x": rect["x"], "y": rect["y"], "dx": rect["dx"], "dy": rect["dy"]}]
        else:
            m_sizes = squarify.normalize_sizes(sub["_eff_size"].tolist(), rect["dx"], rect["dy"])
            member_rects = squarify.squarify(m_sizes, rect["x"], rect["y"], rect["dx"], rect["dy"])

        hub_idx = int(np.argmax(sub["_eff_size"].to_numpy()))
        for i, (_, row) in enumerate(zip(member_rects, sub.itertuples())):
            mrect = member_rects[i]
            ax.add_patch(Rectangle(
                (mrect["x"], mrect["y"]), mrect["dx"], mrect["dy"],
                facecolor=color, edgecolor=edge_color, linewidth=edge_width,
            ))
            if i == hub_idx:
                continue
            term_text = str(getattr(row, "term"))
            if _label_fits(mrect["dx"], mrect["dy"], member_fs):
                wrapped = textwrap.fill(term_text, width=wrap_w, break_long_words=False)
                cx, cy = mrect["x"] + mrect["dx"] / 2, mrect["y"] + mrect["dy"] / 2
                ax.text(cx, cy, wrapped, ha="center", va="center",
                        fontsize=member_fs, color="#222222")

        # A second, thicker outline around the whole cluster on top of its
        # member cells -- makes cluster grouping read at a glance instead of
        # every boundary (cluster and within-cluster alike) looking the same.
        ax.add_patch(Rectangle(
            (rect["x"], rect["y"]), rect["dx"], rect["dy"],
            facecolor="none", edgecolor=cluster_border_color,
            linewidth=cluster_border_width, zorder=5,
        ))

        # The hub label spans the cluster's full bounding rect (not just its
        # own leaf cell), matching the source R renders where the group label
        # floats over the whole colored region rather than being confined to
        # one small box.
        hub_term = str(sub.iloc[hub_idx]["term"])
        if _label_fits(rect["dx"], rect["dy"], hub_fs):
            wrapped = textwrap.fill(hub_term, width=wrap_w, break_long_words=False)
            cx, cy = rect["x"] + rect["dx"] / 2, rect["y"] + rect["dy"] / 2
            ax.text(cx, cy, wrapped, ha="center", va="center",
                    fontsize=hub_fs, fontweight="bold", color="white", zorder=6)

    ax.set_xlim(0, canvas_w)
    ax.set_ylim(0, canvas_h)
    ax.set_aspect("equal")
    ax.invert_yaxis()

    title = text_param(params, "labels_title", "GO rrvgo Cluster Treemap")
    ax.set_title(title, fontsize=title_sz, fontweight="bold")
    return df
