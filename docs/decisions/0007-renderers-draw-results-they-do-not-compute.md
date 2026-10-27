# 0007. Renderers draw results; they do not compute them

- Status: accepted
- Date: 2026-10-27

## Context

A figure prints numbers: a P value under a bracket, a Pearson r in a corner, an AUC in a legend, an EC50 beside a fitted curve, a log-rank P in a survival panel. Somewhere those numbers are computed. In fig-atlas they were creeping into the renderers: `dose_response` fits a 4PL curve with `scipy.optimize.curve_fit`, `group_scatter` runs `scipy.stats.pearsonr` and prints r and P, and the expansion plan for new plot types proposed a statistics layer with paired tests, post-hoc comparisons, ROC/AUC and a curve-fitting framework (`cmg-figures/docs/PLAN_PLOT_CATALOG.md`, v2).

That contradicts what the package says about itself (`docs/guide/01-why.md`): *"It does not choose analysis methods or statistical criteria."* It also puts a second implementation of the test next to the study's real one, where it cannot see the design (pairing, blocking, covariates, missing values) that the choice of test depends on.

## Decision

**The numbers a figure prints arrive as data.** The analysis script (scipy, R, statsmodels -- whatever the study uses) runs the test, the fit or the model, writes the result as a column the renderer can name (`r_col`, `pvalue_col`, `fpr`/`tpr`, fit parameters, curve coordinates), and registers the test table with `fig_atlas.stats.record(table, name=...)`. The build writes that table beside the figure and `verify` checks that it is there.

**A renderer may compute the geometry of its own shape** -- the estimator that *is* the curve: the Kaplan-Meier step function, the mean and confidence band of a line, the order a dendrogram puts rows in, the density a violin draws, the least-squares line drawn over points. That is drawing, not inference, and the renderer must be able to draw it from the data it is given.

**What stays in `fig_atlas.stats` is the display layer**: `stars()` (thresholds from the config), `adjust()` (an adjusted-p column for display), `describe_stars()` (the legend sentence), `record()`/`write()` (the test table beside the figure). The test functions it already carries (`two_group`, `compare_to_control`, `anova`) stay for compatibility and are not extended; new work computes in the analysis script.

## Consequences

- The contract style is "the value arrives as a column", already used by `bar_scatter` (`pvalue_col`) and `cis_linkage` (`pearson_r`). New plot types follow it.
- `tests/test_renderer_purity.py` holds the audit: a renderer may import `scipy.cluster`/`scipy.spatial` (ordering) and, in `line_band`, `scipy.stats` (the CI band's t quantile). Two exceptions are transitional and name the card that removes them: `dose_response`'s 4PL fit (E-04) and `group_scatter`'s Pearson fallback (E-04). An allowlist entry that no longer matches the code fails the test, so the list cannot rot.
- The recipes for the six statistics a catalog panel needs (paired test, post-hoc, correlation/regression, ROC/AUC, curve fit, contingency) are documentation and a template (`cmg-figures` plan card I-04), not package code.
- Reproducibility does not weaken: the figure still carries the numbers, and now it also carries the table that says which test produced them and the column the number was drawn from. What it no longer carries is a second, hidden implementation of the test. Reference values in another language (R) are no longer needed to validate statistics the package does not compute.
- If a study has no analysis script (a quick look at a table), the honest path is short: compute the value in the script that builds the figure, write the column, record the table. `fa` does not run statistics for you.
