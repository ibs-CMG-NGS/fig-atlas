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
           at its top-left), "text" (no frame), and the flowchart shapes
           "decision" (a diamond in the node's box) and "terminal" (a box with
           fully rounded ends, for start and end); these two centre their text
    fill   fill colour for this node (optional; default box_fill)
    color  text colour for this node (optional; default text_color / body_color)
Edges come from the ``edges`` param: a list of {"from", "to"} with optional
"label", "from_side"/"to_side" ("l", "r", "t", "b"; default: across the gap
between the two nodes), "from_at"/"to_at" (where on that side, 0-1 from the
left or top; default 0.5), "rad" (curvature), "style" ("solid"/"dashed") and
"route" ("straight" or "elbow"; default: the ``route`` param). An elbow edge is
drawn with horizontal and vertical segments only, as flowcharts are: an L from
a side to a perpendicular side, a Z between facing sides, a U around the
outside between two sides facing the same way (``elbow_offset`` out).
A straight arrow between two nodes whose spans overlap (side by side: their
heights; one above the other: their widths) is drawn level -- horizontal or
vertical -- through the overlap, unless "from_at"/"to_at" place its ends
(``level_edges: false`` turns this off).

Returns the node rows drawn, ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

FAMILY = "schematic"    # gallery family (fig_atlas/family.py): the shape this module draws

import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon
from matplotlib.path import Path as MplPath

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
    Param("kind_col", str, "kind", role="Column with the node kind: box, group, text, decision or terminal"),
    Param("fill_col", str, "fill", role="Column with a node's own fill colour (empty: box_fill)"),
    Param("color_col", str, "color", role="Column with a node's own text colour (empty: text_color, body_color)"),
    Param("edges", list, [], role="Arrows: list of {from, to, label?, from_side?, to_side?, rad?, style?, route?}"),
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
    Param("text_valign", str, "center", role="Vertical placement of a box's or text node's text: center or top",
          tune="top fills a box from its top edge (text_pad below it); groups always label their top-left corner"),
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
    Param("route", ("straight", "elbow"), "straight",
          role="How edges run: straight lines, or right-angle segments as in flowcharts (an edge's own route wins)"),
    Param("elbow_offset", float, 4.0, unit="diagram units", range=(0, None),
          role="How far a U-shaped elbow edge (two sides facing the same way) runs out past the nodes",
          tune="raise if the return line crowds the boxes it passes"),
    Param("level_edges", bool, True,
          role="Draw a straight arrow level (horizontal or vertical) when the two nodes' spans overlap",
          tune="false to join the middles of the two sides, even if the arrow then slants"),
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


def _level_ats(a, b, sa, sb, y_down):
    """``(from_at, to_at)`` that make the arrow from side ``sa`` of ``a`` to
    side ``sb`` of ``b`` level, or None when their spans do not overlap. A
    diamond or rounded end only meets its side at the middle, so that middle
    is kept and the level line goes through it if the other node spans it."""
    if {sa, sb} == {"l", "r"}:
        lo, size = "y", "h"
    elif {sa, sb} == {"t", "b"}:
        lo, size = "x", "w"
    else:
        return None
    fixed = [n for n in (a, b) if n["kind"] in ("decision", "terminal")]
    lo_s, hi_s = max(a[lo], b[lo]), min(a[lo] + a[size], b[lo] + b[size])
    if hi_s <= lo_s:
        return None
    if len(fixed) == 2:
        mids = {n[lo] + n[size] / 2 for n in fixed}
        if len(mids) > 1:
            return None
        level = mids.pop()
    elif fixed:
        level = fixed[0][lo] + fixed[0][size] / 2
        if not lo_s <= level <= hi_s:
            return None
    else:
        level = (lo_s + hi_s) / 2
    def at(n):
        f = (level - n[lo]) / n[size]
        return 1 - f if lo == "y" and not y_down else f
    return at(a), at(b)


_OUT = {"l": (-1, 0), "r": (1, 0), "t": (0, -1), "b": (0, 1)}   # side -> outward direction (y down)


def _elbow(p0, sa, p1, sb, y_down, offset):
    """Right-angle waypoints from p0 (leaving side sa) to p1 (entering side sb)."""
    flip = 1 if y_down else -1
    (ax_, ay), (bx, by) = _OUT[sa], _OUT[sb]
    ay, by = ay * flip, by * flip
    horiz_a, horiz_b = sa in "lr", sb in "lr"
    if horiz_a != horiz_b:                                   # L: one turn
        corner = (p1[0], p0[1]) if horiz_a else (p0[0], p1[1])
        return [p0, corner, p1]
    if sa == sb:                                             # U: out past both, across, back in
        if horiz_a:
            x = (max if ax_ > 0 else min)(p0[0], p1[0]) + ax_ * offset
            return [p0, (x, p0[1]), (x, p1[1]), p1]
        y = (max if ay > 0 else min)(p0[1], p1[1]) + ay * offset
        return [p0, (p0[0], y), (p1[0], y), p1]
    if horiz_a:                                              # Z: facing sides, turn half way
        mx = (p0[0] + p1[0]) / 2
        return [p0, (mx, p0[1]), (mx, p1[1]), p1] if p0[1] != p1[1] else [p0, p1]
    my = (p0[1] + p1[1]) / 2
    return [p0, (p0[0], my), (p1[0], my), p1] if p0[0] != p1[0] else [p0, p1]


def _trim(points, gap):
    """Shorten the first and last segments by ``gap`` (diagram units)."""
    pts = [list(q) for q in points]
    for i, j in ((0, 1), (-1, -2)):
        dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
        n = (dx * dx + dy * dy) ** 0.5
        if n > 2 * gap:
            pts[i][0] += dx / n * gap
            pts[i][1] += dy / n * gap
    return [tuple(q) for q in pts]


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
    valign = params.get("text_valign", "center")
    to_centre = []          # (texts of one node, the node's vertical middle) to centre once laid out
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
        elif n["kind"] in ("decision", "terminal"):
            face = n["fill"] or params.get("box_fill", "#F3F4F6")
            edge, lw = params.get("box_edge", "#4B5563"), params.get("box_linewidth", 0.6)
            if n["kind"] == "decision":
                ax.add_patch(Polygon([(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)],
                                     closed=True, facecolor=face, edgecolor=edge, linewidth=lw, zorder=2))
            else:
                ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={h / 2}",
                                            facecolor=face, edgecolor=edge, linewidth=lw, zorder=2))
        # Groups label their top-left corner; other nodes are filled from the top
        # and, unless text_valign is "top", centred vertically once drawn (below).
        left = n["kind"] == "group" or (align == "left" and n["kind"] not in ("decision", "terminal"))
        tx, ha = (x + pad, "left") if left else (x + w / 2, "center")
        ty = (y + pad) if y_down else (y + h - pad)
        drawn = []
        if n["title"]:
            drawn.append(ax.text(tx, ty, n["title"], ha=ha, va="top", fontsize=t_size,
                                 fontweight=params.get("title_weight", "bold"),
                                 color=n["color"] or params.get("text_color", "#111827"), zorder=3))
            ty += sign * (t_size * MM_PER_PT * params.get("units_per_mm", 1.0) * spacing + gap)
        if n["body"] and n["kind"] != "group":
            drawn.append(ax.text(tx, ty, n["body"], ha=ha, va="top", fontsize=b_size, linespacing=spacing,
                                 color=n["color"] or params.get("body_color", "#374151"), zorder=3))
        if drawn and n["kind"] != "group" and (valign == "center" or n["kind"] in ("decision", "terminal")):
            to_centre.append((drawn, y + h / 2))

    # Each edge is copied to a plain dict: its optional fields (label, sides, rad,
    # style) are per-arrow choices, not config keys a build should report as missing.
    for e in [dict(x) for x in params.get("edges", []) or []]:
        a, b = nodes[str(e["from"])], nodes[str(e["to"])]
        sa, sb = _auto_sides(a, b, y_down)
        sa, sb = e.get("from_side", sa), e.get("to_side", sb)
        at_a, at_b = 0.5, 0.5
        if params.get("level_edges", True) and not e.get("rad") and "from_at" not in e and "to_at" not in e:
            at_a, at_b = _level_ats(a, b, sa, sb, y_down) or (0.5, 0.5)
        p0, p1 = _anchor(a, sa, y_down, e.get("from_at", at_a)), _anchor(b, sb, y_down, e.get("to_at", at_b))
        style = tuple(params.get("dashed_style", [0, [3, 2]])) if e.get("style") == "dashed" else "solid"
        look = dict(arrowstyle="-|>", mutation_scale=params.get("arrow_head", 6.0),
                    color=params.get("arrow_color", "#374151"), linewidth=params.get("arrow_width", 0.8),
                    linestyle=style, zorder=4)
        route = e.get("route", params.get("route", "straight"))
        pts = _elbow(p0, sa, p1, sb, y_down, params.get("elbow_offset", 4.0)) if route == "elbow" else [p0, p1]
        if len(pts) > 2:
            gap = params.get("arrow_gap", 0.6) / 72 * 25.4 * params.get("units_per_mm", 1.0)
            pts = _trim(pts, gap)
            ax.add_patch(FancyArrowPatch(path=MplPath(pts, [MplPath.MOVETO] + [MplPath.LINETO] * (len(pts) - 1)),
                                         **look))
            seg = max(range(len(pts) - 1), key=lambda i: abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]))
            p0, p1 = pts[seg], pts[seg + 1]                   # the label goes by the longest segment
            sa, sb = ("l", "r") if p0[1] == p1[1] else ("t", "b")
        else:
            ax.add_patch(FancyArrowPatch(p0, p1, connectionstyle=f"arc3,rad={e.get('rad', 0.0)}",
                                         shrinkA=params.get("arrow_gap", 0.6), shrinkB=params.get("arrow_gap", 0.6),
                                         **look))
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
    _centre_texts(ax, to_centre)
    return df.copy()


def _centre_texts(ax, groups):
    """Move each node's texts so the block they form is centred on the node's
    middle: measured from the drawn text, so it holds for any font and size."""
    if not groups:
        return
    ax.apply_aspect()
    renderer = ax.figure.canvas.get_renderer()
    inv = ax.transData.inverted()
    for texts, middle in groups:
        boxes = [t.get_window_extent(renderer) for t in texts]
        y0 = inv.transform((0, min(b.y0 for b in boxes)))[1]
        y1 = inv.transform((0, max(b.y1 for b in boxes)))[1]
        shift = middle - (y0 + y1) / 2
        for t in texts:
            x, y = t.get_position()
            t.set_position((x, y + shift))
