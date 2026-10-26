"""chromosome_ideogram: one chromosome drawn from its cytobands, whole (rounded
ends, band names) or zoomed to a window (a band strip with a position ruler),
with optional markers at given positions (insertion sites, breakpoints).

Data: one row per band of ONE chromosome, with the columns named by start_col,
end_col, band_col and stain_col (UCSC cytoBandIdeo: gneg, gpos25..gpos100,
acen, gvar, stalk). ``markers``: an optional table with the columns named by
marker_pos_col and marker_label_col. x is in bp, so a script can point
connectors at a marker. Returns the markers with the y of the chromosome's top
edge (``y_top``), ready for fig_atlas.source_data.add.
"""
from __future__ import annotations

FAMILY = "field"    # gallery family (fig_atlas/family.py): the shape this module draws

import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator

from fig_atlas.params import text_param
from fig_atlas.schema import CODE_DEFAULT, Param, Schema, typography, uses_schema

STAINS = {"gneg": "#ffffff", "gpos25": "#d4d4d4", "gpos33": "#bdbdbd", "gpos50": "#969696",
          "gpos66": "#737373", "gpos75": "#525252", "gpos100": "#262626", "acen": "#9ca3af",
          "gvar": "#e5e7eb", "stalk": "#e5e7eb"}

SCHEMA = Schema("chromosome_ideogram", params=[
    # [Data]
    Param("start_col", str, "start", role="Column with the band start (bp, 1-based)"),
    Param("end_col", str, "end", role="Column with the band end (bp)"),
    Param("band_col", str, "band", role="Column with the band name"),
    Param("stain_col", str, "gie_stain", role="Column with the Giemsa stain class"),
    Param("marker_pos_col", str, "pos", role="Marker table: column with the position (bp)"),
    Param("marker_label_col", str, "label", role="Marker table: column with the marker text (none: no text)"),
    # [Window]
    Param("x_min", float, None, unit="bp", role="Left end of a zoomed window (both x_min and x_max; none: whole chromosome)"),
    Param("x_max", float, None, unit="bp", role="Right end of a zoomed window"),
    # [Chromosome body]
    Param("stain_colors", dict, CODE_DEFAULT, open_keys=True, unit="hex color",
          role="Fill per stain class (default: grey scale from white gneg to near-black gpos100; module STAINS)"),
    Param("body_y", float, 0.4, unit="axes data units (0-1)", range=(0, 1), role="Height of the chromosome centre"),
    Param("body_height", float, 0.3, unit="axes data units (0-1)", range=(0, 1), role="Chromosome thickness"),
    Param("rounded", bool, True, role="Round the chromosome ends (whole-chromosome view)"),
    Param("round_frac", float, 0.012, unit="fraction of the chromosome length", range=(0, None),
          role="Radius of the rounded ends", tune="raise for rounder ends"),
    Param("outline_color", "color", "#1f2937", unit="hex color", role="Outline colour"),
    Param("outline_width", float, 0.5, unit="pt", range=(0, None), role="Outline width"),
    # [Band names]
    Param("show_band_labels", bool, True, role="Write band names"),
    Param("band_label_size", float, 5.0, unit="pt", range=(0, None), role="Band name size"),
    Param("band_label_rotation", float, 90.0, unit="degrees", role="Band name rotation"),
    Param("band_label_pad", float, 0.03, unit="axes data units", range=(0, None), role="Gap between body and band names"),
    Param("band_label_position", ("above", "inside"), "above",
          role="Band names above the body, or centred inside it (zoomed strip)"),
    Param("band_label_color", "color", "#111827", unit="hex color", role="Band name colour (above the body)"),
    Param("band_label_inside_color", "color", "#ffffff", unit="hex color",
          role="Band name colour inside a dark band (inside position)"),
    Param("dark_stains", list, ["gpos66", "gpos75", "gpos100"], role="Stains on which inside text uses band_label_inside_color"),
    Param("band_label_clear_frac", float, 0.0, unit="fraction of the shown width", range=(0, 1),
          role="Band names centred this close to a marker are left out (0: keep all)",
          tune="raise if a marker arrow covers a band name"),
    Param("band_label_min_frac", float, 0.0, unit="fraction of the shown width", range=(0, 1),
          role="Bands narrower than this get no name", tune="raise if names collide"),
    # [Ruler]
    Param("show_ruler", bool, False, role="Draw a position axis (zoomed view)"),
    Param("ruler_position", ("top", "bottom"), "top", role="Side of the position axis"),
    Param("ruler_unit_bp", float, 1e6, unit="bp per tick unit", range=(1, None), role="Tick unit (1e6: Mb, 1e3: kb)"),
    Param("ruler_suffix", str, " Mb", role="Text after each tick value"),
    Param("ruler_decimals", int, 2, unit="digits", range=(0, None), role="Decimals in tick values"),
    Param("ruler_nbins", int, 5, unit="ticks", range=(1, None), role="Approximate number of ruler ticks"),
    # [Markers]
    Param("marker_color", "color", "#111827", unit="hex color", role="Marker arrow and text colour"),
    Param("marker_style", ("arrow", "line"), "arrow", role="Arrow from above, or a vertical line through the body"),
    Param("marker_length", float, 0.25, unit="axes data units", range=(0, None), role="Length of a marker arrow"),
    Param("marker_width", float, 1.0, unit="pt", range=(0, None), role="Marker line width"),
    Param("marker_head", float, 6.0, unit="pt", range=(0, None), role="Marker arrow head size (head is 0.4 x this long)"),
    Param("marker_label_size", float, 6.0, unit="pt", range=(0, None), role="Marker text size"),
    # [Text]
    Param("labels_title", str, None, role="Name under the chromosome, e.g. 'Chromosome 2' (none: no name)"),
    *typography(title_size=8.0),
    Param("tick_label_size", float, None, unit="pt", range=(0, None), role="Ruler tick label size (default: rcParams)"),
    Param("title_y", float, 0.0, unit="axes data units (0-1)", role="Height of the name's top edge"),
    Param("text_color", "color", "#111827", unit="hex color", role="Colour of the name"),
])


@uses_schema(SCHEMA)
def render_chromosome_ideogram(ax, df, params, markers=None):
    """Draw the chromosome onto ``ax``; returns the markers with ``y_top``."""
    s_col, e_col = params.get("start_col", "start"), params.get("end_col", "end")
    b_col, st_col = params.get("band_col", "band"), params.get("stain_col", "gie_stain")
    bands = df.sort_values(s_col).reset_index(drop=True)
    c0, c1 = float(bands[s_col].min()) - 1, float(bands[e_col].max())
    lo, hi = params.get("x_min"), params.get("x_max")
    zoom = lo is not None and hi is not None
    x0, x1 = (float(lo), float(hi)) if zoom else (c0, c1)
    y, h = float(params.get("body_y", 0.4)), float(params.get("body_height", 0.3))
    stains = params.get("stain_colors", STAINS)
    ow = float(params.get("outline_width", 0.5))
    oc = params.get("outline_color", "#1f2937")

    shown = bands[(bands[e_col] >= x0) & (bands[s_col] - 1 <= x1)]
    if params.get("rounded", True) and not zoom:
        r = (c1 - c0) * float(params.get("round_frac", 0.012))
        clip = FancyBboxPatch((c0, y - h / 2), c1 - c0, h, boxstyle=f"round,pad=0,rounding_size={r}",
                              mutation_aspect=h / 2 / r if r else 1, facecolor="none", edgecolor=oc, linewidth=ow,
                              zorder=3)
    else:
        a, b = max(c0, x0), min(c1, x1)
        clip = Rectangle((a, y - h / 2), b - a, h, facecolor="none", edgecolor=oc, linewidth=ow, zorder=3)
    ax.add_patch(clip)
    for _, band in shown.iterrows():
        a, b = max(float(band[s_col]) - 1, x0), min(float(band[e_col]), x1)
        rect = Rectangle((a, y - h / 2), b - a, h, facecolor=stains.get(str(band[st_col]), "#ffffff"),
                         edgecolor="none", zorder=2)
        ax.add_patch(rect)
        rect.set_clip_path(clip)

    if params.get("show_band_labels", True):
        min_w = float(params.get("band_label_min_frac", 0.0)) * (x1 - x0)
        inside = params.get("band_label_position", "above") == "inside"
        dark = set(params.get("dark_stains", ["gpos66", "gpos75", "gpos100"]))
        clear = float(params.get("band_label_clear_frac", 0.0)) * (x1 - x0)
        mpos = [] if markers is None or not len(markers) else             [float(v) for v in markers[params.get("marker_pos_col", "pos")]]
        for _, band in shown.iterrows():
            a, b = max(float(band[s_col]) - 1, x0), min(float(band[e_col]), x1)
            if b - a < min_w or any(abs((a + b) / 2 - m) < clear for m in mpos):
                continue
            if inside:
                color = params.get("band_label_inside_color", "#ffffff") if str(band[st_col]) in dark \
                    else params.get("band_label_color", "#111827")
                ax.text((a + b) / 2, y, str(band[b_col]), ha="center", va="center", color=color, zorder=4,
                        fontsize=float(params.get("band_label_size", 5.0)))
            else:
                ax.text((a + b) / 2, y + h / 2 + float(params.get("band_label_pad", 0.03)), str(band[b_col]),
                        ha="center", va="bottom", rotation=float(params.get("band_label_rotation", 90.0)),
                        color=params.get("band_label_color", "#111827"),
                        fontsize=float(params.get("band_label_size", 5.0)))

    out = pd.DataFrame(columns=["pos", "label", "y_top"])
    if markers is not None and len(markers):
        p_col, l_col = params.get("marker_pos_col", "pos"), params.get("marker_label_col", "label")
        mc = params.get("marker_color", "#111827")
        top = y + h / 2
        length = float(params.get("marker_length", 0.25))
        rows = []
        for _, m in markers.iterrows():
            pos = float(m[p_col])
            label = m[l_col] if l_col and l_col in markers and pd.notna(m[l_col]) else None
            if params.get("marker_style", "arrow") == "arrow":
                ax.annotate("", xy=(pos, top), xytext=(pos, top + length),
                            arrowprops=dict(arrowstyle="-|>", mutation_scale=float(params.get("marker_head", 6.0)),
                                            color=mc, linewidth=float(params.get("marker_width", 1.0)),
                                            shrinkA=0, shrinkB=0), zorder=5)
                ty = top + length
            else:
                ax.plot([pos, pos], [y - h / 2, top + length], color=mc,
                        linewidth=float(params.get("marker_width", 1.0)), zorder=5)
                ty = top + length
            if label:
                ax.text(pos, ty, str(label), ha="center", va="bottom", color=mc,
                        fontsize=float(params.get("marker_label_size", 6.0)))
            rows.append({"pos": pos, "label": label, "y_top": ty})
        out = pd.DataFrame(rows)

    ax.set_xlim(x0, x1)
    ax.set_ylim(0, 1)
    for side in ("left", "right", "top", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_yticks([])
    if params.get("show_ruler", False):
        unit = float(params.get("ruler_unit_bp", 1e6))
        dec, suffix = int(params.get("ruler_decimals", 2)), params.get("ruler_suffix", " Mb")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=int(params.get("ruler_nbins", 5))))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / unit:.{dec}f}{suffix}"))
        pos = params.get("ruler_position", "top")
        ax.xaxis.set_ticks_position(pos)
        ax.spines[pos].set_visible(True)
        tick_sz = params.get("tick_label_size")
        if tick_sz is not None:
            ax.tick_params(labelsize=tick_sz)
    else:
        ax.set_xticks([])
    title = text_param(params, "labels_title", None)
    if title:
        ax.text((max(c0, x0) + min(c1, x1)) / 2, float(params.get("title_y", 0.0)), title, ha="center", va="bottom",
                color=params.get("text_color", "#111827"), fontsize=params.get("title_size", 8.0))
    return out
