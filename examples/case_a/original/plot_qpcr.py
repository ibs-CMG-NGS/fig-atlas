# plot_qpcr.py -- qPCR of four antioxidant genes after H2O2 (a student's script)
#
# Case A example of fig-atlas (docs/tutorials/case_a_port_script.md): the kind
# of script a figure starts from -- every size, colour and limit typed into the
# code. The data in qpcr_results.csv are synthetic, not measurements.
#
#   python plot_qpcr.py        -> qpcr_antioxidant.png
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("qpcr_results.csv")

genes = ["Hmox1", "Nqo1", "Gclm", "Txnrd1"]
conditions = ["vehicle", "H2O2"]
colors = {"vehicle": "#9CA3AF", "H2O2": "#D55E00"}

fig, ax = plt.subplots(figsize=(6, 4))
width = 0.4
x = np.arange(len(genes))
for i, cond in enumerate(conditions):
    sub = df[df["condition"] == cond]
    means = [sub.loc[sub["gene"] == g, "fold_change"].mean() for g in genes]
    sems = [sub.loc[sub["gene"] == g, "fold_change"].sem() for g in genes]
    pos = x + (i - 0.5) * width
    ax.bar(pos, means, width * 0.9, yerr=sems, capsize=3, color=colors[cond], label=cond)
    for j, g in enumerate(genes):
        vals = sub.loc[sub["gene"] == g, "fold_change"]
        ax.scatter(np.full(len(vals), pos[j]), vals, s=15, color="black", zorder=3)

ax.set_xticks(x)
ax.set_xticklabels(genes, fontsize=11)
ax.set_xlabel("Gene", fontsize=12)
ax.set_ylabel("Fold change (vs vehicle)", fontsize=12)
ax.set_title("Antioxidant genes after H2O2", fontsize=14)
ax.set_ylim(0, 6)
ax.legend(frameon=False, fontsize=10)
plt.tight_layout()
plt.savefig("qpcr_antioxidant.png", dpi=300)
