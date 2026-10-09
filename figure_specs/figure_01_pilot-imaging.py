"""Figure 1 of the imaging pilot (roadmap 6a.4): FKHR-GFP translocation, BBBC013v1."""

from fig_atlas import FigureSpec, get_config, publish

SPEC = FigureSpec(
    number=1,
    slug="imaging_translocation",
    title="Wortmannin drives FKHR-GFP into the nucleus of U2OS cells",
    source_stem="pilot-imaging/figures/figure1_imaging_translocation",
    primary_code="analysis/pilot-imaging_analysis.py",
    panel_notes=[
        "Panel a: Representative fields (crop of the {image_size} image) of U2OS cells expressing FKHR-EGFP "
        "(green) with DRAQ5 DNA stain (magenta), no drug and 150 nM Wortmannin for 1 h; both images use "
        "the same linear display range per channel. No scale bar: the pixel size of BBBC013 is not published.",
        "Panel b: Nuclear / cytoplasmic GFP ratio per well (points), mean +/- s.e.m. (bars), "
        "{n_control_wells} no-drug and {n_positive_wells} Wortmannin wells; {n_nuclei_total:,} nuclei in all "
        "wells used. Asterisks, {star_rule}.",
        "Panel c: Ratio against Wortmannin dose (log scale), mean +/- s.e.m. of the replicate wells per dose, "
        "with the wells as points; dashed line, the no-drug mean.",
    ],
    claim_boundary=(
        "Quantification is per well from automatically segmented nuclei (Otsu threshold on the DNA channel) "
        "and a ring around each nucleus as its cytoplasm; ratios are computed at render time from the public "
        "images. The data are BBBC013v1 by Ilya Ravkin (Broad Bioimage Benchmark Collection; {license}; "
        "Ljosa et al., Nature Methods, 2012); this is a pipeline pilot, not a new biological result."
    ),
)


if __name__ == "__main__":
    config = get_config()
    publish(SPEC, config)
