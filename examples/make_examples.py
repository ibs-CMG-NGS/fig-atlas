"""Regenerate the example bundles in examples/ (synthetic data, fixed seed).

    python examples/make_examples.py

The data are simulated -- not measurements -- so they can be committed and
used by the tutorial (docs/tutorials/first_figure.md) and its CI test with no
download. Re-running writes byte-identical files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEED = 20261008


def _write(bundle: Path, df: pd.DataFrame, metadata: str) -> None:
    (bundle / "inputs").mkdir(parents=True, exist_ok=True)
    (bundle / "metadata").mkdir(parents=True, exist_ok=True)
    df.to_csv(bundle / "inputs" / "data.csv", index=False, lineterminator="\n")
    (bundle / "metadata" / "metadata.yaml").write_text(metadata, encoding="utf-8", newline="\n")


def dose_response(rng: np.random.Generator) -> pd.DataFrame:
    """Cell viability (%) of three compounds over seven doses, four replicates:
    a four-parameter logistic curve per compound plus noise."""
    doses = np.round(np.logspace(-2, 1, 7), 4)                      # 0.01 .. 10 uM
    curves = {"compound A": (0.3, 1.2), "compound B": (2.0, 1.0), "vehicle": (1e6, 1.0)}   # (IC50, Hill)
    rows = []
    for name, (ic50, hill) in curves.items():
        for d in doses:
            mean = 100 / (1 + (d / ic50) ** hill)
            for rep in range(1, 5):
                rows.append({"compound": name, "dose_uM": d, "replicate": rep,
                             "viability": round(float(mean + rng.normal(0, 4)), 2)})
    return pd.DataFrame(rows)


def screen_hits(rng: np.random.Generator) -> pd.DataFrame:
    """A screen of 400 features: effect sizes (most near zero, 30 true hits),
    two-sided z-test P values and Benjamini-Hochberg adjusted P values."""
    from scipy import stats
    n, hits = 400, 30
    effect = rng.normal(0, 0.25, n)
    idx = rng.choice(n, hits, replace=False)
    effect[idx] += rng.choice([-1, 1], hits) * rng.uniform(0.6, 1.8, hits)
    se = rng.uniform(0.12, 0.2, n)
    p = 2 * stats.norm.sf(np.abs(effect / se))
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1].clip(max=1)
    p_adj = np.empty(n)
    p_adj[order] = adj
    return pd.DataFrame({"feature": [f"F{i:03d}" for i in range(1, n + 1)], "effect": effect.round(4),
                         "p_value": [float(f"{x:.4g}") for x in p], "p_adj": [float(f"{x:.4g}") for x in p_adj]})


DOSE_META = """\
# Synthetic example (examples/make_examples.py): viability over dose, 3 compounds x 7 doses x 4 replicates.
plot_type: line_band
plot_params:
  x_col: dose_uM
  y_col: viability
  group_col: compound
  x_log: true
  error: sem
  show_points: true
  labels_title: "Viability after 48 h"
  labels_xlabel: "Dose (uM)"
  labels_ylabel: "Viability (% of control)"
"""

SCREEN_META = """\
# Synthetic example (examples/make_examples.py): 400 screened features, effect size and BH-adjusted P.
plot_type: threshold_scatter
plot_params:
  x_col: effect
  y_col: p_adj
  effect_col: effect
  sig_col: p_adj
  y_transform: neg_log10
  effect_threshold: 0.5
  sig_threshold: 0.05
  label_mode: top_n
  label_cols: ["feature"]
  label_top_n: 6
  labels_title: "Screen hits"
  labels_xlabel: "Effect size"
  labels_ylabel: "-log10 adjusted P"
"""


def main() -> None:
    rng = np.random.default_rng(SEED)
    _write(HERE / "dose_response", dose_response(rng), DOSE_META)
    _write(HERE / "screen_hits", screen_hits(rng), SCREEN_META)
    print("wrote examples/dose_response and examples/screen_hits")


if __name__ == "__main__":
    main()
