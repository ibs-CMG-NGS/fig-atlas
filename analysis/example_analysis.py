"""Example analysis script: generates a multi-panel Figure 1 source file.

Replace this with your real analysis. The only contract with the rest of the
framework is that this script writes:
  {OUTPUT_ROOT}/figures/figure1_example.{png,pdf,svg}

All path resolution goes through fig_atlas.get_config() so that RAW_ROOT
and OUTPUT_ROOT can be set via environment variables without editing this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents] if (p / ".fig-atlas").is_file())))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fig_atlas import get_config

CONFIG = get_config()
OUT = CONFIG.output_root / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def make_figure() -> None:
    rng = np.random.default_rng(2024)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("ggplot")

    time_points = np.arange(1, 9)
    control = np.array([4.2, 4.5, 4.8, 5.1, 5.3, 5.6, 5.9, 6.2])
    treated = control + np.array([0.2, 0.4, 0.6, 0.9, 1.0, 1.2, 1.4, 1.6])
    treated += 0.08 * rng.standard_normal(len(control))

    fig = plt.figure(figsize=(12, 4.4), dpi=CONFIG.dpi)
    gs = fig.add_gridspec(1, 3, wspace=0.28)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    ax_a.plot(time_points, control, color="#4C78A8", marker="o", linewidth=2.2, markersize=6, label="control")
    ax_a.plot(time_points, treated, color="#F58518", marker="s", linewidth=2.2, markersize=6, label="treated")
    ax_a.set_title("a", loc="left", fontweight="bold")
    ax_a.set_xlabel("time point")
    ax_a.set_ylabel("signal")
    ax_a.legend(frameon=False, loc="best")

    slope, intercept = np.polyfit(control, treated, 1)
    fit = slope * control + intercept
    ax_b.scatter(control, treated, s=60, color="#4C78A8", edgecolor="black", alpha=0.85)
    ax_b.plot(control, fit, color="#F58518", linewidth=1.8)
    ax_b.set_title("b", loc="left", fontweight="bold")
    ax_b.set_xlabel("control")
    ax_b.set_ylabel("treated")

    labels = ["WT", "KO1", "KO2"]
    values = [4.8, 6.2, 7.1]
    errs = [0.25, 0.30, 0.28]
    ax_c.bar(labels, values, yerr=errs, color=["#4C78A8", "#F58518", "#54A24B"], capsize=5, edgecolor="black")
    ax_c.set_title("c", loc="left", fontweight="bold")
    ax_c.set_ylabel("mean score")
    ax_c.set_ylim(0, 8.0)

    fig.suptitle("Figure 1. Treatment response across biological conditions", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))

    stem = OUT / "figure1_example"
    for fmt in CONFIG.formats:
        fig.savefig(stem.with_suffix(f".{fmt}"), bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {stem}.{{png,pdf,svg}}")


if __name__ == "__main__":
    make_figure()
