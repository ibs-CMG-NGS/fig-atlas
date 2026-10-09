"""Shared data-prep helpers for ATAC-seq DA (differential accessibility)
pairwise-comparison projects.

RNA-seq DE projects get their plot-ready column contracts for free from
cmg-seqviewer's bundle-export feature (renamed/derived columns like
cluster_id, _cluster_size, _fe_median already baked into inputs/data.csv).
There is no equivalent export tool for this R/ATAC pipeline -- its raw
output (final_da_results.csv, go_termcluster_*.csv, kegg_enrichment_*.csv)
keeps R/DESeq2/clusterProfiler's own column names and, for the GO cluster
tables, one row per TERM rather than one row per CLUSTER REPRESENTATIVE.

These functions do that adaptation in versioned Python instead of by hand
per project, so a sibling DA project (Acute_3D, Chronic_24H, Chronic_48H
vs Control, ...) can reuse them directly. raw_data/ itself stays an
unmodified copy of the source CSVs -- this module is where the transform
logic lives, not the raw_data files.
"""

from __future__ import annotations

import re

import pandas as pd


def prep_da_volcano_df(da_results: pd.DataFrame, peak_annotation: pd.DataFrame) -> pd.DataFrame:
    """Adapt final_da_results.csv + peak_annotation_total.csv into
    render_volcano's column contract (log2FC, padj, symbol/gene_id).

    peak_annotation only carries rows for significant peaks (that's what
    the upstream R script itself annotates), so the merge leaves `symbol`
    NaN for non-significant peaks -- harmless, since render_volcano only
    ever labels a top-N subset of the significant ones anyway. A peak
    without an embedded gene symbol in its annotation text (e.g. a bare
    "Promoter (8-9kb)" or "Distal Intergenic" annotation, which names no
    gene) falls back to its own peak_id as the label, matching what the
    reference figure shows for those peaks (raw "Interval_NNNNN" labels).
    """
    df = da_results.rename(columns={"log2FoldChange": "log2FC", "peak_id": "gene_id"})

    def _extract_symbol(annotation):
        if pd.isna(annotation):
            return None
        # ChIPseeker-style annotation text embeds the gene symbol (or a
        # bare Entrez ID when no symbol is known) between the transcript
        # ID and the next comma, e.g.
        # "Intron (ENSMUST00000041463.7/Pacrg, intron 2 of 4)" -> "Pacrg".
        # Promoter/Distal Intergenic/UTR annotations carry no such token.
        m = re.search(r"/([^/,]+),", str(annotation))
        return m.group(1) if m else None

    ann = peak_annotation.rename(columns={"peak_id": "gene_id"}).copy()
    ann["symbol"] = ann["annotation"].apply(_extract_symbol)
    df = df.merge(ann[["gene_id", "symbol"]], on="gene_id", how="left")
    df["symbol"] = df["symbol"].fillna(df["gene_id"])
    return df


def prep_da_go_cluster_df(raw_termcluster: pd.DataFrame) -> pd.DataFrame:
    """Adapt a raw go_termcluster_{up,down}_{BP,CC,MF}.csv (one row per
    term, a `cluster` column grouping them) into render_go_cluster_dot's
    column contract: one row per cluster REPRESENTATIVE (lowest p.adjust
    in that cluster), with _cluster_size (member count) and _fe_median
    (cluster's median Fold Enrichment) added -- the same reduction
    cmg-seqviewer's bundle-export already does for RNA-seq GO clusters.
    """
    if raw_termcluster.empty:
        return raw_termcluster
    df = raw_termcluster.rename(columns={
        "ID": "term_id",
        "Description": "description",
        "GeneRatio": "gene_ratio",
        "BgRatio": "bg_ratio",
        "FoldEnrichment": "fold_enrichment",
        "p.adjust": "fdr",
        "Count": "gene_count",
        "geneID": "gene_symbols",
    })

    if "fold_enrichment" not in df.columns and "gene_ratio" in df.columns and "bg_ratio" in df.columns:
        def _parse_ratio(r):
            if pd.isna(r) or "/" not in str(r):
                return 1.0
            parts = str(r).split("/")
            try:
                return float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                return 1.0
        gr = df["gene_ratio"].apply(_parse_ratio)
        br = df["bg_ratio"].apply(_parse_ratio)
        df["fold_enrichment"] = gr / br.replace(0.0, 1.0)
    elif "fold_enrichment" not in df.columns:
        df["fold_enrichment"] = 1.0

    if "cluster" not in df.columns:
        df["cluster"] = range(1, len(df) + 1)

    reps = []
    for cluster, group in df.groupby("cluster"):
        rep = group.loc[group["fdr"].idxmin()].copy()
        rep["_cluster_size"] = len(group)
        rep["_fe_median"] = group["fold_enrichment"].median()
        rep["cluster_id"] = f"{int(cluster):03d}"
        reps.append(rep)
    return pd.DataFrame(reps).sort_values("fdr").reset_index(drop=True)


def prep_da_kegg_df(raw_kegg: pd.DataFrame) -> pd.DataFrame:
    """Adapt a raw kegg_enrichment_{up,down}.csv into render_go_bar's
    column contract (description, fdr, gene_ratio, bg_ratio, gene_count,
    gene_symbols). KEGG terms aren't clustered upstream, so no
    representative-row reduction is needed here, unlike the GO tables.
    """
    return raw_kegg.rename(columns={
        "ID": "term_id",
        "Description": "description",
        "GeneRatio": "gene_ratio",
        "BgRatio": "bg_ratio",
        "p.adjust": "fdr",
        "Count": "gene_count",
        "geneID": "gene_symbols",
    })
