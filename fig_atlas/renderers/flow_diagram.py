"""flow_diagram: boxes joined by arrows -- pipelines, architectures, decision
and state diagrams drawn from a table, so a schematic is code like any other
panel (it rebuilds, passes preflight, and its text follows the config).

Data: one row per node, with columns named by the *_col params:
    id     unique name, used by the edges
    x, y   top-left corner, in the diagram's units (e.g. mm; y grows downward
           unless y_down is false)
    w, h   width and height
    title  bold first line (optional)
    body   further lines, newline-separated (optional)
    kind   "box" (default), "group" (dashed container drawn underneath, title
           at its top-left) or "text" (no frame)
    fill   fill colour for this node (optional; default box_fill)
    color  text colour for this node (optional; default text_color / body_color)
Edges come from the ``edges`` param: a list of {"from", "to"} with optional
"label", "from_side"/"to_side" ("l", "r", "t", "b"; default: across the gap
between the two nodes), "from_at"/"to_at" (where on that side, 0-1 from the
left or top; default 0.5), "rad" (curvature) and "style" ("solid"/"dashed").

Returns the node rows drawn, ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from fig_atlas.schema import Param, Schema, uses_schema

MM_PER_PT = 25.4 / 72
VERTICAL_SLOPE = 0.05     # an arrow this close to vertical (dx / dy) counts as vertical for its label

SCHEMA = Schema("flow_diagram", params=[
    # [Data]
    Param("id_col", str, "id", role="Column with each node's unique name (edges refer to it)"),
    Param("x_col", str, "x", role="Column with the node's left edge (diagram units)"),
    Param("y_col", str, "y", role="Column with the node's top edge (diagram units)"),
    Param("w_col", str, "w", role="Column with the node's width"),
    Param("h_col", str, "h", role="Column with the node's height"),
    Param("title_col", str, "title", role="Column with the node's bold first line"),
    Param("body_col", str, "body", role="Column with further lines, separated by newlines"),
    Param("kind_col", str, "kind", role="Column with the node kind: box, group or text"),
    Param("fill_col", str, "fill", role="Column with a node's own fill colour (empty: box_fill)"),
    Param("color_col", str, "color", role="Column with a node's own text colour (empty: text_color, body_color)"),
    Param("edges", list, [], role="Arrows: list of {from, to, label?, from_side?, to_side?, rad?, style?}"),
    # [Canvas]
    Param("xlim", list, None, unit="diagram units [min, max]", role="Horizontal extent (default: the nodes)"),
    Param("ylim", list, None, unit="diagram units [min, max]", role="Vertical extent (default: the nodes)"),
    Param("y_down", bool, True, role="y grows downward, like a page (false: upward, like a plot)"),
    Param("units_per_mm", float, 1.0, unit="diagram units per mm", range=(0, None),
          role="Scale of the diagram units, used to place body text below a title",
          tune="1 when the diagram is laid out in mm"),
    # [Boxes]
    Param("box_fill", "color", "#F3F4F6", unit="hex color", role="Box fill"),
    Param("box_edge", "color", "#4B5563", unit="hex color", role="Box outline"),
    Param("box_linewidth", float, 0.6, unit="pt", range=(0, None), role="Box outline width"),
    Param("box_radius", float, 1.0, unit="diagram units", range=(0, None), role="Corner radius of boxes and groups",
          tune="0 for square corners"),
    Param("group_edge", "color", "#9CA3AF", unit="hex color", role="Group outline"),
    Param("group_fill", "color", "none", unit="hex color or none", role="Group fill"),
    Param("group_linestyle", str, "--", role="Group outline style (matplotlib linestyle)"),
    Param("group_linewidth", float, 0.6, unit="pt", range=(0, None), role="Group outline width"),
    # [Text]
    Param("title_size", float, 7.0, unit="pt", range=(0, None), role="Node title size"),
    Param("body_size", float, 6.0, unit="pt", range=(0, None), role="Node body size"),
    Param("title_weight", str, "bold", role="Node title weight"),
    Param("text_color", "color", "#111827", unit="hex color", role="Title colour"),
    Param("body_color", "color", "#374151", unit="hex color", role="Body colour"),
    Param("text_align", str, "center", role="Text alignment in boxes: center or left"),
    Param("text_pad", float, 1.5, unit="diagram units", range=(0, None),
          role="Gap between a box's edge and its text", tune="raise if text touches the outline"),
    Param("line_spacing", float, 1.25, unit="multiple of the font size", range=(0, None),
          role="Line spacing of the body text"),
    Param("title_gap", float, 0.8, unit="diagram units", range=(0, None),
          role="Gap between a node's title and its body"),
    # [Arrows]
    Param("arrow_color", "color", "#374151", unit="hex color", role="Arrow colour"),
    Param("arrow_width", float, 0.8, unit="pt", range=(0, None), role="Arrow line width"),
    Param("arrow_head", float, 6.0, unit="pt", range=(0, None), role="Arrow head size"),
    Param("arrow_gap", float, 0.6, unit="pt", range=(0, None), role="Gap between an arrow's ends and the boxes"),
    Param("dashed_style", list, [0, [3, 2]], unit="matplotlib dash pattern (offset, [on, off] in pt)",
          role="Line style of edges marked style: dashed"),
    Param("edge_label_size", float, 6.0, unit="pt", range=(0, None), role="Edge label size"),
    Param("edge_label_color", "color", "#374151", unit="hex color", role="Edge label colour"),
    Param("edge_label_offset", float, 1.2, unit="diagram units",
          role="Edge label distance from the arrow's middle (above a horizontal arrow, right of others)"),
])


def _anchor(n, side, y_down, at=0.5):
    """A point on a node's side, ``at`` of the way along it (from the left or
    the top), in data coordinates."""
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    top, bottom = (y, y + h) if y_down else (y + h, y)
    along = y + h * at if y_down else y + h * (1 - at)
    return {"l": (x, along), "r": (x + w, along), "t": (x + w * at, top), "b": (x + w * at, bottom)}[side]


def _auto_sides(a, b, y_down):
    """Sides to join two nodes by: across the gap between them."""
    if b["x"] >= a["x"] + a["w"]:
        return "r", "l"
    if b["x"] + b["w"] <= a["x"]:
        return "l", "r"
    later = b["y"] >= a["y"] + a["h"]          # b starts after a ends along y
    if y_down:
        return ("b", "t") if later else ("t", "b")
    return ("t", "b") if later else ("b", "t")


def _text(r, col):
    v = r.get(col)
    return "" if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v)


@uses_schema(SCHEMA)
def render_flow_diagram(ax, df, params):
    """Draw the diagram onto ``ax``; returns the node rows drawn."""
    c = {k: params.get(f"{k}_col", k) for k in ("id", "x", "y", "w", "h", "title", "body", "kind", "fill", "color")}
    nodes = {}
    for _, r in df.iterrows():
        nodes[str(r[c["id"]])] = {"x": float(r[c["x"]]), "y": float(r[c["y"]]), "w": float(r[c["w"]]),
                                  "h": float(r[c["h"]]), "title": _text(r, c["title"]), "body": _text(r, c["body"]),
                                  "kind": _text(r, c["kind"]) or "box", "fill": _text(r, c["fill"]),
                                  "color": _text(r, c["color"])}
    y_down = params.get("y_down", True)
    pad, align = params.get("text_pad", 1.5), params.get("text_align", "center")
    t_size, b_size = params.get("title_size", 7.0), params.get("body_size", 6.0)
    spacing, gap = params.get("line_spacing", 1.25), params.get("title_gap", 0.8)
    radius = params.get("box_radius", 1.0)
    sign = 1 if y_down else -1

    for n in sorted(nodes.values(), key=lambda n: n["kind"] != "group"):      # groups underneath
        x, y, w, h = n["x"], n["y"], n["w"], n["h"]
        if n["kind"] == "group":
            ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                                        facecolor=params.get("group_fill", "none"),
                                        edgecolor=params.get("group_edge", "#9CA3AF"),
                                        linestyle=params.get("group_linestyle", "--"),
                                        linewidth=params.get("group_linewidth", 0.6), zorder=1))
        elif n["kind"] == "box":
            ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                                        facecolor=n["fill"] or params.get("box_fill", "#F3F4F6"),
                                        edgecolor=params.get("box_edge", "#4B5563"),
                                        linewidth=params.get("box_linewidth", 0.6), zorder=2))
        # Groups label their top-left corner; boxes and text nodes fill from the top.
        left = n["kind"] == "group" or align == "left"
        tx, ha = (x + pad, "left") if left else (x + w / 2, "center")
        ty = (y + pad) if y_down else (y + h - pad)
        if n["title"]:
            ax.text(tx, ty, n["title"], ha=ha, va="top", fontsize=t_size, fontweight=params.get("title_weight", "bold"),
                    color=n["color"] or params.get("text_color", "#111827"), zorder=3)
            ty += sign * (t_size * MM_PER_PT * params.get("units_per_mm", 1.0) * spacing + gap)
        if n["body"] and n["kind"] != "group":
            ax.text(tx, ty, n["body"], ha=ha, va="top", fontsize=b_size, linespacing=spacing,
                    color=n["color"] or params.get("body_color", "#374151"), zorder=3)

    # Each edge is copied to a plain dict: its optional fields (label, sides, rad,
    # style) are per-arrow choices, not config keys a build should report as missing.
    for e in [dict(x) for x in params.get("edges", []) or []]:
        a, b = nodes[str(e["from"])], nodes[str(e["to"])]
        sa, sb = _auto_sides(a, b, y_down)
        sa, sb = e.get("from_side", sa), e.get("to_side", sb)
        p0, p1 = _anchor(a, sa, y_down, e.get("from_at", 0.5)), _anchor(b, sb, y_down, e.get("to_at", 0.5))
        style = tuple(params.get("dashed_style", [0, [3, 2]])) if e.get("style") == "dashed" else "solid"
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=params.get("arrow_head", 6.0),
                                     connectionstyle=f"arc3,rad={e.get('rad', 0.0)}",
                                     color=params.get("arrow_color", "#374151"), linewidth=params.get("arrow_width", 0.8),
                                     linestyle=style, shrinkA=params.get("arrow_gap", 0.6),
                                     shrinkB=params.get("arrow_gap", 0.6), zorder=4))
        if e.get("label"):
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            off = params.get("edge_label_offset", 1.2)
            if sa in ("l", "r") and sb in ("l", "r"):          # horizontal: label above the arrow
                ax.text(mx, my - sign * off, e["label"], ha="center", va="bottom" if y_down else "top",
                        fontsize=params.get("edge_label_size", 6.0), color=params.get("edge_label_color", "#374151"),
                        zorder=5)
            elif abs(p1[0] - p0[0]) < abs(p1[1] - p0[1]) * VERTICAL_SLOPE:   # vertical: label to its right
                ax.text(mx + off, my, e["label"], ha="left", va="center",
                        fontsize=params.get("edge_label_size", 6.0), color=params.get("edge_label_color", "#374151"),
                        zorder=5)
            else:                                              # slanted: label off the line, on the outer side
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                norm = (dx * dx + dy * dy) ** 0.5
                nx, ny = dy / norm, -dx / norm                 # perpendicular to the arrow
                if nx < 0:
                    nx, ny = -nx, -ny
                ax.text(mx + nx * off, my + ny * off, e["label"], ha="left", va="center",
                        fontsize=params.get("edge_label_size", 6.0), color=params.get("edge_label_color", "#374151"),
                        zorder=5)

    xs = [v for n in nodes.values() for v in (n["x"], n["x"] + n["w"])]
    ys = [v for n in nodes.values() for v in (n["y"], n["y"] + n["h"])]
    ax.set_xlim(*(params.get("xlim") or (min(xs), max(xs))))
    lo, hi = params.get("ylim") or (min(ys), max(ys))
    ax.set_ylim((hi, lo) if y_down else (lo, hi))
    ax.set_aspect("equal")
    ax.axis("off")
    return df.copy()
