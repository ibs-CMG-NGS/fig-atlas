# Example data bundles

Small **synthetic** data bundles (simulated, not measurements) for the tutorial
[docs/tutorials/first_figure.md](../docs/tutorials/first_figure.md) and its CI test. They
are committed so the tutorial needs no download; `python examples/make_examples.py`
regenerates them byte for byte (fixed seed).

| Bundle | Data | `plot_type` (contract) |
|---|---|---|
| `dose_response/` | Viability (% of control) of 3 compounds x 7 doses x 4 replicates, four-parameter logistic curves plus noise | `line_band` (`core.line_band`) |
| `screen_hits/` | 400 features: effect size, two-sided z-test P, Benjamini-Hochberg adjusted P; 30 simulated true hits | `threshold_scatter` (`core.threshold_scatter`) |

Each bundle follows the table bundle contract
([docs/contracts/table_bundle_contract.md](../docs/contracts/table_bundle_contract.md)):
`inputs/data.csv` plus `metadata/metadata.yaml` with `plot_type` and `plot_params`
(which columns are x, y, groups, ...). Real data go under `raw_data/` (git-ignored,
read-only); these examples are the only data in the repository.
