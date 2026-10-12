"""Regenerate the gallery bundles in examples/gallery/ (synthetic data, fixed seed).

    python examples/make_gallery.py

One small bundle per basic shape. Each is a starting point: copy the folder
under raw_data/<project>/, replace inputs/data.csv with your own table (same
column names, or name yours in plot_params), then `fa ingest bundle`. The
gallery page (docs/reference/gallery.md, `fa reference`) shows the figure each
one draws, and a test builds every one of them. The data are simulated -- not
measurements. Re-running writes byte-identical files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent / "gallery"
SEED = 20261013


def _write(name: str, df: pd.DataFrame | None, meta: str, files: dict | None = None) -> None:
    b = HERE / name
    (b / "inputs").mkdir(parents=True, exist_ok=True)
    (b / "metadata").mkdir(parents=True, exist_ok=True)
    if df is not None:
        df.to_csv(b / "inputs" / "data.csv", index=False, lineterminator="\n")
    for fname, write in (files or {}).items():
        write(b / "inputs" / fname)
    (b / "metadata" / "metadata.yaml").write_text(meta, encoding="utf-8", newline="\n")


def line_band(rng):
    hours = np.arange(0, 25, 3)
    rows = []
    for strain, rate in (("wild type", 0.32), ("mutant", 0.22)):
        for rep in range(1, 4):
            for h in hours:
                od = 1.2 / (1 + np.exp(-rate * (h - 12)))
                rows.append({"strain": strain, "hour": int(h), "replicate": rep, "od600": round(float(od + rng.normal(0, 0.03)), 3)})
    return pd.DataFrame(rows)


def threshold_scatter(rng):
    from scipy import stats
    n, hits = 300, 25
    lfc = rng.normal(0, 0.3, n)
    idx = rng.choice(n, hits, replace=False)
    lfc[idx] += rng.choice([-1, 1], hits) * rng.uniform(1.0, 3.0, hits)
    p = 2 * stats.norm.sf(np.abs(lfc / rng.uniform(0.2, 0.35, n)))
    order = np.argsort(p)
    adj = np.minimum.accumulate((p[order] * n / np.arange(1, n + 1))[::-1])[::-1].clip(max=1)
    padj = np.empty(n)
    padj[order] = adj
    return pd.DataFrame({"gene": [f"G{i:03d}" for i in range(1, n + 1)], "log2_fold_change": lfc.round(3),
                         "padj": [float(f"{x:.3g}") for x in padj]})


def venn(rng):
    genes = [f"G{i:03d}" for i in range(1, 121)]
    a = set(rng.choice(genes, 60, replace=False))
    b = set(rng.choice(sorted(a), 25, replace=False)) | set(rng.choice(sorted(set(genes) - a), 30, replace=False))
    rows = [{"dataset": "drug A", "item": g} for g in sorted(a)] + [{"dataset": "drug B", "item": g} for g in sorted(b)]
    return pd.DataFrame(rows)


def violin(rng):
    rows = []
    for genotype, mu, sd in (("wild type", 1.8, 0.35), ("heterozygous", 1.5, 0.4), ("knockout", 1.1, 0.45)):
        rows += [{"genotype": genotype, "spines_per_um": round(float(v), 3)} for v in rng.normal(mu, sd, 40).clip(0.1)]
    return pd.DataFrame(rows)


def histogram(rng):
    rows = []
    for cond, mu in (("control", 12.0), ("treated", 15.0)):
        rows += [{"condition": cond, "cell_diameter_um": round(float(v), 2)} for v in rng.normal(mu, 2.0, 300)]
    return pd.DataFrame(rows)


def dose_response(rng):
    doses = np.round(np.logspace(-2, 2, 9), 4)
    rows = []
    for name, (ec50, hill) in {"compound A": (0.5, 1.2), "compound B": (5.0, 1.0)}.items():
        for d in doses:
            mean = 5 + 95 / (1 + (d / ec50) ** hill)
            rows += [{"compound": name, "dose_uM": d, "replicate": r, "viability": round(float(mean + rng.normal(0, 4)), 2)}
                     for r in range(1, 4)]
    return pd.DataFrame(rows)


def survival(rng):
    rows = []
    for group, scale in (("vehicle", 25.0), ("treated", 90.0)):
        t = rng.exponential(scale, 25)
        follow = rng.uniform(40, 90, 25)
        for i, (ti, fi) in enumerate(zip(t, follow), start=1):
            rows.append({"group": group, "mouse": f"{group[0].upper()}{i:02d}", "days": round(float(min(ti, fi)), 1),
                         "died": int(ti <= fi)})
    return pd.DataFrame(rows)


def stacked_bar(rng):
    rows = []
    for sample, shift in (("control 1", 0), ("control 2", 0), ("treated 1", 1), ("treated 2", 1)):
        props = np.array([0.45, 0.30, 0.15, 0.10]) + shift * np.array([-0.15, 0.05, 0.12, -0.02])
        counts = rng.multinomial(500, props / props.sum())
        rows += [{"sample": sample, "cell_type": c, "cells": int(n)}
                 for c, n in zip(("neurons", "astrocytes", "microglia", "oligodendrocytes"), counts)]
    return pd.DataFrame(rows)


def boxplot(rng):
    rows = []
    for treatment, mu in (("untreated", 1.0), ("low dose", 1.6), ("high dose", 2.6)):
        rows += [{"treatment": treatment, "relative_expression": round(float(v), 3)}
                 for v in rng.lognormal(np.log(mu), 0.25, 8)]
    return pd.DataFrame(rows)


def multi_group_heatmap(rng):
    samples = {"control": ["C1", "C2", "C3"], "day 1": ["D1_1", "D1_2", "D1_3"], "day 3": ["D3_1", "D3_2", "D3_3"]}
    rows = []
    for g in range(1, 21):
        pattern = rng.choice([-1, 0, 1], 3)
        row = {"gene_label": f"G{g:03d}"}
        for (grp, cols), level in zip(samples.items(), pattern):
            for c in cols:
                row[c] = round(float(level + rng.normal(0, 0.3)), 3)
        rows.append(row)
    return pd.DataFrame(rows)


def image_files(rng):
    from PIL import Image
    yy, xx = np.mgrid[0:180, 0:240]
    nuc, cyto = np.zeros((180, 240)), np.zeros((180, 240))
    for cx, cy in rng.uniform([25, 25], [215, 155], size=(9, 2)):
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2
        nuc += 3000 * np.exp(-r2 / 70)
        cyto += 1500 * np.exp(-r2 / 450)
    def saver(arr):
        return lambda path: Image.fromarray((arr + rng.normal(100, 20, arr.shape)).clip(0, 65535)
                                            .astype(np.uint16)).save(path)
    return {"dapi.tif": saver(nuc), "tubulin.tif": saver(cyto)}


HEAD = "# Gallery example (examples/make_gallery.py): synthetic data, not measurements.\n"
META = {
    "line_band": HEAD + """# inputs/data.csv: one row per replicate measurement -- strain (line), hour (x), od600 (y).
# With your data: keep these columns, or name yours in plot_params (x_col, y_col, group_col).
plot_type: line_band
plot_params:
  x_col: hour
  y_col: od600
  group_col: strain
  error: sd
  labels_title: "Growth"
  labels_xlabel: "Time (h)"
  labels_ylabel: "OD600"
""",
    "threshold_scatter": HEAD + """# inputs/data.csv: one row per gene -- log2_fold_change (x), padj (y, shown as -log10).
plot_type: threshold_scatter
plot_params:
  x_col: log2_fold_change
  y_col: padj
  effect_col: log2_fold_change
  sig_col: padj
  y_transform: neg_log10
  effect_threshold: 1.0
  sig_threshold: 0.05
  label_mode: top_n
  label_cols: ["gene"]
  label_top_n: 5
  labels_title: "Treated vs control"
  labels_xlabel: "log2 fold change"
  labels_ylabel: "-log10 adjusted P"
""",
    "venn": HEAD + """# inputs/data.csv: one row per (list, item) -- dataset (which list), item (e.g. a gene); 2 or 3 lists.
plot_type: venn
plot_params:
  set_labels: ["drug A", "drug B"]
  filter_name: "Genes changed"
  title_size: 7                 # pt; the title and its count line (the renderer's own default is for a larger canvas)
""",
    "violin": HEAD + """# inputs/data.csv: one row per measurement -- genotype (category), spines_per_um (value).
plot_type: violin
plot_params:
  x_col: genotype
  y_col: spines_per_um
  x_order: ["wild type", "heterozygous", "knockout"]
  show_points: true
  labels_ylabel: "Spine density (per um)"
  labels_xlabel: ""
""",
    "histogram": HEAD + """# inputs/data.csv: one row per cell -- condition (group), cell_diameter_um (value).
plot_type: histogram
plot_params:
  x_col: cell_diameter_um
  group_col: condition
  bins: 25
  density: true
  labels_xlabel: "Cell diameter (um)"
""",
    "dose_response": HEAD + """# inputs/data.csv: one row per replicate -- compound (group), dose_uM (x, > 0), viability (y).
# The fitted EC50 per compound is in the figure's source data (four-parameter logistic).
plot_type: dose_response
plot_params:
  x_col: dose_uM
  y_col: viability
  group_col: compound
  show_ec50: true
  labels_xlabel: "Dose (uM)"
  labels_ylabel: "Viability (% of control)"
""",
    "survival": HEAD + """# inputs/data.csv: one row per animal -- group, days (to death or last follow-up), died (1) or censored (0).
# No test is drawn; compare groups with a log-rank test through fig_atlas.stats.
plot_type: survival
plot_params:
  time_col: days
  event_col: died
  group_col: group
  labels_xlabel: "Days"
""",
    "stacked_bar": HEAD + """# inputs/data.csv: one row per (sample, cell type) -- sample (bar), cell_type (part), cells (count).
plot_type: stacked_bar
plot_params:
  x_col: sample
  stack_col: cell_type
  value_col: cells
  stack_colors: {neurons: "#0072B2", astrocytes: "#E69F00", microglia: "#009E73", oligodendrocytes: "#CC79A7"}   # Okabe-Ito: safe for colour-blind readers
  labels_xlabel: ""
""",
    "boxplot": HEAD + """# inputs/data.csv: one row per sample -- treatment (category), relative_expression (value).
plot_type: boxplot
plot_params:
  x_col: treatment
  y_col: relative_expression
  labels_xlabel: ""
  labels_ylabel: "Relative expression"
""",
    "multi_group_heatmap": HEAD + """# inputs/data.csv: one row per gene -- gene_label, then one column per sample (values, e.g. z-scores).
# sample_groups names which columns belong to which group (annotation strip above the heatmap).
plot_type: multi_group_heatmap
plot_params:
  gene_label_col: gene_label
  sample_groups:
    control: ["C1", "C2", "C3"]
    "day 1": ["D1_1", "D1_2", "D1_3"]
    "day 3": ["D3_1", "D3_2", "D3_3"]
  cluster_rows: true
  gene_fontsize: 5              # pt; row labels
  tick_label_size: 6            # pt; sample names and colour-bar ticks
  axes_label_size: 7            # pt; colour-bar title
  colorbar_pad: 0.22            # fraction of the axes width between the gene names and the colour bar
  group_colors: {control: "#9CA3AF", "day 1": "#E69F00", "day 3": "#D55E00"}   # hex; the group strip above the columns
  margin_bottom: 0.2            # fraction of the figure; room for the sample names below
  margin_right: 0.8             # fraction of the figure; room for the colour bar and its title
""",
    "image_panel": HEAD + """# inputs/: one image file per channel (16-bit TIFF here). Images are shown from these files,
# never from an adjusted copy; the display range per channel is set below.
plot_type: image_panel
pixel_size: 0.25
pixel_unit: "µm"
channels:
  - file: "dapi.tif"
  - file: "tubulin.tif"
plot_params:
  channel_colors: ["#3b82f6", "#22c55e"]
  channel_labels: ["DAPI", "tubulin"]
  display_ranges: [[100, 3000], [100, 1600]]
  show_channel_labels: true
  pixel_size: 0.25
  scale_bar: 10
""",
}


def main() -> None:
    rng = np.random.default_rng(SEED)
    makers = {"line_band": line_band, "threshold_scatter": threshold_scatter, "venn": venn, "violin": violin,
              "histogram": histogram, "dose_response": dose_response, "survival": survival,
              "stacked_bar": stacked_bar, "boxplot": boxplot, "multi_group_heatmap": multi_group_heatmap}
    for name, make in makers.items():
        _write(name, make(rng), META[name])
    _write("image_panel", None, META["image_panel"], image_files(rng))
    print(f"wrote {len(META)} bundles in {HERE}")


if __name__ == "__main__":
    main()
