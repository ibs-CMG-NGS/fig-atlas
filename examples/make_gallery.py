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


def group_scatter(rng):
    rows = []
    for batch, shift in (("batch 1", 0.0), ("batch 2", 0.3)):
        for i in range(1, 16):
            x = rng.uniform(20, 60)
            rows.append({"library": f"{batch[-1]}{i:02d}", "batch": batch, "frip_pct": round(float(x), 2),
                         "signal_log2": round(float(0.03 * x - 1.0 + shift + rng.normal(0, 0.15)), 3)})
    df = pd.DataFrame(rows)
    # What the figure prints comes from the analysis, not from the renderer
    # (docs/decisions/0007): the correlation is computed here, once, and travels
    # to the figure as a column. No extra random draws, so later bundles are unchanged.
    from scipy.stats import pearsonr
    r, p = pearsonr(df["frip_pct"], df["signal_log2"])
    df["r"], df["p_value"] = float(r), float(p)
    return df


def effect_dots(rng):
    rows = []
    for item, est in (("age (per 10 y)", 0.35), ("smoking", 0.6), ("BMI (per 5)", 0.2), ("diabetes", 0.45),
                      ("statin use", -0.3)):
        for model, shrink in (("unadjusted", 1.0), ("adjusted", 0.7)):
            e = est * shrink + rng.normal(0, 0.03)
            se = 0.1 + rng.uniform(0, 0.05)
            rows.append({"factor": item, "model": model, "log_odds_ratio": round(float(e), 3),
                         "ci_low": round(float(e - 1.96 * se), 3), "ci_high": round(float(e + 1.96 * se), 3)})
    return pd.DataFrame(rows)


def bar_scatter(rng):
    rows = []
    for gene, ko in (("Gfap", 2.4), ("Aqp4", 1.6), ("S100b", 1.1), ("Aldh1l1", 0.6)):
        for cond, mu in (("control", 1.0), ("knockout", ko)):
            rows += [{"gene": gene, "condition": cond, "relative_mrna": round(float(v), 3)}
                     for v in rng.lognormal(np.log(mu), 0.15, 4)]
    return pd.DataFrame(rows)


def heatmap(rng):
    rows = []
    for g in range(1, 26):
        up = rng.choice([-1, 1]) * rng.uniform(0.5, 2.0)
        row = {"gene": f"G{g:03d}"}
        for s in ("ctrl_1", "ctrl_2", "ctrl_3"):
            row[s] = round(float(5 + rng.normal(0, 0.3)), 3)
        for s in ("trt_1", "trt_2", "trt_3"):
            row[s] = round(float(5 + up + rng.normal(0, 0.3)), 3)
        rows.append(row)
    return pd.DataFrame(rows)


def pca(rng):
    genes = 300
    base = rng.lognormal(5, 1, genes)
    effect = np.where(rng.random(genes) < 0.2, rng.lognormal(0, 0.8, genes), 1.0)
    data = {"gene": [f"G{i:04d}" for i in range(1, genes + 1)]}
    for s in ("ctrl_1", "ctrl_2", "ctrl_3", "ctrl_4"):
        data[s] = rng.poisson(base).astype(int)
    for s in ("trt_1", "trt_2", "trt_3", "trt_4"):
        data[s] = rng.poisson(base * effect).astype(int)
    return pd.DataFrame(data)


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


# --- field-pack (omics) plot types: one example each -----------------------------------------
def _de_table(rng, n=400):
    from scipy import stats
    lfc = rng.normal(0, 0.35, n)
    idx = rng.choice(n, 40, replace=False)
    lfc[idx] += rng.choice([-1, 1], 40) * rng.uniform(1.0, 3.5, 40)
    se = rng.uniform(0.2, 0.4, n)
    p = 2 * stats.norm.sf(np.abs(lfc / se))
    order = np.argsort(p)
    adj = np.minimum.accumulate((p[order] * n / np.arange(1, n + 1))[::-1])[::-1].clip(max=1)
    padj = np.empty(n)
    padj[order] = adj
    return lfc, p, padj


def volcano(rng):
    lfc, p, padj = _de_table(rng)
    n = len(lfc)
    return pd.DataFrame({"gene_id": [f"ENSG{i:011d}" for i in range(1, n + 1)],
                         "symbol": [f"GENE{i}" for i in range(1, n + 1)],
                         "base_mean": (10 ** rng.uniform(1, 4, n)).round(1), "log2FC": lfc.round(3),
                         "pvalue": [float(f"{x:.3g}") for x in p], "padj": [float(f"{x:.3g}") for x in padj]})


def ma_plot(rng):
    lfc, _, padj = _de_table(rng)
    n = len(lfc)
    return pd.DataFrame({"peak": [f"peak{i}" for i in range(1, n + 1)], "baseMean": (10 ** rng.uniform(1, 3.5, n)).round(1),
                         "log2FoldChange": lfc.round(3), "padj": [float(f"{x:.3g}") for x in padj]})


_TERMS = ["response to oxidative stress", "regulation of cell cycle", "DNA repair", "apoptotic process",
          "synapse organization", "axon guidance", "inflammatory response", "autophagy"]


def go_bar(rng):
    n = len(_TERMS)
    counts = rng.integers(8, 60, n)
    return pd.DataFrame({"term_id": [f"GO:00{i:05d}" for i in range(n)], "description": _TERMS,
                         "gene_ratio": [f"{c}/350" for c in counts], "gene_count": counts,
                         "fdr": [float(f"{x:.3g}") for x in 10 ** -rng.uniform(1.5, 9, n)],
                         "fold_enrichment": rng.uniform(1.5, 5, n).round(2)})


def go_cluster_dot(rng):
    df = go_bar(rng)
    df.insert(0, "cluster_id", range(len(df)))
    df["_cluster_size"] = rng.integers(1, 12, len(df))
    return df


def count_summary(rng):
    rows = []
    for ds, spread in (("Acute D1", 1.3), ("Acute D3", 1.0), ("Chronic 24h", 1.6)):
        lfc = rng.normal(0, spread, 500)
        rows += [{"dataset": ds, "gene": f"G{i}", "log2fc": round(float(v), 3),
                  "adj_pvalue": 0.001 if abs(v) > 1.4 else 0.4} for i, v in enumerate(lfc)]
    return pd.DataFrame(rows)


def _cross_condition(rng):
    rows = []
    for t in _TERMS[:6]:
        for c in ("Acute D1", "Acute D3", "Chronic 24h", "Chronic 48h"):
            if rng.random() < 0.75:
                rows.append({"GO Term": t, "Condition": c,
                             "Signed -log10(FDR)": round(float(rng.choice([-1, 1]) * rng.uniform(1.4, 6)), 2),
                             "Gene Ratio": round(float(rng.uniform(0.02, 0.3)), 3)})
    return pd.DataFrame(rows)


def cross_condition_heatmap(rng):
    return _cross_condition(rng)


def cross_condition_dotplot(rng):
    return _cross_condition(rng)


def motif_dotplot(rng):
    rows = []
    for m in ("AP-1", "NRF2", "KLF", "CTCF", "TEAD", "CEBP"):
        for c in ("Acute D1", "Acute D3", "Chronic 24h", "Chronic 48h"):
            sig = rng.random() < 0.55
            rows.append({"motif": m, "pattern_class": c,
                         "log2fc": round(float(rng.normal(0, 1.1)), 2) if sig else None,
                         "neg_log10_p": round(float(rng.uniform(2, 15)), 1) if sig else None})
    return pd.DataFrame(rows)


def peak_feature_enrichment(rng):
    # Fixed shares, so the legend (upper left of the last panel) sits where its bars leave room.
    bg = np.array([25.0, 35.0, 30.0, 10.0])
    shares = {"total": [35.0, 30.0, 25.0, 10.0], "up": [45.0, 25.0, 20.0, 10.0], "down": [25.0, 40.0, 28.0, 7.0]}
    rows = []
    for gs, da in shares.items():
        for f, d, b in zip(("Promoter", "Intron", "Intergenic", "Exon"), da, bg):
            rows.append({"GeneSet": gs, "Feature": f, "DA_Pct": round(float(d), 2), "Background_Pct": b,
                         "OddsRatio": round(float((d / (100 - d)) / (b / (100 - b))), 3),
                         "p_adjust": float(f"{10 ** -rng.uniform(0, 6):.3g}")})
    return pd.DataFrame(rows)

# --- plot catalog (plans/PLAN_PLOT_CATALOG.md), appended so earlier examples keep their data ---
def paired_plot(rng):
    """Fasting glucose of 8 mice per arm at baseline and week 4. The paired t-test runs
    here, as an analysis script would (docs/howto/analysis_recipes.md, section 2);
    the renderer only draws the p_value column."""
    from scipy.stats import ttest_rel
    rows = []
    for arm, drop in (("vehicle", 0.0), ("drug", 1.6)):
        base = rng.normal(9.0, 1.0, 8)
        week4 = base - drop + rng.normal(0, 0.6, 8)
        p = float(ttest_rel(week4, base).pvalue)
        for i, (b, w) in enumerate(zip(base, week4), start=1):
            for cond, v in (("baseline", b), ("week 4", w)):
                rows.append({"mouse": f"{arm[0].upper()}{i}", "arm": arm, "timepoint": cond,
                             "glucose_mmol_l": round(float(v), 2), "p_value": float(f"{p:.3g}")})
    return pd.DataFrame(rows)


def grouped_bar(rng):
    """qPCR expression of a gene in three genotypes, three treatments, four replicates.
    Each treatment is compared with vehicle within a genotype by Dunnett's test, as an
    analysis script would (docs/howto/analysis_recipes.md, section 3); the renderer
    only draws the p_vs_vehicle column."""
    from scipy.stats import dunnett
    effect = {"vehicle": 0.0, "drug A": 0.9, "drug B": 0.25}
    rows = []
    for gt, base in (("WT", 1.0), ("Het", 0.8), ("KO", 0.5)):
        vals = {t: base + d * base + rng.normal(0, 0.12, 4) for t, d in effect.items()}
        res = dunnett(vals["drug A"], vals["drug B"], control=vals["vehicle"], random_state=0)  # seeded integration
        p = {"vehicle": None, "drug A": float(f"{res.pvalue[0]:.3g}"), "drug B": float(f"{res.pvalue[1]:.3g}")}
        for t, v in vals.items():
            rows += [{"genotype": gt, "treatment": t, "replicate": i, "rel_expression": round(float(x), 3),
                      "p_vs_vehicle": p[t]} for i, x in enumerate(v, start=1)]
    return pd.DataFrame(rows)


def correlation_scatter(rng):
    """Body weight and fat mass of mice on two diets, 14 per diet. The least-squares
    line, its 95% confidence band and Pearson r and P are computed per diet here, as
    an analysis script would (docs/howto/analysis_recipes.md, section 4), and travel
    as fit rows and r / p_value columns; the renderer only draws them."""
    from scipy.stats import pearsonr, t
    rows, fits = [], []
    for diet, slope, base in (("chow", 0.25, 2.0), ("high-fat", 0.55, 1.0)):
        w = rng.uniform(22, 38, 14)
        fat = base + slope * (w - 22) + rng.normal(0, 1.0, 14)
        r, p = pearsonr(w, fat)
        b, a = np.polyfit(w, fat, 1)
        resid = fat - (a + b * w)
        s = np.sqrt(resid @ resid / (len(w) - 2))
        grid = np.linspace(w.min(), w.max(), 25)
        half = t.ppf(0.975, len(w) - 2) * s * np.sqrt(1 / len(w) + (grid - w.mean()) ** 2 / ((w - w.mean()) ** 2).sum())
        rows += [{"diet": diet, "body_weight": round(float(x), 2), "fat_mass": round(float(y), 2),
                  "r": round(float(r), 4), "p_value": float(f"{p:.3g}")} for x, y in zip(w, fat)]
        fits += [{"diet": diet, "fit_x": round(float(x), 3), "fit_y": round(float(a + b * x), 4),
                  "ci_low": round(float(a + b * x - h), 4), "ci_high": round(float(a + b * x + h), 4)}
                 for x, h in zip(grid, half)]
    return pd.concat([pd.DataFrame(rows), pd.DataFrame(fits)], ignore_index=True)


def raincloud(rng):
    """Escape latency of mice in a water maze: vehicle and two doses, 16 mice each
    (the high dose skews long). Each dose is compared with vehicle by Dunnett's test,
    as an analysis script would (docs/howto/analysis_recipes.md, section 3); the
    renderer only draws the p_vs_vehicle column."""
    from scipy.stats import dunnett
    lat = {"vehicle": rng.normal(22, 5, 16), "low dose": rng.normal(27, 6, 16),
           "high dose": 25 + rng.gamma(2.0, 6.0, 16)}
    res = dunnett(lat["low dose"], lat["high dose"], control=lat["vehicle"], random_state=0)  # seeded integration
    p = {"vehicle": None, "low dose": float(f"{res.pvalue[0]:.3g}"), "high dose": float(f"{res.pvalue[1]:.3g}")}
    return pd.DataFrame([{"treatment": t, "mouse": i, "latency_s": round(float(x), 1), "p_vs_vehicle": p[t]}
                         for t, v in lat.items() for i, x in enumerate(v, start=1)])


def column_scatter(rng):
    """Plasma IL-6 of mice: sham, vehicle and two drugs, 12 mice each. Sham and each
    drug are compared with vehicle by Dunnett's test, as an analysis script would
    (docs/howto/analysis_recipes.md, section 3); the renderer only draws the
    p_vs_vehicle column."""
    from scipy.stats import dunnett
    il6 = {"sham": rng.normal(18, 4, 12), "vehicle": rng.normal(42, 9, 12),
           "drug A": rng.normal(27, 7, 12), "drug B": rng.normal(38, 9, 12)}
    others = ["sham", "drug A", "drug B"]
    res = dunnett(*(il6[k] for k in others), control=il6["vehicle"], random_state=0)  # seeded integration
    p = {"vehicle": None, **{k: float(f"{pv:.3g}") for k, pv in zip(others, res.pvalue)}}
    return pd.DataFrame([{"treatment": t, "mouse": i, "il6_pg_ml": round(float(x), 1), "p_vs_vehicle": p[t]}
                         for t, v in il6.items() for i, x in enumerate(v, start=1)])


def roc_curve(rng):
    """Two blood markers for a disease, 60 cases and 60 controls. The curves, the
    AUC (Mann-Whitney), its 95% bootstrap interval (1000 resamples) and the Youden
    point are computed here, as an analysis script would
    (docs/howto/analysis_recipes.md, section 5); the renderer only draws them."""
    from scipy.stats import rankdata
    labels = np.r_[np.ones(60), np.zeros(60)]

    def auc(y, s):
        r = rankdata(s)
        n1 = y.sum()
        return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))

    rows = []
    for marker, shift in (("marker A", 1.4), ("marker B", 0.6)):
        score = np.r_[rng.normal(shift, 1, 60), rng.normal(0, 1, 60)]
        order = np.argsort(-score, kind="stable")
        y = labels[order]
        tpr = np.r_[0.0, np.cumsum(y) / y.sum()]
        fpr = np.r_[0.0, np.cumsum(1 - y) / (1 - y).sum()]
        boot = []
        for _ in range(1000):
            k = np.r_[rng.integers(0, 60, 60), 60 + rng.integers(0, 60, 60)]
            boot.append(auc(labels[k], score[k]))
        lo, hi = np.percentile(boot, [2.5, 97.5])
        best = int(np.argmax(tpr - fpr))
        rows += [{"marker": marker, "fpr": round(float(f), 4), "tpr": round(float(t), 4),
                  "auc": round(float(auc(labels, score)), 4), "auc_ci_low": round(float(lo), 4),
                  "auc_ci_high": round(float(hi), 4), "youden": i == best}
                 for i, (f, t) in enumerate(zip(fpr, tpr))]
    return pd.DataFrame(rows)


def bland_altman(rng):
    """HbA1c of 40 patients by the laboratory method and a point-of-care device. The
    bias (mean difference) and the 95% limits of agreement (bias +/- 1.96 SD of the
    differences) are computed here, as an analysis script would; the renderer only
    draws them."""
    true = rng.uniform(5.0, 10.0, 40)
    lab = true + rng.normal(0, 0.15, 40)
    device = true + 0.12 + rng.normal(0, 0.25, 40)
    diff = lab - device
    bias, sd = float(diff.mean()), float(diff.std(ddof=1))
    return pd.DataFrame({"patient": range(1, 41), "hba1c_lab": lab.round(2), "hba1c_device": device.round(2),
                         "bias": round(bias, 4), "loa_low": round(bias - 1.96 * sd, 4),
                         "loa_high": round(bias + 1.96 * sd, 4)})


def correlation_matrix(rng):
    """Six clinical variables of 80 patients. Pearson r and P of every pair are
    computed here, as an analysis script would (docs/howto/analysis_recipes.md,
    section 4), and written one row per pair; the renderer only draws them."""
    from scipy.stats import pearsonr
    n = 80
    age = rng.normal(55, 10, n)
    bmi = rng.normal(27, 4, n)
    sbp = 90 + 0.6 * age + 0.8 * bmi + rng.normal(0, 8, n)
    glucose = 70 + 0.5 * bmi + 0.2 * age + rng.normal(0, 8, n)
    hdl = 75 - 0.9 * bmi + rng.normal(0, 7, n)
    steps = 12000 - 60 * age - 120 * bmi + rng.normal(0, 1500, n)
    wide = {"age": age, "BMI": bmi, "SBP": sbp, "glucose": glucose, "HDL": hdl, "steps": steps}
    names = list(wide)
    rows = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            r, p = pearsonr(wide[a], wide[b])
            rows.append({"var1": a, "var2": b, "r": round(float(r), 4), "p_value": float(f"{p:.3g}")})
    return pd.DataFrame(rows)

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
    "group_scatter": HEAD + """# inputs/data.csv: one row per library -- frip_pct (x), signal_log2 (y), batch (group), library (label);
# r and p_value hold the correlation the panel prints (computed by the analysis, drawn by the renderer).
plot_type: group_scatter
plot_params:
  x_col: frip_pct
  y_col: signal_log2
  group_col: batch
  group_colors: {"batch 1": "#0072B2", "batch 2": "#E69F00"}
  legend: true
  r_col: r
  p_col: p_value
  xlabel: "Fraction of reads in peaks (%)"
  ylabel: "Signal (log2)"
""",
    "effect_dots": HEAD + """# inputs/data.csv: one row per (factor, model) -- the estimate and its 95 % confidence limits.
plot_type: effect_dots
plot_params:
  item_col: factor
  series_col: model
  estimate_col: log_odds_ratio
  low_col: ci_low
  high_col: ci_high
  series_colors: {unadjusted: "#9CA3AF", adjusted: "#0072B2"}
  xlabel: "log odds ratio (95 % CI)"
""",
    "bar_scatter": HEAD + """# inputs/data.csv: one row per replicate -- gene (category), condition (bar colour), relative_mrna (value).
# Bars are the mean +/- SEM of the replicates; the dots are the replicates.
plot_type: bar_scatter
plot_params:
  category_col: gene
  group_col: condition
  value_col: relative_mrna
  group_colors: {control: "#9CA3AF", knockout: "#0072B2"}
  labels_ylabel: "mRNA (relative to control)"
  axes_label_size: 7            # pt; this renderer's own defaults are for a larger canvas
  tick_label_size: 6            # pt
  title_size: 8                 # pt
""",
    "heatmap": HEAD + """# inputs/data.csv: one row per gene -- gene (label), then one column per sample (values).
plot_type: heatmap
plot_params:
  label_col: gene
  sample_columns: ["ctrl_1", "ctrl_2", "ctrl_3", "trt_1", "trt_2", "trt_3"]
  sorting: clustering
  n_genes: 20                   # rows shown; up to max_gene_labels (20) are named
  tick_label_size: 6            # pt; this renderer's own defaults are for a larger canvas
  axes_label_size: 7            # pt
""",
    "pca": HEAD + """# inputs/data.csv: one row per gene -- gene, then one column of counts per sample.
# sample_groups names which columns belong to which group (point colour and legend).
plot_type: pca
plot_params:
  sample_groups:
    control: ["ctrl_1", "ctrl_2", "ctrl_3", "ctrl_4"]
    treated: ["trt_1", "trt_2", "trt_3", "trt_4"]
  group_colors: {control: "#9CA3AF", treated: "#0072B2"}
  show_labels: false
  title: ""
  point_size: 30                # pt^2; this renderer's own defaults are for a larger canvas
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
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
    "volcano": HEAD + """# inputs/data.csv: one row per tested gene -- gene_id, symbol, base_mean, log2FC, pvalue, padj
# (omics pack contract de_go.volcano: fig_atlas_omics/contracts/de_go_bundle_contract.md).
plot_type: volcano
plot_params:
  log2fc_threshold: 1.0
  padj_threshold: 0.05
  annotation_mode: top_n
  annotation_top_n: 5
  labels_title: "Treated vs control"
  title_size: 8                 # pt; the recipe's own sizes are for a larger canvas
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
  annotation_label_size: 6      # pt
  dot_size: 6                   # pt^2
""",
    "ma_plot": HEAD + """# inputs/data.csv: one row per peak -- baseMean (x, shown as log10), log2FoldChange (y), padj
# (omics pack contract de_go.ma_plot).
plot_type: ma_plot
plot_params:
  effect_threshold: 1.0
  labels_title: "Treated vs control"
  labels_xlabel: "log10 mean accessibility"
  labels_ylabel: "log2 fold change"
  title_size: 8                 # pt; the recipe's own sizes are for a larger canvas
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
  dot_size: 6                   # pt^2
""",
    "go_bar": HEAD + """# inputs/data.csv: one row per enriched term -- description, gene_ratio, gene_count, fdr, fold_enrichment
# (omics pack contract de_go.go_bar).
plot_type: go_bar
plot_params:
  top_n: 8
  x_axis: "-log10(FDR)"
  horizontal: true
  bar_color: "#2563eb"
  show_threshold_line: true
  labels_title: "GO biological process"
  title_size: 8                 # pt
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
""",
    "go_cluster_dot": HEAD + """# inputs/data.csv: one row per cluster representative term -- cluster_id, description, fdr, gene_ratio,
# fold_enrichment, _cluster_size (omics pack contract de_go.go_cluster_dot).
plot_type: go_cluster_dot
plot_params:
  x_axis: "-log10(FDR)"
  color_by: "Fold Enrichment"
  size_by: "Cluster size"
  top_n: 8
  labels_title: "GO BP clusters"
  title_size: 8                 # pt
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
""",
    "count_summary": HEAD + """# inputs/data.csv: one row per (dataset, gene) -- dataset, log2fc, adj_pvalue
# (omics pack contract integrated.count_summary).
plot_type: count_summary
plot_params:
  fdr_max: 0.05
  lfc_min: 1.0
  unit: "genes"
  show_legend: false
  labels_title: "Differentially expressed genes"
  title_size: 8                 # pt
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
  value_label_fontsize: 6       # pt
""",
    "cross_condition_heatmap": HEAD + """# inputs/data.csv: long format, one row per significant (term, condition) -- GO Term, Condition,
# Signed -log10(FDR), Gene Ratio (omics pack contract cross_condition.enrichment).
plot_type: cross_condition_heatmap
plot_params:
  condition_order: ["Acute D1", "Acute D3", "Chronic 24h", "Chronic 48h"]
  show_legend: false            # the seven-bin key needs more width than one column leaves; true in a wider figure
  title_size: 8                 # pt
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
""",
    "cross_condition_dotplot": HEAD + """# inputs/data.csv: the same long format as cross_condition_heatmap
# (omics pack contract cross_condition.enrichment).
plot_type: cross_condition_dotplot
plot_params:
  condition_order: ["Acute D1", "Acute D3", "Chronic 24h", "Chronic 48h"]
  size_legend_below: true       # the dot-size key under the plot, clear of the dots
  size_legend_below_offset_pts: 48   # pt below the axes; clears the rotated condition labels
  title_size: 8                 # pt
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
""",
    "motif_dotplot": HEAD + """# inputs/data.csv: long format, one row per (motif, condition) -- motif, pattern_class, log2fc,
# neg_log10_p; empty where not significant (omics pack contract atac_feature.motif_enrichment).
plot_type: motif_dotplot
plot_params:
  class_order: ["Acute D1", "Acute D3", "Chronic 24h", "Chronic 48h"]
  fc_min: -2
  fc_max: 2
  size_scale: 4.0               # pt^2 per -log10(P) unit
  labels_title: "Motif enrichment"
  title_size: 8                 # pt
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
""",
    "peak_feature_enrichment": HEAD + """# inputs/data.csv: one row per (peak set, genomic feature) -- GeneSet, Feature, OddsRatio, p_adjust,
# DA_Pct, Background_Pct (omics pack contract atac_feature.peak_features).
plot_type: peak_feature_enrichment
plot_params:
  geneset_order: ["total", "up", "down"]
  fdr_max: 0.05
  legend_loc: "upper left"      # of the last panel; move it where that panel's bars leave room
  labels_title: ""              # the panel titles (total, up, down) say it; a figure title would sit on them
  title_size: 8                 # pt
  axes_label_size: 7            # pt
  tick_label_size: 6            # pt
""",
    "paired_plot": HEAD + """# inputs/data.csv: one row per (mouse, timepoint) -- mouse (subject), arm (group), timepoint (condition),
# glucose_mmol_l (value), p_value (each arm's paired t-test, computed when the data were made -- the
# renderer draws it, it runs no test). With your data: keep these columns, or name yours below.
plot_type: paired_plot
plot_params:
  subject_col: mouse
  condition_col: timepoint
  value_col: glucose_mmol_l
  group_col: arm
  pvalue_col: p_value
  condition_order: ["baseline", "week 4"]
  group_order: ["vehicle", "drug"]
  condition_labels: {"baseline": "Base", "week 4": "Wk 4"}
  summary: mean
  summary_style: bar            # the mean as a bar per timepoint, subjects on top; line joins the means instead
  summary_error: sem            # error bar on the bar: sd, sem or ci95 (say which in the legend)
  group_colors: {"vehicle": "#6b7280", "drug": "#2563eb"}
  labels_ylabel: "Fasting glucose (mmol/l)"
""",
    "grouped_bar": HEAD + """# inputs/data.csv: one row per replicate -- genotype (category), treatment (group), rel_expression (value),
# p_vs_vehicle (each treatment's Dunnett P against vehicle within a genotype, computed when the data were
# made -- the renderer draws it, it runs no test). With your data: keep these columns, or name yours below.
plot_type: grouped_bar
plot_params:
  category_col: genotype
  group_col: treatment
  value_col: rel_expression
  pvalue_col: p_vs_vehicle
  control_group: vehicle
  category_order: ["WT", "Het", "KO"]
  group_order: ["vehicle", "drug A", "drug B"]
  arrangement: interleaved      # or separated: one block of genotypes per treatment
  error: sem                    # sd, sem or ci95 -- say which in the legend
  group_colors: {"vehicle": "#d1d5db", "drug A": "#2563eb", "drug B": "#93c5fd"}
  legend_loc: "upper right"
  labels_ylabel: "Relative expression"
""",
    "correlation_scatter": HEAD + """# inputs/data.csv: one row per mouse -- diet (group), body_weight (x), fat_mass (y), and each diet's
# Pearson r and P (r, p_value) -- then the fit rows: a grid of body weights (fit_x) with the least-squares
# line (fit_y) and its 95% confidence band (ci_low, ci_high), all computed when the data were made. The
# renderer draws them; it fits nothing. With your data: keep these columns, or name yours below.
plot_type: correlation_scatter
plot_params:
  x_col: body_weight
  y_col: fat_mass
  group_col: diet
  group_order: ["chow", "high-fat"]
  group_colors: {"chow": "#6b7280", "high-fat": "#dc2626"}
  fit_x_col: fit_x
  fit_y_col: fit_y
  band_lower_col: ci_low        # 95% confidence band of the line -- say so in the legend
  band_upper_col: ci_high
  r_col: r
  p_col: p_value
  legend_loc: "lower right"
  labels_xlabel: "Body weight (g)"
  labels_ylabel: "Fat mass (g)"
""",
    "raincloud": HEAD + """# inputs/data.csv: one row per mouse -- treatment (category), latency_s (value), p_vs_vehicle (each
# dose's Dunnett P against vehicle, computed when the data were made -- the renderer draws it, it runs no
# test). With your data: keep these columns, or name yours below.
plot_type: raincloud
plot_params:
  category_col: treatment
  value_col: latency_s
  pvalue_col: p_vs_vehicle
  control_category: vehicle
  category_order: ["vehicle", "low dose", "high dose"]
  category_colors: {"vehicle": "#9ca3af", "low dose": "#60a5fa", "high dose": "#1d4ed8"}
  orientation: horizontal       # or vertical
  labels_xlabel: "Escape latency (s)"
""",
    "column_scatter": HEAD + """# inputs/data.csv: one row per mouse -- treatment (category), il6_pg_ml (value), p_vs_vehicle (Dunnett P
# against vehicle, computed when the data were made -- the renderer draws it, it runs no test). With your
# data: keep these columns, or name yours below.
plot_type: column_scatter
plot_params:
  category_col: treatment
  value_col: il6_pg_ml
  pvalue_col: p_vs_vehicle
  control_category: vehicle
  category_order: ["sham", "vehicle", "drug A", "drug B"]
  category_colors: {"sham": "#9ca3af", "vehicle": "#111827", "drug A": "#2563eb", "drug B": "#93c5fd"}
  point_layout: swarm           # or jitter, aligned
  summary: mean
  error: sd                     # sem, ci95, or iqr with summary: median -- say which in the legend
  labels_ylabel: "Plasma IL-6 (pg/mL)"
""",
    "roc_curve": HEAD + """# inputs/data.csv: one row per curve point -- marker (group), fpr, tpr -- and each marker's AUC with its
# 95% bootstrap interval (auc, auc_ci_low, auc_ci_high) and the Youden point (youden), all computed when
# the data were made. The renderer draws them; it ranks nothing. With your data: keep these columns, or
# name yours below.
plot_type: roc_curve
plot_params:
  group_col: marker
  group_colors: {"marker A": "#dc2626", "marker B": "#2563eb"}
  auc_col: auc
  auc_low_col: auc_ci_low       # 95% bootstrap interval -- say so in the legend
  auc_high_col: auc_ci_high
  operating_point_col: youden
  legend_loc: "lower right"
""",
    "bland_altman": HEAD + """# inputs/data.csv: one row per patient -- hba1c_lab and hba1c_device (the two methods) -- and the bias
# and 95% limits of agreement (bias, loa_low, loa_high: bias +/- 1.96 SD of the differences), computed
# when the data were made. The renderer draws them. With your data: keep these columns, or name yours below.
plot_type: bland_altman
plot_params:
  a_col: hba1c_lab
  b_col: hba1c_device
  bias_col: bias
  loa_low_col: loa_low
  loa_high_col: loa_high
  labels_xlabel: "Mean HbA1c (%)"
  labels_ylabel: "Laboratory \u2212 device (%)"
""",
    "correlation_matrix": HEAD + """# inputs/data.csv: one row per pair of variables -- var1, var2, r, p_value (Pearson, computed when the
# data were made from 80 patients). The renderer draws them; it correlates nothing. With your data: keep
# these columns, or name yours below.
plot_type: correlation_matrix
plot_params:
  p_col: p_value
  variable_order: ["age", "BMI", "SBP", "glucose", "HDL", "steps"]
  triangle: lower
  mark: square                  # or circle
""",
}


def main() -> None:
    rng = np.random.default_rng(SEED)
    makers = {"line_band": line_band, "threshold_scatter": threshold_scatter, "venn": venn, "violin": violin,
              "histogram": histogram, "dose_response": dose_response, "survival": survival,
              "stacked_bar": stacked_bar, "boxplot": boxplot, "multi_group_heatmap": multi_group_heatmap,
              "group_scatter": group_scatter, "effect_dots": effect_dots, "bar_scatter": bar_scatter,
              "heatmap": heatmap, "pca": pca,
              # field-pack plot types, after the core ones so their data do not change
              "volcano": volcano, "ma_plot": ma_plot, "go_bar": go_bar, "go_cluster_dot": go_cluster_dot,
              "count_summary": count_summary, "cross_condition_heatmap": cross_condition_heatmap,
              "cross_condition_dotplot": cross_condition_dotplot, "motif_dotplot": motif_dotplot,
              "peak_feature_enrichment": peak_feature_enrichment,
              # plot catalog (plans/PLAN_PLOT_CATALOG.md), appended in card order
              "paired_plot": paired_plot, "grouped_bar": grouped_bar,
              "correlation_scatter": correlation_scatter, "raincloud": raincloud,
              "column_scatter": column_scatter, "roc_curve": roc_curve,
              "bland_altman": bland_altman, "correlation_matrix": correlation_matrix}
    for name, make in makers.items():
        _write(name, make(rng), META[name])
    # The images get their own random stream, so adding a table example never changes their pixels.
    _write("image_panel", None, META["image_panel"], image_files(np.random.default_rng(SEED + 1)))
    print(f"wrote {len(META)} bundles in {HERE}")


if __name__ == "__main__":
    main()
