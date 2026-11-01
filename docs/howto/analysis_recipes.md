# How-to: compute the numbers a figure prints

A P value under a bracket, a Pearson r in a corner, an AUC in a legend, an EC50 beside a curve: these are **results**, and fig-atlas does not compute them. The analysis script does — scipy, R, statsmodels, whatever the study already uses — and the figure draws what the script hands it ([decision 0007](../decisions/0007-renderers-draw-results-they-do-not-compute.md)).

The reason is not purity. A test depends on the design: which pairs belong together, which subject is the control, which covariates exist, which values are missing. That knowledge lives in the analysis script, not in a renderer that receives a tidy table. So the renderer draws, and the script decides.

## 1. The five steps every recipe shares

| Step | What you write | Where it ends up |
|---|---|---|
| Compute | the test, fit or model, in the analysis script | `analysis/<domain>/<category>/<project>_analysis.py` |
| Write a column | `df["p_value"] = ...` | the table the panel draws |
| Register the table | `stats.record(table, name="paired_t", title="...")` | `outputs/publish/<project>/figure_NN_statistics/paired_t.csv` |
| Name the column | `pvalue_col: p_value` in the config | the panel's `plots.<name>` block |
| Describe it in the legend | `claims.record("star_rule", ...)` | `{star_rule}` in the FigureSpec |

The config block names the column; the renderer only reads it:

```yaml
plots:
  before_after:
    pvalue_col: "p_value"                                        # column the analysis script wrote
    sig_thresholds: [[0.001, "***"], [0.01, "**"], [0.05, "*"]]  # P -> symbol, ascending thresholds
```

The legend phrase is built from the same thresholds, so it cannot drift from the marks:

```python
from fig_atlas import claims

thresholds = cfg["plots"]["before_after"]["sig_thresholds"]
rule = "paired t-test, two-sided (" + ", ".join(f"{sym}P < {thr:g}" for thr, sym in thresholds) + ")"
claims.record("star_rule", rule, source=f"{__file__} (paired t-test on before/after)")
```

## 2. Before and after: a paired test

One row per subject, two columns (before, after). The pairing is the design, so it is here, not in the renderer:

```python
import pandas as pd
from scipy.stats import ttest_rel, wilcoxon
from fig_atlas import stats

wide = load_pairs()                                     # subject, before, after
p = ttest_rel(wide["after"], wide["before"]).pvalue      # Student's paired t-test
# p = wilcoxon(wide["after"], wide["before"]).pvalue     # non-normal differences: Wilcoxon signed-rank

long = wide.melt(id_vars="subject", var_name="condition", value_name="value")
long["p_value"] = p                                     # the renderer draws this column

stats.record(pd.DataFrame({"test": ["paired t"], "n": [len(wide)], "p": [p]}),
             name="paired_t", title="Before vs after (two-sided paired t-test)")
```

In R the same step is one line, and the table is written for the script to read:

```r
p <- t.test(d$after, d$before, paired = TRUE)$p.value
write.csv(data.frame(test = "paired t", n = nrow(d), p = p), "paired_t.csv", row.names = FALSE)
```

## 3. Three or more groups: post-hoc comparisons

The omnibus test first, then the comparisons the panel actually brackets. Only the comparisons you draw need a row:

```python
import pandas as pd
from scipy.stats import tukey_hsd
from fig_atlas import stats

groups = [df.loc[df["group"] == g, "value"].to_numpy() for g in order]
res = tukey_hsd(*groups)                                # family-wise correction is inside Tukey
rows = [{"group_a": order[i], "group_b": order[j], "p_adj": float(res.pvalue[i, j])}
        for i in range(len(order)) for j in range(i + 1, len(order))]
comparisons = pd.DataFrame(rows)
stats.record(comparisons, name="posthoc", title="Tukey HSD, all pairwise comparisons")
```

Against one control, use `scipy.stats.dunnett` (or `statsmodels.stats.multicomp`) instead, and write the resulting `p_adj` beside the comparison the bracket spans. R's `emmeans::contrast(..., adjust = "tukey")` gives the same table.

## 4. Two variables: correlation and regression

The r and P are printed; the line is drawn. Both come from the same fit here, so the number and the line agree:

```python
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from fig_atlas import stats

df = load_xy()                                           # one row per item: x, y, group
r, p = pearsonr(df["x"], df["y"])                        # or spearmanr for ranks
df["r"], df["p_value"] = r, p                            # read by r_col / p_col

stats.record(pd.DataFrame({"r": [r], "p": [p], "n": [len(df)]}),
             name="correlation", title="Pearson correlation")
```

The config names the two columns (`group_scatter` draws them in a corner):

```yaml
plots:
  signal_vs_quality:
    r_col: "r"            # column with the correlation (one value per panel)
    p_col: "p_value"      # and its P
```

A confidence band or a prediction band is more of the same: compute the grid and the band edges in the script, record the fit table, and a renderer that draws a band takes the coordinates. Do not let the renderer re-fit and decide which number to print.

## 5. A classifier: ROC and AUC

The curve is a result of ranking, so it is computed, not smoothed. No extra dependency is needed for the curve itself:

```python
import numpy as np
import pandas as pd
from fig_atlas import stats

def roc(labels, scores):
    order = np.argsort(-np.asarray(scores))
    y = np.asarray(labels, dtype=float)[order]
    tpr = np.cumsum(y) / y.sum()
    fpr = np.cumsum(1.0 - y) / (1.0 - y).sum()
    return np.r_[0.0, fpr], np.r_[0.0, tpr], float(np.trapezoid(np.r_[0.0, tpr], np.r_[0.0, fpr]))

fpr, tpr, auc = roc(labels, scores)                      # numpy 2: trapezoid; np.trapz before it
curve = pd.DataFrame({"fpr": fpr, "tpr": tpr, "auc": auc})
stats.record(curve, name="roc", title="ROC curve, cases versus controls")
```

A confidence interval for the AUC is a bootstrap or DeLong job — 2000 resamples in the script, or `pROC::ci.auc` in R — and it travels in the same table as two more columns (`ci_low`, `ci_high`). A renderer that prints "AUC 0.83 (0.76-0.89)" reads all three from those columns.

## 6. A dose series: a curve fit

The model is a scientific choice (4PL, 3PL, Michaelis-Menten, a line), so it is made in the script, and its parameters are reported with the curve:

```python
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from fig_atlas import stats

def four_pl(x, bottom, top, log_ec50, hill):             # x = log10(dose)
    return bottom + (top - bottom) / (1.0 + 10.0 ** ((log_ec50 - x) * hill))

popt, cov = curve_fit(four_pl, np.log10(dose), response, p0=[response.min(), response.max(), np.median(np.log10(dose)), 1.0],
                      bounds=([-np.inf, -np.inf, -np.inf, 0.0], [np.inf, np.inf, np.inf, np.inf]))
curve = pd.DataFrame({"dose_log10": grid, "response_fit": four_pl(grid, *popt)})
params = pd.DataFrame({"parameter": ["bottom", "top", "log_ec50", "hill"], "estimate": popt})
stats.record(params, name="dose_response_fit", title="4PL fit (log10 EC50)")
```

The fitted table goes to the figure, and the panel prints the parameters it is given — including the EC50 with the interval the script computed from `cov`.

## 7. Counts: a contingency table and a proportion's interval

Proportions need a test and an interval; both are computed on the counts, and the figure draws the bars with the interval as a whisker:

```python
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from fig_atlas import stats

table = pd.crosstab(df["group"], df["outcome"])          # rows: groups, columns: outcomes
chi2, p, dof, expected = chi2_contingency(table)
# p = fisher_exact(table)[1] for a 2x2 table whose expected counts are small
summary = df.groupby(["group", "outcome"]).size().rename("count").reset_index()
summary["p_value"] = p
stats.record(pd.DataFrame({"chi2": [chi2], "dof": [dof], "p": [p]}),
             name="contingency", title="Chi-square test of independence")
```

A proportion's 95% interval (Wilson, which behaves at small n and near 0 or 1) is a few lines, and it belongs in the table the renderer draws from:

```python
def wilson(k, n, z=1.959964):
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / d
    half = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / d
    return centre - half, centre + half

low, high = wilson(12, 40)                                # ci_low, ci_high columns
```

## 8. What the package still does

Computing is the script's job; the package keeps the display and the record:

- **The display layer** in `fig_atlas.stats`: `stars()` (a P value to a symbol, thresholds from the config), `adjust()` (an adjusted-P column for display), `describe()` (the legend sentence for the tests the package itself once ran), `record()`/`write()` (the test table beside the figure).
- **The build** writes every registered table to `figure_NN_statistics/`, and `verify` fails when a figure that draws marks has no table beside it. The table is the provenance: which test, which n, which P.
- **The legacy** path: a few older renderers still offer a `stat_test` setting and run the comparison themselves through `fig_atlas.stats` (the omics `tf_expression_bars` is the last one). They keep working, and they are not extended — new figures pass the P value in a column, as above.

If a study has no analysis script yet, the honest path is short: compute the value in the script that builds the figure, write the column, register the table. A number typed into a config or a title is what `fa claims --check` is there to catch.
