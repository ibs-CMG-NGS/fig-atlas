"""Figure 1 declaration with three sub-panels (a, b, c).

This spec describes what the figure is about. The actual layout and plotting
logic live in analysis/example_analysis.py.
"""

from fig_atlas import FigureSpec, get_config, publish

SPEC = FigureSpec(
    number=1,
    slug="example_subpanels",
    title="Example figure with panels a, b, and c",
    # Path to generated figure stem relative to output_root (without extension).
    # The publish step expects {output_root}/figures/figure1_example.{png,pdf,svg}.
    source_stem="figures/figure1_example",
    primary_code="analysis/example_analysis.py",
    panel_notes=[
        "Panel a: overview of condition-level differences.",
        "Panel b: per-sample comparison with one highlighted outlier.",
        "Panel c: summary statistics for the same dataset.",
    ],
    statistics_tables=[
        "supplementary_tables/Supplementary_Table_01_DE_results.csv",
    ],
    claim_boundary=(
        "These panels illustrate a paper-figure workflow using synthetic example data; "
        "replace them with real results before submission."
    ),
)


if __name__ == "__main__":
    config = get_config()
    publish(SPEC, config)
