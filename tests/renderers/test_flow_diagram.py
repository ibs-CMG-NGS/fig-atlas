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
