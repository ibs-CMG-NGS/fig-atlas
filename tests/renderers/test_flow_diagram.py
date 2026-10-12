"""render_flow_diagram: boxes, groups and arrows from a node table."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from fig_atlas.renderers import render_flow_diagram  # noqa: E402

NODES = pd.DataFrame([
    {"id": "g", "x": 0, "y": 0, "w": 60, "h": 30, "title": "Build", "kind": "group"},
    {"id": "a", "x": 5, "y": 8, "w": 20, "h": 15, "title": "Run", "body": "script\nrecorder"},
    {"id": "b", "x": 35, "y": 8, "w": 20, "h": 15, "title": "Publish"},
    {"id": "c", "x": 35, "y": 40, "w": 20, "h": 10, "title": "Verify", "kind": "text"},
])
EDGES = [{"from": "a", "to": "b", "label": "figure"}, {"from": "b", "to": "c"}]


def _arrows(ax):
    return [p for p in ax.patches if isinstance(p, FancyArrowPatch)]


def test_draws_boxes_groups_and_arrows():
    fig, ax = plt.subplots()
    drawn = render_flow_diagram(ax, NODES, {"edges": EDGES})
    boxes = [p for p in ax.patches if isinstance(p, FancyBboxPatch)]
    assert len(drawn) == len(NODES)
    assert len(boxes) == 3                     # two boxes and the group; the text node has no frame
    assert len(_arrows(ax)) == 2
    texts = {t.get_text() for t in ax.texts}
    assert {"Build", "Run", "Publish", "Verify", "figure", "script\nrecorder"} <= texts
    plt.close(fig)


def test_arrow_leaves_the_side_facing_its_target():
    fig, ax = plt.subplots()
    render_flow_diagram(ax, NODES, {"edges": EDGES})
    across, down = _arrows(ax)
    (x0, _), (x1, _) = across._posA_posB
    assert (x0, x1) == (25, 35)                 # right side of a -> left side of b
    (_, y0), (_, y1) = down._posA_posB
    assert (y0, y1) == (23, 40)                 # bottom of b -> top of c (y grows downward)
    plt.close(fig)


def test_explicit_sides_and_page_extent():
    fig, ax = plt.subplots()
    render_flow_diagram(ax, NODES, {"edges": [{"from": "a", "to": "c", "from_side": "b", "to_side": "l"}],
                                    "xlim": [0, 100], "ylim": [0, 60]})
    (x0, y0), (x1, y1) = _arrows(ax)[0]._posA_posB
    assert (x0, y0) == (15, 23) and (x1, y1) == (35, 45)
    assert ax.get_xlim() == (0, 100) and ax.get_ylim() == (60, 0)   # y downward by default
    plt.close(fig)


def test_node_text_colour():
    nodes = pd.DataFrame([{"id": "n", "x": 0, "y": 0, "w": 20, "h": 10, "title": "Risk", "body": "stale",
                           "kind": "text", "color": "#DC2626"}])
    fig, ax = plt.subplots()
    render_flow_diagram(ax, nodes, {})
    assert {t.get_color() for t in ax.texts} == {"#DC2626"}
    plt.close(fig)


def test_edge_point_along_a_side():
    fig, ax = plt.subplots()
    render_flow_diagram(ax, NODES, {"edges": [{"from": "b", "to": "c", "from_at": 0.25, "to_at": 0.25}]})
    (x0, y0), (x1, y1) = _arrows(ax)[0]._posA_posB
    assert (x0, y0) == (40, 23) and (x1, y1) == (40, 40)      # a quarter along b's bottom and c's top
    plt.close(fig)


def test_label_of_a_slanted_arrow_sits_off_the_line():
    nodes = pd.DataFrame([{"id": "p", "x": 40, "y": 0, "w": 20, "h": 10},
                          {"id": "q", "x": 0, "y": 30, "w": 20, "h": 10}])
    fig, ax = plt.subplots()
    render_flow_diagram(ax, nodes, {"edges": [{"from": "p", "to": "q", "from_side": "b", "to_side": "r",
                                               "label": "L"}], "edge_label_offset": 2.0})
    (x0, y0), (x1, y1) = _arrows(ax)[0]._posA_posB
    label = next(t for t in ax.texts if t.get_text() == "L")
    lx, ly = label.get_position()
    # distance from the label anchor to the arrow's line equals the offset
    dist = abs((y1 - y0) * lx - (x1 - x0) * ly + x1 * y0 - y1 * x0) / ((y1 - y0) ** 2 + (x1 - x0) ** 2) ** 0.5
    assert abs(dist - 2.0) < 1e-6
    plt.close(fig)


def test_flowchart_shapes_centre_their_text():
    from matplotlib.patches import Polygon
    nodes = pd.DataFrame([{"id": "s", "x": 0, "y": 0, "w": 20, "h": 8, "title": "Start", "kind": "terminal"},
                          {"id": "d", "x": 0, "y": 14, "w": 20, "h": 12, "title": "Changes files?", "kind": "decision"}])
    fig, ax = plt.subplots()
    render_flow_diagram(ax, nodes, {"edges": [{"from": "s", "to": "d"}]})
    diamond = next(p for p in ax.patches if isinstance(p, Polygon))
    assert sorted(map(tuple, diamond.get_xy()[:4])) == [(0, 20), (10, 14), (10, 26), (20, 20)]
    fig.canvas.draw()
    title = next(t for t in ax.texts if t.get_text() == "Changes files?")
    bb = title.get_window_extent().transformed(ax.transData.inverted())
    assert abs((bb.y0 + bb.y1) / 2 - 20) < 2.5          # text sits about the diamond's middle
    (_, y0), (_, y1) = _arrows(ax)[0]._posA_posB
    assert (y0, y1) == (8, 14)                          # terminal bottom -> diamond top vertex
    plt.close(fig)


def test_box_text_is_centred_vertically():
    """A tall box keeps its text in the middle, not stuck to the top edge."""
    nodes = pd.DataFrame([{"id": "b", "x": 0, "y": 0, "w": 40, "h": 30, "title": "Title", "body": "one\ntwo"}])
    fig, ax = plt.subplots(figsize=(3, 3))
    render_flow_diagram(ax, nodes, {"xlim": [0, 40], "ylim": [0, 30]})
    fig.canvas.draw()
    inv = ax.transData.inverted()
    boxes = [t.get_window_extent() for t in ax.texts]
    y0 = inv.transform((0, min(b.y0 for b in boxes)))[1]
    y1 = inv.transform((0, max(b.y1 for b in boxes)))[1]
    assert abs((y0 + y1) / 2 - 15) < 0.5
    render_flow_diagram(ax2 := plt.subplots(figsize=(3, 3))[1], nodes,
                        {"xlim": [0, 40], "ylim": [0, 30], "text_valign": "top", "text_pad": 1.5})
    top = ax2.transData.inverted().transform((0, ax2.texts[0].get_window_extent().y1))[1]
    assert abs(min(top, 30 - top) - 1.5) < 1.0       # top: the title starts text_pad below the top edge
    plt.close("all")


def test_arrow_between_overlapping_spans_is_level():
    """Side-by-side nodes of different heights: the arrow runs level through
    the shared span (through a terminal's middle, where its rounded end is)."""
    nodes = pd.DataFrame([{"id": "c", "x": 0, "y": 69, "w": 42, "h": 20},
                          {"id": "e", "x": 49, "y": 75, "w": 31, "h": 12, "kind": "terminal"},
                          {"id": "p", "x": 0, "y": 0, "w": 20, "h": 10},
                          {"id": "q", "x": 30, "y": 4, "w": 20, "h": 10}])
    fig, ax = plt.subplots()
    render_flow_diagram(ax, nodes, {"edges": [{"from": "c", "to": "e"}, {"from": "p", "to": "q"}]})
    (_, y0), (_, y1) = _arrows(ax)[0]._posA_posB
    assert y0 == y1 == 81                       # the terminal's middle
    (_, y0), (_, y1) = _arrows(ax)[1]._posA_posB
    assert y0 == y1 == 7                        # middle of the shared span 4-10
    render_flow_diagram(ax2 := plt.subplots()[1], nodes,
                        {"edges": [{"from": "p", "to": "q"}], "level_edges": False})
    (_, y0), (_, y1) = _arrows(ax2)[0]._posA_posB
    assert (y0, y1) == (5, 9)                   # off: side middles, slanted
    plt.close("all")


def test_elbow_edges_run_horizontally_and_vertically():
    """Flowchart connectors: an L from a bottom to a left side, a U around the
    outside between two right sides; every segment is horizontal or vertical."""
    nodes = pd.DataFrame([{"id": "p", "x": 0, "y": 0, "w": 20, "h": 10},
                          {"id": "q", "x": 40, "y": 30, "w": 20, "h": 10},
                          {"id": "s", "x": 40, "y": 0, "w": 20, "h": 10}])
    fig, ax = plt.subplots()
    render_flow_diagram(ax, nodes, {"route": "elbow", "elbow_offset": 5.0, "edges": [
        {"from": "p", "to": "q", "from_side": "b", "to_side": "l"},
        {"from": "s", "to": "q", "from_side": "r", "to_side": "r"}]})
    l_shape, u_shape = (a._path_original.vertices for a in _arrows(ax))   # the route, before the head is added
    for v in (l_shape, u_shape):
        for (x0, y0), (x1, y1) in zip(v[:-1], v[1:]):
            assert abs(x0 - x1) < 1e-9 or abs(y0 - y1) < 1e-9
    assert len(l_shape) == 3 and abs(l_shape[1][0] - 10) < 1e-9 and abs(l_shape[1][1] - 35) < 1e-9
    assert abs(max(u_shape[:, 0]) - 65) < 1e-9          # 5 units past the right sides at x = 60
    plt.close(fig)
