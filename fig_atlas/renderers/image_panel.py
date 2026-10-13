"""Image panel: a microscope image, blot or gel with a scale bar (roadmap 6a.3).

``source`` is one image file, or a list of greyscale files (one per channel)
that are tinted with ``channel_colors`` and summed. Adjustments are a crop,
a linear display range per channel (given, or from percentiles) and an
optional gamma; fig_atlas.images records them with the source hashes so the
figure's provenance and README disclose them (verify warns on gamma != 1).
"""
from __future__ import annotations

from pathlib import Path

from ..schema import Param, Schema, uses_schema

SCHEMA = Schema("image_panel", params=[
    # [Source and adjustments]
    Param("channel_colors", list, None, unit="matplotlib colours, one per file",
          role="Tint per greyscale channel when several files are combined (default: green, magenta, cyan, ...)"),
    Param("channel_labels", list, None, role="Name per channel, shown in a corner when show_channel_labels"),
    Param("display_ranges", list, None, unit="image units [min, max] per channel",
          role="Linear display range per channel (default: from display_percentiles)"),
    Param("display_percentiles", list, [0.0, 100.0], unit="percentiles [low, high]",
          role="Display range taken from the image when display_ranges is not set",
          tune="e.g. [0.5, 99.5] to ignore a few saturated pixels"),
    Param("gamma", float, 1.0, unit="exponent", range=(0, None),
          role="Gamma on the scaled image; anything but 1 is a nonlinear adjustment and verify warns"),
    Param("crop", list, None, unit="pixels [x0, y0, x1, y1]", role="Region shown (default: the whole image)"),
    Param("interpolation", str, "nearest", role="Resampling when drawn (matplotlib imshow; nearest keeps pixels)"),
    Param("panel", str, None, role="Panel letter recorded with the adjustments (README 'Images' section)"),
    # [Scale bar]
    Param("pixel_size", float, None, unit="physical units per pixel", range=(0, None),
          role="Size of one pixel; needed for a scale bar"),
    Param("pixel_unit", str, "µm", role="Unit of pixel_size and scale_bar"),
    Param("scale_bar", float, None, unit="physical units (pixel_unit)", range=(0, None),
          role="Scale bar length (default: no bar)"),
    Param("scale_bar_position", ("lower right", "lower left", "upper right", "upper left"), "lower right",
          role="Corner of the scale bar"),
    Param("scale_bar_color", "color", "white", unit="color", role="Scale bar and its label colour"),
    Param("scale_bar_thickness", float, 2.0, unit="pt", range=(0, None), role="Scale bar line width"),
    Param("scale_bar_pad", float, 0.05, unit="fraction of the panel", range=(0, 0.5),
          role="Distance of the bar from the panel edges"),
    Param("scale_bar_label", bool, True, role="Print the length above the bar"),
    Param("scale_bar_fontsize", float, 6.0, unit="pt", range=(0, None), role="Scale bar label size"),
    # [Labels and frame]
    Param("show_channel_labels", bool, False, role="Print the channel names, in their tint, in the upper left"),
    Param("channel_label_fontsize", float, 6.0, unit="pt", range=(0, None), role="Channel name size"),
    Param("channel_label_box", bool, False,
          role="Put a dark box behind the channel names (keeps them readable on a busy image)"),
    Param("channel_label_box_color", "color", "black", unit="color", role="Colour of that box"),
    Param("channel_label_box_alpha", float, 0.6, unit="[0-1] opacity", range=(0, 1), role="Opacity of that box"),
    Param("labels_title", str, None, role="Panel title"),
    Param("title_size", float, 8.0, unit="pt", range=(0, None), role="Panel title size"),
    Param("frame", bool, False, role="Draw a frame around the image"),
    Param("frame_color", "color", "black", unit="color", role="Frame colour"),
    Param("frame_width", float, 0.5, unit="pt", range=(0, None), role="Frame line width"),
])

_TINTS = ["#00ff00", "#ff00ff", "#00ffff", "#ff0000", "#0000ff", "#ffff00"]


def _channels(source, params):
    from ..images import Channel
    files = [source] if isinstance(source, (str, Path)) else list(source)
    colors = params.get("channel_colors") or (["white"] if len(files) == 1 else _TINTS[:len(files)])
    labels = params.get("channel_labels") or [""] * len(files)
    ranges = params.get("display_ranges") or [None] * len(files)
    if not (len(colors) == len(labels) == len(ranges) == len(files)):
        raise ValueError(f"image_panel: {len(files)} file(s) but {len(colors)} colour(s), "
                         f"{len(labels)} label(s), {len(ranges)} display range(s)")
    return [Channel(str(f), c, r, l) for f, c, r, l in zip(files, colors, ranges, labels)]


def _scale_bar(ax, width_px: int, height_px: int, params) -> float | None:
    size, length = params.get("pixel_size"), params.get("scale_bar")
    if not (size and length):
        return None
    bar_px = float(length) / float(size)
    if bar_px > width_px:
        raise ValueError(f"image_panel: a {length} {params.get('pixel_unit', 'µm')} bar is "
                         f"{bar_px:.0f} px, wider than the {width_px} px shown")
    pad = float(params.get("scale_bar_pad", 0.05))
    corner = params.get("scale_bar_position", "lower right")
    x1 = width_px * (1 - pad) if "right" in corner else width_px * pad + bar_px
    y = height_px * (1 - pad) if "lower" in corner else height_px * pad   # image rows grow downwards
    color = params.get("scale_bar_color", "white")
    ax.plot([x1 - bar_px, x1], [y, y], color=color, linewidth=float(params.get("scale_bar_thickness", 2.0)),
            solid_capstyle="butt")
    if params.get("scale_bar_label", True):
        ax.text(x1 - bar_px / 2, y - height_px * pad / 2, f"{float(length):g} {params.get('pixel_unit', 'µm')}",
                color=color, ha="center", va="bottom" if "lower" in corner else "top",
                fontsize=float(params.get("scale_bar_fontsize", 6.0)))
    return bar_px


@uses_schema(SCHEMA)
def render_image_panel(ax, source, params):
    """Draw a microscope image, blot or gel onto ``ax`` from its original file.

    ``source`` is one image file, or a list of greyscale files (one per
    channel) that are tinted and combined. ``params`` (the panel's
    ``plots:`` block; keys in the config reference under image_panel) sets
    the crop, the linear display range per channel, gamma and the scale bar
    (from ``pixel_size``). Never pass a brightened or cropped copy: the
    adjustments are made here and recorded with the source file hashes, so
    the figure's README lists them and verify fails if a source image
    changes (AGENTS.md 4.7). Returns the recorded entry."""
    from ..images import prepare, record
    chans = _channels(source, params)
    prep = prepare(chans, crop=params.get("crop"), gamma=float(params.get("gamma", 1.0)),
                   percentiles=params.get("display_percentiles", [0.0, 100.0]))
    h, w = prep.rgb.shape[:2]
    ax.imshow(prep.rgb, interpolation=params.get("interpolation", "nearest"))
    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(h - 0.5, -0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    frame = bool(params.get("frame", False))
    for spine in ax.spines.values():
        spine.set_visible(frame)
        spine.set_edgecolor(params.get("frame_color", "black"))
        spine.set_linewidth(float(params.get("frame_width", 0.5)))
    bar_px = _scale_bar(ax, w, h, params)
    if params.get("show_channel_labels", False):
        box = (dict(boxstyle="square,pad=0.15", fc=params.get("channel_label_box_color", "black"), ec="none",
                    alpha=float(params.get("channel_label_box_alpha", 0.6)))
               if params.get("channel_label_box", False) else None)
        for i, ch in enumerate(c for c in chans if c.label):
            ax.text(0.03, 0.97 - i * 0.09, ch.label, transform=ax.transAxes, color=ch.color, ha="left", va="top",
                    fontsize=float(params.get("channel_label_fontsize", 6.0)), fontweight="bold", bbox=box)
    title = params.get("labels_title")
    if title:
        ax.set_title(title, fontsize=float(params.get("title_size", 8.0)), fontweight="bold")
    entry = {**prep.record, "panel": params.get("panel"), "pixel_size": params.get("pixel_size"),
             "pixel_unit": params.get("pixel_unit", "µm"), "scale_bar": params.get("scale_bar"),
             "scale_bar_px": bar_px}
    return record(entry)
