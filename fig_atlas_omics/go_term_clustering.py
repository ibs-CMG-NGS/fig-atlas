"""Gene-overlap (Jaccard) hierarchical clustering of GO enrichment term tables.

Used by a supplementary-table script and a figure of the same study, so both
always agree on cluster membership. Gene overlap (not rrvgo semantic similarity)
is used because it needs no ontology database and its clusters can be checked
from the gene lists alone.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

JACCARD_DIST_THRESHOLD = 0.7  # merge terms sharing >=30% of their genes


def _jaccard_distance_matrix(gene_sets: list[set[str]]) -> np.ndarray:
    n = len(gene_sets)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            a, b = gene_sets[i], gene_sets[j]
            union = len(a | b)
            jacc = (len(a & b) / union) if union else 0.0
            dist[i, j] = dist[j, i] = 1.0 - jacc
    return dist


def _overlap_distance_matrix(gene_sets: list[set[str]]) -> np.ndarray:
    """1 - overlap coefficient (|A & B| / min(|A|, |B|)): a term nested in a larger
    one is at distance 0, so parent / child terms merge (EnrichmentMap's measure)."""
    n = len(gene_sets)
    dist = np.zeros((n, n))
    for i in range(n):
        a = gene_sets[i]
        for j in range(i + 1, n):
            b = gene_sets[j]
            m = min(len(a), len(b))
            ov = (len(a & b) / m) if m else 0.0
            dist[i, j] = dist[j, i] = 1.0 - ov
    return dist


def cluster_go_terms(
    df: pd.DataFrame,
    gene_col: str = "geneID",
    padj_col: str = "p.adjust",
    dist_threshold: float = JACCARD_DIST_THRESHOLD,
    metric: str = "jaccard",
) -> pd.DataFrame:
    """Add Cluster_Num / Cluster_Size / Cluster_Representative_Term columns.

    ``df`` must already be scoped to a single concordance class's significant
    terms (classes are mutually exclusive gene populations, so cross-class
    Jaccard overlap is structurally ~0 -- see module docstring). Cluster_Num is
    renumbered 1..k by ascending best (min) ``padj_col`` within the class, so
    cluster 1 is always that class's most significant functional module.
    """
    df = df.copy()
    n = len(df)
    if n == 0:
        df["_raw_cluster"] = pd.Series(dtype=int)
    elif n == 1:
        df["_raw_cluster"] = [1]
    else:
        gene_sets = [set(str(s).split("/")) for s in df[gene_col]]
        dist = (_overlap_distance_matrix(gene_sets) if metric == "overlap"
                else _jaccard_distance_matrix(gene_sets))
        condensed = squareform(dist, checks=False)
        z = linkage(condensed, method="average")
        df["_raw_cluster"] = fcluster(z, t=dist_threshold, criterion="distance")

    cluster_rank = (
        df.groupby("_raw_cluster")[padj_col].min().sort_values().reset_index()
        .assign(cluster_num=lambda x: range(1, len(x) + 1))
        .set_index("_raw_cluster")["cluster_num"]
    )
    df["Cluster_Num"] = df["_raw_cluster"].map(cluster_rank)
    df["Cluster_Size"] = df.groupby("_raw_cluster")["_raw_cluster"].transform("size")

    rep = df.loc[df.groupby("_raw_cluster")[padj_col].idxmin(), ["_raw_cluster", "Cluster_Num"]]
    term_col = "Description" if "Description" in df.columns else None
    if term_col:
        rep_terms = df.loc[df.groupby("_raw_cluster")[padj_col].idxmin(), ["_raw_cluster", term_col]]
        rep_map = dict(zip(rep_terms["_raw_cluster"], rep_terms[term_col]))
        df["Cluster_Representative_Term"] = df["_raw_cluster"].map(rep_map)

    return df.drop(columns=["_raw_cluster"])


def term_gene_sets(bundle_files, term_ids) -> dict[str, set[str]]:
    """Member genes of each GO term, pooled over per-condition enrichment results.

    ``bundle_files``: clusterProfiler-style tables (columns ``term_id`` /
    ``gene_symbols`` or ``ID`` / ``geneID``), e.g. every species x condition x
    direction GO:BP result of one assay. Symbols are upper-cased so human and
    mouse members pool into one set per term.
    """
    from pathlib import Path
    wanted = set(term_ids)
    genes: dict[str, set[str]] = {}
    for f in bundle_files:
        d = pd.read_csv(Path(f))
        id_col = "term_id" if "term_id" in d.columns else "ID"
        gene_col = "gene_symbols" if "gene_symbols" in d.columns else "geneID"
        for t, g in zip(d[id_col], d[gene_col]):
            if t in wanted:
                genes.setdefault(t, set()).update(s.strip().upper() for s in str(g).split("/") if s.strip())
    return genes


def cluster_cross_condition_terms(go_long: pd.DataFrame, gene_sets: dict[str, set[str]],
                                  id_col: str = "GO ID", term_col: str = "GO Term",
                                  padj_col: str = "Adjusted P-value",
                                  dist_threshold: float = JACCARD_DIST_THRESHOLD,
                                  metric: str = "jaccard") -> pd.DataFrame:
    """Gene-overlap clusters of the terms in a long cross-condition GO table.

    ``go_long`` has one row per (condition column, term) significant result. Each
    term is placed once, with its best (smallest) adjusted P across conditions and
    its pooled member genes; terms are clustered with ``cluster_go_terms``
    (``metric`` "jaccard" as in Supplementary Table S3, or "overlap" -- the overlap
    coefficient, which also merges a term nested inside a larger one). Returns one row per term: id, term, best padj,
    n_genes, Cluster_Num (1 = most significant cluster), Cluster_Size,
    Cluster_Representative_Term. Terms without member genes are dropped (reported
    by the caller).
    """
    best = (go_long.groupby([id_col, term_col])[padj_col].min().reset_index()
            .rename(columns={padj_col: "best_padj", term_col: "Description"}))
    best = best[best[id_col].isin(gene_sets)].copy()
    best["geneID"] = best[id_col].map(lambda t: "/".join(sorted(gene_sets[t])))
    best["n_genes"] = best[id_col].map(lambda t: len(gene_sets[t]))
    out = cluster_go_terms(best, gene_col="geneID", padj_col="best_padj", dist_threshold=dist_threshold,
                           metric=metric)
    return out.rename(columns={"Description": term_col}).sort_values(["Cluster_Num", "best_padj"]).reset_index(drop=True)


def long_table_from_ora_bundles(entries, project_root) -> tuple[pd.DataFrame, dict[str, set[str]]]:
    """Cross-condition GO table built directly from per-condition ORA results.

    ``entries``: list of {species, condition, files: [glob, ...]} (repo-relative),
    each file one clusterProfiler-style result (``term_id``/``ID``, ``description``/
    ``Description``, ``fdr``/``p.adjust``, ``gene_symbols``/``geneID``) whose name
    says the direction (``go_bp_up_...`` / ``go_bp_down_...``). Every significant
    term is kept -- no pre-selection. Within one species x condition a term found in
    both directions keeps the more significant one.

    Returns (long table with Condition = "<Species>_<condition>", Direction, GO ID,
    GO Term, Adjusted P-value, Signed -log10(FDR); gene sets {GO ID: member genes
    pooled over all results, upper-cased}).
    """
    from pathlib import Path
    root = Path(project_root)
    rows, genes = [], {}
    for e in entries:
        cond = f"{e['species']}_{e['condition']}"
        for pat in e.get("files", []):
            for f in sorted(root.glob(pat)):
                name = f.parent.parent.name.lower()
                direction = "UP" if "_up_" in name else ("DOWN" if "_down_" in name else None)
                d = pd.read_csv(f)
                if d.empty:
                    continue
                id_col = "term_id" if "term_id" in d.columns else "ID"
                term_col = "description" if "description" in d.columns else "Description"
                p_col = "fdr" if "fdr" in d.columns else "p.adjust"
                g_col = "gene_symbols" if "gene_symbols" in d.columns else "geneID"
                if direction is None and "direction" in d.columns:
                    direction = str(d["direction"].iloc[0]).upper()
                sign = -1.0 if direction == "DOWN" else 1.0
                for t, desc, p, g in zip(d[id_col], d[term_col], d[p_col], d[g_col]):
                    p = float(p)
                    rows.append({"Condition": cond, "Direction": direction, "GO ID": t, "GO Term": desc,
                                 "Adjusted P-value": p,
                                 "Signed -log10(FDR)": sign * float(-np.log10(max(p, 1e-300)))})
                    genes.setdefault(t, set()).update(s.strip().upper() for s in str(g).split("/") if s.strip())
    long = pd.DataFrame(rows)
    if len(long):
        long = (long.sort_values("Adjusted P-value")
                .drop_duplicates(subset=["Condition", "GO ID"], keep="first").reset_index(drop=True))
    return long, genes


def select_clusters_by_group(clusters: pd.DataFrame, go_long: pd.DataFrame, per_group: int, total: int,
                             groups=("Human", "Mouse"), id_col: str = "GO ID",
                             padj_col: str = "Adjusted P-value") -> list[tuple[int, str]]:
    """Pick clusters so every group (species) is represented.

    For each group, clusters are ranked by their best adjusted P within that
    group's conditions (Condition = "<group>_<condition>"); the top ``per_group``
    of each group are taken in group order (a cluster already taken counts for
    the first group that picked it, and the next one down is taken instead),
    then the list is filled to ``total`` from the overall ranking
    (Cluster_Num). Returns [(Cluster_Num, picked_by)], in that order.
    """
    term_cluster = dict(zip(clusters[id_col], clusters["Cluster_Num"]))
    gl = go_long.assign(_group=go_long["Condition"].str.split("_").str[0],
                        _cluster=go_long[id_col].map(term_cluster)).dropna(subset=["_cluster"])
    chosen: list[tuple[int, str]] = []
    taken: set[int] = set()
    for g in groups:
        ranked = (gl[gl["_group"] == g].groupby("_cluster")[padj_col].min().sort_values().index.astype(int))
        n = 0
        for k in ranked:
            if n >= per_group:
                break
            if k in taken:
                continue
            chosen.append((int(k), g))
            taken.add(int(k))
            n += 1
    for k in sorted(clusters["Cluster_Num"].unique()):
        if len(chosen) >= total:
            break
        if int(k) not in taken:
            chosen.append((int(k), "overall"))
            taken.add(int(k))
    return chosen[:total]
