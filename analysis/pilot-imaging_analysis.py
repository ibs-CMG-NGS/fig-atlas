"""pilot-imaging: an imaging figure from the domain-neutral core only (roadmap 6a.4).

Public data: BBBC013v1 (U2OS cells, FKHR-EGFP cytoplasm-to-nucleus translocation,
DRAQ5 DNA counterstain; CC BY 3.0, Ilya Ravkin, Broad Bioimage Benchmark
Collection). Fetch with `python scripts/fetch_bbbc013.py`.

  a  Representative images, no drug vs 150 nM Wortmannin (render_image_panel:
     same linear display range; adjustments recorded with the source hashes).
  b  Nuclear / cytoplasmic GFP per well, no drug vs 150 nM Wortmannin
     (render_bar_scatter; Welch test through fig_atlas.stats, table published).
  c  Dose response, mean +/- SEM of the replicate wells (render_line_band).

Quantification per well: nuclei = DNA channel above an Otsu threshold (opened,
small objects dropped); cytoplasm = a ring around the nuclei; ratio = mean
background-subtracted GFP in nuclei / in the ring. Every setting is in
configs/config_pilot-imaging.yaml. No omics module is imported.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
                            if (p / ".fig-atlas").is_file())))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from fig_atlas import claims, get_config, save_page_figure, source_data, stats  # noqa: E402
from fig_atlas.images import load  # noqa: E402
from fig_atlas.renderers import (  # noqa: E402
    place_panel_tags,
    render_bar_scatter,
    render_image_panel,
    render_line_band,
)

CONFIG = get_config()
CFG = CONFIG._raw
RAW = CONFIG.raw_root
IMAGES = RAW / "images" / "BBBC013_v1_images_bmp"
OUT = CONFIG.figures_root


# ------------------------------------------------------------------- plate --
def plate_map() -> pd.DataFrame:
    """One row per well: row letter, column, dose (the plate map's values, A01..H12 order)."""
    values = [v for v in (RAW / "BBBC013_v1_platemap_all.txt").read_text().split("\n")[1:] if v.strip()]
    wells = [(r, c) for r in "ABCDEFGH" for c in range(1, 13)]
    df = pd.DataFrame([{"row": r, "col": c, "index": i + 1, "dose": float(v)}
                       for i, ((r, c), v) in enumerate(zip(wells, values))])
    df["well"] = df["row"] + "-" + df["col"].map("{:02d}".format)
    return df


def image_path(channel: int, well: pd.Series) -> Path:
    return IMAGES / f"Channel{channel}-{int(well['index']):02d}-{well['well']}.BMP"


# ---------------------------------------------------------- quantification --
def otsu(a: np.ndarray) -> float:
    hist, _ = np.histogram(a, bins=256, range=(0, 256))
    p = hist / hist.sum()
    w = np.cumsum(p)
    mu = np.cumsum(p * np.arange(256))
    between = (mu[-1] * w - mu) ** 2 / (w * (1 - w) + 1e-12)
    return float(np.argmax(between))


def nuclear_ratio(well: pd.Series, seg: dict) -> tuple[float, int]:
    gfp = load(image_path(1, well)).astype(float)
    dna = load(image_path(2, well)).astype(float)
    t = otsu(dna) if seg.get("threshold", "otsu") == "otsu" else float(seg["threshold"])
    mask = ndi.binary_opening(dna > t, iterations=int(seg.get("opening_iter", 2)))
    lab, n = ndi.label(mask)
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.flatnonzero(sizes >= float(seg.get("min_nucleus_px", 30))))
    gap, width = int(seg.get("ring_gap_px", 1)), int(seg.get("ring_width_px", 5))
    ring = ndi.binary_dilation(keep, iterations=gap + width) & ~ndi.binary_dilation(keep, iterations=gap)
    bg = np.percentile(gfp, float(seg.get("background_percentile", 1)))
    return float((gfp[keep].mean() - bg) / (gfp[ring].mean() - bg)), int((sizes >= float(seg.get("min_nucleus_px", 30))).sum())


def quantify() -> pd.DataFrame:
    pc = CFG.get("plate", {})
    plate = plate_map()
    plate = plate[plate["row"].isin(pc.get("rows", ["A", "B", "C", "D"]))].copy()
    group = {c: "control" for c in pc.get("negative_cols", [1, 2])}
    group.update({c: "positive" for c in pc.get("positive_cols", [12])})
    group.update({c: "dose" for c in pc.get("dose_cols", list(range(3, 12)))})
    plate["group"] = plate["col"].map(group)
    plate = plate.dropna(subset=["group"])
    seg = CFG.get("segmentation", {})
    res = plate.apply(lambda w: nuclear_ratio(w, seg), axis=1, result_type="expand")
    plate["ratio"], plate["n_nuclei"] = res[0], res[1].astype(int)
    return plate.reset_index(drop=True)


# -------------------------------------------------------------------- figure --
def main() -> None:
    fcfg = CFG.get("figures", {})
    plt.rcParams.update({"font.family": fcfg.get("font_family", "DejaVu Sans")})   # CLAUDE.md 1.4
    wells = quantify()
    ctrl = wells[wells["group"] == "control"]
    pos = wells[wells["group"] == "positive"]
    h, w = load(image_path(1, wells.iloc[0])).shape[:2]
    claims.record("image_size", f"{w} x {h}", source="pixel dimensions of the BBBC013 images")
    claims.record("license", CFG.get("data", {}).get("license", ""), source="BBBC013 page, bbbc.broadinstitute.org/BBBC013")
    claims.record("n_control_wells", len(ctrl), source="BBBC013 rows A-D, no-drug wells")
    claims.record("n_positive_wells", len(pos), source="BBBC013 rows A-D, 150 nM Wortmannin wells")
    claims.record("n_nuclei_total", int(wells["n_nuclei"].sum()), source="nuclei segmented in the wells used")
    claims.record("ratio_control_mean", float(ctrl["ratio"].mean()), source="mean nuclear/cytoplasmic GFP, no drug")
    claims.record("ratio_positive_mean", float(pos["ratio"].mean()), source="mean nuclear/cytoplasmic GFP, 150 nM")

    # Statistics through the stats layer: Welch test of treated vs no-drug wells.
    bcfg = CFG.get("plots", {}).get("ratio_bars", {})
    test = stats.compare_to_control({"no drug": ctrl["ratio"], "Wortmannin 150 nM": pos["ratio"]},
                                    control="no drug", test=bcfg.get("stat_test", "welch"))
    stats.record(test, name="ratio_vs_no_drug", title="Nuclear/cytoplasmic GFP per well, 150 nM Wortmannin vs no drug")
    claims.record("star_rule", stats.describe(bcfg.get("stat_test", "welch"), "none", bcfg.get("star_thresholds"),
                                              against="no-drug wells"))
    claims.record("p_ratio", float(test.loc[0, "p"]), source="Welch test, panel b")

    W = CONFIG.page.content_width_mm if CONFIG.page is not None else 184.6
    fig_w, fig_h = (CONFIG.page.figure_size_in(height_mm=float(fcfg.get("height_mm", 62)))
                    if CONFIG.page is not None else (W / 25.4, float(fcfg.get("height_mm", 62)) / 25.4))
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=CONFIG.dpi)
    left, right, top, bottom = fcfg.get("margins", [0.03, 0.99, 0.86, 0.20])
    gs = fig.add_gridspec(1, 3, width_ratios=fcfg.get("width_ratios", [2.1, 0.9, 1.25]),
                          wspace=float(fcfg.get("wspace", 0.45)), left=left, right=right, top=top, bottom=bottom)
    gs_img = gs[0, 0].subgridspec(1, 2, wspace=float(fcfg.get("images_wspace", 0.06)))

    # a: images
    icfg = dict(CFG.get("plots", {}).get("images", {}))
    titles = icfg.pop("titles", ["No drug", "Wortmannin 150 nM"])
    plate = plate_map().set_index("well")
    ax_imgs = []
    for k, well in enumerate((icfg.pop("control_well", "A-01"), icfg.pop("treated_well", "A-12"))):
        ax = fig.add_subplot(gs_img[0, k])
        w = plate.loc[well].copy()
        w["well"] = well
        render_image_panel(ax, [image_path(1, w), image_path(2, w)],
                           {**icfg, "labels_title": titles[k], "panel": "a",
                            "show_channel_labels": icfg.get("show_channel_labels", True) and k == 0})
        ax_imgs.append(ax)

    # b: bars + points, stars from the stats-layer P
    ax_b = fig.add_subplot(gs[0, 1])
    wide = {"metric": ["ratio"], "p": [float(test.loc[0, "p"])]}
    for i, v in enumerate(ctrl["ratio"]):
        wide[f"c{i}"] = [v]
    for i, v in enumerate(pos["ratio"]):
        wide[f"w{i}"] = [v]
    colors = bcfg.get("colors", ["#9ca3af", "#16a34a"])
    names = bcfg.get("group_labels", ["No drug", "Wortmannin"])
    render_bar_scatter(ax_b, pd.DataFrame(wide), {
        "category_col": "metric", "pvalue_col": "p",
        "groups": [{"label": names[0], "color": colors[0], "columns": [f"c{i}" for i in range(len(ctrl))]},
                   {"label": names[1], "color": colors[1], "columns": [f"w{i}" for i in range(len(pos))]}],
        "sig_thresholds": bcfg.get("star_thresholds"), "bar_width": bcfg.get("bar_width", 0.7),
        "point_size": bcfg.get("point_size", 10), "point_jitter": bcfg.get("point_jitter", 0.08),
        "errorbar": bcfg.get("errorbar", "sem"), "capsize": bcfg.get("capsize", 2.0),
        "errorbar_width": bcfg.get("errorbar_width", 0.6), "y_headroom": bcfg.get("y_headroom", 1.25),
        "sig_line_width": bcfg.get("sig_line_width", 0.6), "sig_gap": bcfg.get("sig_gap", 0.04),
        "labels_xlabel": "", "labels_ylabel": bcfg.get("ylabel", "Nuclear / cytoplasmic GFP"),
        "xtick_mode": bcfg.get("xtick_mode", "group"), "axes_label_weight": bcfg.get("axes_label_weight", "normal"),
        "show_legend": bcfg.get("show_legend", False), "legend_loc": bcfg.get("legend_loc", "best"),
        "title_size": bcfg.get("title_size", 6.5),
        "axes_label_size": bcfg.get("axes_label_size", 6.0), "tick_label_size": bcfg.get("tick_label_size", 5.5)})
    source_data.add(wells[wells["group"].isin(["control", "positive"])][["well", "group", "dose", "n_nuclei", "ratio"]],
                    panel="b", title="Nuclear/cytoplasmic GFP per well")

    # c: dose response
    dcfg = CFG.get("plots", {}).get("dose_curve", {})
    ax_c = fig.add_subplot(gs[0, 2])
    doses = wells[wells["group"] == "dose"]
    summary = render_line_band(ax_c, doses, {
        "x_col": "dose", "y_col": "ratio", "x_log": True, "error": "sem", "show_points": dcfg.get("show_points", True),
        "group_colors": {None: dcfg.get("color", "#16a34a")}, "line_width": dcfg.get("line_width", 1.0),
        "marker_size": dcfg.get("marker_size", 2.5), "band_alpha": dcfg.get("band_alpha", 0.25),
        "point_size": dcfg.get("point_size", 6), "labels_xlabel": dcfg.get("xlabel", "Wortmannin (nM)"),
        "labels_ylabel": dcfg.get("ylabel", "Nuclear / cytoplasmic GFP"),
        "axes_label_size": dcfg.get("axes_label_size", 6.0), "tick_label_size": dcfg.get("tick_label_size", 5.5)})
    ax_c.axhline(float(ctrl["ratio"].mean()), color=dcfg.get("control_line_color", "#6b7280"),
                 linewidth=float(dcfg.get("control_line_width", 0.6)), linestyle=dcfg.get("control_line_style", "--"))
    source_data.add(summary, panel="c", title="Dose response: mean, SEM band and n per dose")

    tcfg = fcfg.get("tags", {})
    place_panel_tags(fig, [[("a", ax_imgs[:1])], [("b", [ax_b])], [("c", [ax_c])]],
                     float(tcfg.get("size", 9.0)), pad_pt=float(tcfg.get("pad_pt", 2.0)), align_rows=[["a", "b", "c"]])

    OUT.mkdir(parents=True, exist_ok=True)
    for fmt in CONFIG.formats:
        save_page_figure(fig, OUT / f"figure1_imaging_translocation.{fmt}")
    plt.close(fig)
    print(f"Saved figure: {OUT / 'figure1_imaging_translocation'}.{{{','.join(CONFIG.formats)}}}")


if __name__ == "__main__":
    main()
