"""Draw a figure from the project config's ``plots:`` blocks (roadmap 7.4).

Each block is one panel, drawn in order (a, b, c, ...) on a grid:

    plots:
      volcano:                                  # panel name
        renderer: "fig_atlas_omics.renderers:render_volcano"   # or a plot name for fig_atlas.render
        bundle: "raw_data/<study>/<project>/volcano_plot_bundle"   # data: the bundle's inputs
        log2fc_threshold: 1.0                   # ... every renderer parameter, commented
        ...

A block with ``bundle`` reads the bundle's ``inputs/data.csv`` (or, for an
image panel, the channel files listed in its metadata). A block without one
gets its data from the analysis script's ``load(name, block)``. ``fa ingest
bundle`` writes such blocks; the analysis script from ``fa new project`` calls
``draw_plots``.

Renderers drawn this way take ``(ax, df, params)``, ``(fig, df, params)`` (a
subfigure) or ``(ax, source, params)`` (image files). Others need data
prepared in the script.
"""
from __future__ import annotations

import importlib
import inspect
import math
import string
from pathlib import Path

FIGURE_ARGS = ("fig", "container", "sf_or_fig")
DRAWABLE = {("ax", "df"), ("ax", "source"), *((f, "df") for f in FIGURE_ARGS)}


def resolve(target: str):
    """A renderer from "module:function" or a plot name (fig_atlas.render)."""
    if ":" in target:
        module, _, attr = target.partition(":")
        return getattr(importlib.import_module(module), attr)
    from .renderer_registry import find
    return find(target)[1]


def call_shape(fn) -> tuple[str, str]:
    params = list(inspect.signature(fn).parameters)
    return (params + ["", ""])[0], (params + ["", ""])[1]


def drawable(fn) -> bool:
    return call_shape(fn) in DRAWABLE


def bundle_data(bundle: Path, shape: tuple[str, str]):
    """The data a renderer gets from a bundle: the image files for an image
    panel, else ``inputs/data.csv`` as a table."""
    import pandas as pd
    import yaml
    if shape[1] == "source":
        meta = yaml.safe_load((bundle / "metadata" / "metadata.yaml").read_text(encoding="utf-8")) or {}
        return [bundle / "inputs" / (c["file"] if isinstance(c, dict) else c) for c in meta.get("channels", [])]
    return pd.read_csv(bundle / "inputs" / "data.csv")


def draw_plots(fig, plots: dict, root: Path, layout: dict | None = None, load=None) -> list:
    """Draw every ``plots:`` block that names a renderer; returns the
    ``place_panel_tags`` columns ([(letter, axes), ...] per grid column)."""
    layout = layout or {}
    names = [k for k, v in (plots or {}).items() if isinstance(v, dict) and v.get("renderer")]
    if not names:
        raise ValueError("no plots to draw: add a block with `fa ingest bundle <bundle> --project <name>`, "
                         "or a plots.<name> block with a renderer")
    cols = int(layout.get("columns") or min(len(names), 3))      # 0 / unset: one per panel, up to 3
    rows = math.ceil(len(names) / cols)
    gs = fig.add_gridspec(rows, cols, left=0, right=1, bottom=0, top=1,
                          wspace=float(layout.get("wspace", 0.1)), hspace=float(layout.get("hspace", 0.15)))
    columns: dict[int, list] = {}
    fitted: list = []                                             # (subfigure, axes) to fit in their cells
    for i, name in enumerate(names):
        block = dict(plots[name])
        fn = resolve(block.pop("renderer"))
        bundle = block.pop("bundle", None)
        shape = call_shape(fn)
        if shape not in DRAWABLE:
            raise ValueError(f"plots.{name}: {fn.__name__} takes {shape}; draw it in the analysis script")
        if bundle:
            data = bundle_data(root / bundle, shape)
        elif load is not None:
            data = load(name, block)
        else:
            raise ValueError(f"plots.{name} has no bundle and the script gives no load()")
        # Every panel gets its own subfigure: renderers that place their axes
        # relative to "the figure" (to fit long labels, colourbars) then stay
        # inside their own cell instead of spreading over the whole figure.
        sf = fig.add_subfigure(gs[i // cols, i % cols])
        if shape[0] in FIGURE_ARGS:
            fn(sf, data, block)                   # lays out its own axes inside the subfigure
        else:
            ax = sf.add_subplot(1, 1, 1)
            fn(ax, data, block)
            fitted.append((sf, ax))
        axes = list(sf.axes)
        columns.setdefault(i % cols, []).append((string.ascii_lowercase[i], axes))
    tags = layout.get("tags", {}) or {}
    top_pt = float(tags.get("size", 9.0)) + float(tags.get("pad_pt", 2.0)) if tags.get("show", True) else 0.0
    fit_in_cells(fig, fitted, pad_mm=float(layout.get("panel_pad_mm", 1.0)), top_reserve_pt=top_pt)
    return [columns[c] for c in sorted(columns)]



def draw_bundle(bundle: Path, width_mm: float = 85.0, height_mm: float = 62.0, root: Path | None = None):
    """One bundle drawn on its own, as `fa ingest bundle` would draw it: its
    plot_type's renderer with its plot_params, on a figure of the given
    printed size (single column by default). Returns the figure.
    Used by the example gallery (docs/reference/gallery.md) and its test."""
    import matplotlib.pyplot as plt
    import yaml
    from .contracts import ingest_map
    bundle = Path(bundle)
    meta = yaml.safe_load((bundle / "metadata" / "metadata.yaml").read_text(encoding="utf-8")) or {}
    target = ingest_map().get(meta.get("plot_type"))
    if target is None:
        raise ValueError(f"{bundle}: no renderer for plot_type {meta.get('plot_type')!r}")
    root = Path(root) if root is not None else bundle.parent
    block = {"renderer": target, "bundle": bundle.resolve().relative_to(root.resolve()).as_posix(),
             **(meta.get("plot_params") or {})}
    fig = plt.figure(figsize=(width_mm / 25.4, height_mm / 25.4))
    draw_plots(fig, {bundle.name: block}, root, layout={"columns": 1, "tags": {"show": False}})
    return fig

def fit_in_cells(fig, panels: list, pad_mm: float = 1.0, top_reserve_pt: float = 0.0, passes: int = 3) -> None:
    """Resize each panel's axes so its outer bounding box -- tick labels, axis
    titles, title and legend included -- fills its grid cell, ``pad_mm``
    inside the edges, with ``top_reserve_pt`` kept free above it for the panel
    tag (AGENTS.md 1.5). Nothing is cut off at the canvas edge, and panels in
    one column start on the same line. A few passes, since tick labels can
    change when the axes change size."""
    if not panels:
        return
    pad = pad_mm / 25.4 * fig.dpi
    top = top_reserve_pt / 72.0 * fig.dpi
    for _ in range(passes):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for sf, ax in panels:
            cell, outer, box = sf.bbox, ax.get_tightbbox(renderer), ax.get_window_extent(renderer)
            x0 = box.x0 + (cell.x0 + pad - outer.x0)
            x1 = box.x1 + (cell.x1 - pad - outer.x1)
            y0 = box.y0 + (cell.y0 + pad - outer.y0)
            y1 = box.y1 + (cell.y1 - pad - top - outer.y1)
            if x1 - x0 < pad or y1 - y0 < pad:
                continue                          # labels larger than the cell: leave it to preflight
            (fx0, fy0), (fx1, fy1) = sf.transSubfigure.inverted().transform([(x0, y0), (x1, y1)])
            ax.set_position([fx0, fy0, fx1 - fx0, fy1 - fy0])
