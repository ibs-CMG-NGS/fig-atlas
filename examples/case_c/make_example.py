"""Case C example of fig-atlas: data and a hand-drawn sketch of the figure wanted.

    python examples/case_c/make_example.py

writes request/data.csv (synthetic: per gene, a log2 fold change with its 95 %
confidence interval and an adjusted P) and request/sketch.png, a rough drawing
of the figure a researcher has in mind, with notes -- what a Case C request
starts from (docs/tutorials/case_c_from_sketch.md). Drawn in matplotlib's xkcd
style so it reads as a sketch: the positions are approximate, not data.
Replace both with a real request when one is at hand.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 7
GENES = ["Hmox1", "Nqo1", "Gclm", "Gclc", "Txnrd1", "Srxn1", "Slc7a11", "Gsta1",
         "Prdx1", "Sod1", "Cat", "Gpx1"]
TRUE = [2.3, 1.6, 1.1, 0.9, 0.8, 1.9, 1.4, 0.2, 0.1, -0.15, -0.9, -0.6]


def make_data() -> list[dict]:
    rng = np.random.default_rng(SEED)
    rows = []
    for g, mu in zip(GENES, TRUE):
        est = mu + rng.normal(0, 0.08)
        se = rng.uniform(0.12, 0.28)
        z = abs(est) / se
        p = float(np.exp(-0.717 * z - 0.416 * z * z))          # two-sided normal P (approximation)
        rows.append({"gene": g, "log2fc": round(est, 3), "ci_low": round(est - 1.96 * se, 3),
                     "ci_high": round(est + 1.96 * se, 3), "padj": float(f"{min(1.0, p * len(GENES)):.3g}")})
    return rows


def make_sketch(rows: list[dict]) -> None:
    import logging

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # xkcd asks for the Humor Sans font first; without it matplotlib falls back
    # (the sketch still looks hand-drawn) but logs every text. Keep it quiet.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    rows = sorted(rows, key=lambda r: r["log2fc"])           # the sketch shows the order wanted
    rng = np.random.default_rng(SEED + 1)
    with plt.xkcd(scale=0.8, length=60, randomness=2):
        fig, ax = plt.subplots(figsize=(6.0, 4.6))
        for i, r in enumerate(rows):
            x = r["log2fc"] + rng.normal(0, 0.06)               # roughly where it goes
            half = (r["ci_high"] - r["ci_low"]) / 2
            sig = r["padj"] < 0.05
            col = "#d62728" if sig and x > 0 else "#1f77b4" if sig else "#999999"
            ax.plot([x - half, x + half], [i, i], color=col, lw=1.5)
            ax.plot(x, i, "o", color=col, ms=7)
        ax.axvline(0, color="black", ls="--", lw=1)
        ax.set_yticks(range(len(rows)), [r["gene"] for r in rows])
        ax.set_xlabel("log2 fold change (95% CI)")
        ax.set_title("H2O2 response of antioxidant genes")
        ax.annotate("biggest up\non top", xy=(2.3, len(rows) - 1), xytext=(0.6, len(rows) - 2.2),
                    arrowprops=dict(arrowstyle="->"), fontsize=9)
        ax.text(1.0, 2.0, "red = up, blue = down\n(only if padj < 0.05)\ngrey = not significant", fontsize=9)
        ax.text(-1.7, 9.6, "same style as\nour other panels!", fontsize=9, color="#555555")
        ax.set_xlim(-1.8, 3.0)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(HERE / "request" / "sketch.png", dpi=110, metadata={"Software": None})
        plt.close(fig)


def main() -> None:
    rows = make_data()
    (HERE / "request").mkdir(exist_ok=True)
    with (HERE / "request" / "data.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    make_sketch(rows)
    print(f"wrote {HERE / 'request' / 'data.csv'} and {HERE / 'request' / 'sketch.png'}")


if __name__ == "__main__":
    main()
