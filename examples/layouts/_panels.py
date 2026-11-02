"""Draw one example bundle from examples/gallery/ into a layout cell.

The layout examples use the gallery's synthetic bundles as their data. In your
own analysis script this is where you draw your data with your renderers; only
the layout call and ``layouts.finish`` carry over.
"""
from pathlib import Path

import yaml

from fig_atlas.bundle_figure import FIGURE_ARGS, bundle_data, call_shape, resolve
from fig_atlas.contracts import ingest_map

EXAMPLES = Path(__file__).resolve().parents[1]


def draw(cell, panel) -> None:
    """Draw one panel into ``cell``: ``panel`` is a bundle name in examples/gallery/, or
    ``{bundle: <path under examples/>, where: {column: value}, params: {...}}`` to draw
    the rows of a bundle that match ``where``, with params over the bundle's own."""
    spec = panel if isinstance(panel, dict) else {"bundle": f"gallery/{panel}"}
    bundle = EXAMPLES / spec["bundle"]
    meta = yaml.safe_load((bundle / "metadata" / "metadata.yaml").read_text(encoding="utf-8")) or {}
    fn = resolve(ingest_map()[meta["plot_type"]])
    shape = call_shape(fn)
    data = bundle_data(bundle, shape)
    for column, value in (spec.get("where") or {}).items():
        data = data[data[column] == value]
    target = cell if shape[0] in FIGURE_ARGS else cell.add_subplot(1, 1, 1)
    fn(target, data, {**(meta.get("plot_params") or {}), **(spec.get("params") or {})})
