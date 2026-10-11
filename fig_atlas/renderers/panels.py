"""Shared helpers for multi-panel figure assembly."""

from __future__ import annotations

# gid set on every panel tag, so checks (fig_atlas.preflight) can find the
# tags among a figure's texts without guessing from their content.
PANEL_TAG_GID = "panel-tag"


def panel_label(subfig, letter, label_size):
    """Stamp a bold panel letter (a, b, c, …) in the top-left of a SubFigure."""
    tag = subfig.suptitle(letter, x=0.02, y=0.98, fontsize=label_size,
                          fontweight="bold", ha="left", va="top")
    tag.set_gid(PANEL_TAG_GID)
    return tag


def place_panel_tags(fig, columns, label_size, pad_pt=2.0, fontweight="bold", align_rows=None):
    """Place panel letters on each panel's measured outer bounding box.

    ``columns`` is a list of layout columns; each column is a list of
    ``(letter, [axes, ...])`` for the panels stacked in it. Each tag's left
    edge sits on the column's shared plumb line -- the leftmost outer edge
    (tick labels, axis titles, legends included) of any panel in that
    column -- and its baseline sits ``pad_pt`` above its own panel's outer
    top edge (AGENTS.md rule 1.5: tags follow the outer bounding box, not the
    plot spine, and stacked panels share one vertical line).

    ``align_rows`` (optional) lists groups of letters that sit in one
    layout row, e.g. ``[["a", "b"], ["c", "d", "e"]]``; each group's tags
    share the highest of their baselines so a row's tags line up
    horizontally even when the panels' titles differ in height.

    Call after everything in the panels has been drawn; the layout is
    measured with a draw pass.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    to_fig = fig.transFigure.inverted()
    pad_px = pad_pt / 72.0 * fig.dpi
    placements = {}
    for column in columns:
        boxes = []
        for letter, axes in column:
            bbs = [a.get_tightbbox(renderer) for a in axes]
            boxes.append((letter, min(b.x0 for b in bbs), max(b.y1 for b in bbs)))
        x_plumb = min(x0 for _, x0, _ in boxes)
        for letter, _, y1 in boxes:
            placements[letter] = [x_plumb, y1]
    for row in align_rows or []:
        present = [l for l in row if l in placements]
        if present:
            y_row = max(placements[l][1] for l in present)
            for l in present:
                placements[l][1] = y_row
    tags = []
    for letter, (x, y) in placements.items():
        fx, fy = to_fig.transform((x, y + pad_px))
        tags.append(fig.text(fx, fy, letter, fontsize=label_size, fontweight=fontweight,
                             ha="left", va="bottom", gid=PANEL_TAG_GID))
    return tags


def align_title_to_labels(ax, title=None):
    """Start a left-aligned axes title at the axes' outer left edge.

    A horizontal bar chart with long category names has its tick labels far
    left of the spine; a title at ``x=0`` then starts over the bars, and one
    placed by a typed axes fraction (``set_x(-1.25)``) drifts whenever the
    labels or the axes width change. This measures the left edge of the tick
    labels and axis title (the title itself left out) and moves the title
    there, so the title -- and a panel tag placed on the outer box -- line up
    with the labels. ``title`` defaults to the axes' left title (what
    ``set_title(..., loc="left")`` sets), else its centre title. Call after the
    axes are fully drawn; returns the title.
    """
    fig = ax.figure
    if title is None:
        title = ax._left_title if ax.get_title("left") else ax.title
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    visible = title.get_visible()
    title.set_visible(False)
    left = ax.get_tightbbox(renderer).x0
    title.set_visible(visible)
    title.set_ha("left")
    title.set_x(ax.transAxes.inverted().transform((left, 0))[0])
    return title
