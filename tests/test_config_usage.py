"""Config-key usage (fig_atlas.config_usage, roadmap 2.1): what a build read,
what it asked for but the config lacked, and what fa lint makes of that."""
from __future__ import annotations

import copy
import json

import pytest

from fig_atlas import config_usage as cu


@pytest.fixture(autouse=True)
def _clean():
    for reg in (cu.READ, cu.MISSED, cu.DEFAULTS):
        reg.clear()
    yield
    for reg in (cu.READ, cu.MISSED, cu.DEFAULTS):
        reg.clear()


def test_tracking_dict_records_reads_and_misses():
    d = cu.TrackingDict({"plots": {"volcano": {"lfc_min": 1.0, "fdr_max": 0.05}, "pca": {"n": 2}},
                         "figures": {"dpi": 300}}, owner="c.yaml")
    v = d.get("plots", {}).get("volcano", {})
    assert v.get("lfc_min", 0.5) == 1.0
    assert v.get("legend_fontsize", 7) == 7                 # absent: default used
    assert d["figures"]["dpi"] == 300
    assert cu.READ["c.yaml"] == {"plots", "plots.volcano", "plots.volcano.lfc_min", "figures", "figures.dpi"}
    assert cu.MISSED["c.yaml"] == {"plots.volcano.legend_fontsize"}
    merged = {**d["plots"]["pca"]}                           # bulk copy counts as reading
    assert merged == {"n": 2} and "plots.pca.n" in cu.READ["c.yaml"]
    assert isinstance(d["plots"], dict)
    assert json.loads(json.dumps(d))["figures"]["dpi"] == 300   # still serialisable
    assert type(copy.deepcopy(d)) is dict


def test_lint_reports_unread_typos_and_defaults():
    config = {"project": {"name": "p"}, "plots": {"volcano": {"lfc_min": 1.0, "legend_font_size": 8, "old_key": 1}},
              "figures": {"dpi": 300, "palette": ["#000", "#fff"]}}
    read = {"plots", "plots.volcano", "plots.volcano.lfc_min", "figures.dpi", "figures.palette"}
    missed = {"plots.volcano.legend_fontsize", "figures.title_size"}
    res = cu.lint(config, read, missed)
    assert res["unread"] == ["plots.volcano.legend_font_size", "plots.volcano.old_key"]   # project.* is tooling
    assert res["typos"] == [{"key": "plots.volcano.legend_font_size", "code_reads": "plots.volcano.legend_fontsize"}]
    assert res["missed"] == ["figures.title_size", "plots.volcano.legend_fontsize"]


def test_unread_keys_are_grouped_by_reason():
    config = {"plots": {"old_heatmap": {"term_col": "x", "title_pad": 3},
                        "strip": {"show_band": False, "band": {"width": 1, "color": "k"}, "size": 2},
                        "panel": {"mode": "bars", "venn": {"alpha": 0.5}}}}
    read = {"plots.strip.show_band", "plots.strip.size", "plots.panel.mode"}
    code = 'cfg.get("strip"); s.get("show_band"); s.get("band"); p.get("venn"); p.get("mode")'
    unread = cu.lint(config, read, set())["unread"]
    groups = {g["key"]: g for g in cu.classify_unread(config, unread, read, code)}
    assert groups["plots.old_heatmap"] == {"key": "plots.old_heatmap", "keys": 2, "why": "no_code"}
    assert groups["plots.strip.band"]["why"] == "switched_off" and groups["plots.strip.band"]["toggle"] == "plots.strip.show_band"
    assert groups["plots.panel.venn"]["why"] == "not_reached"


def test_instrumented_renderers_record_the_defaults_they_fall_back_on():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    from fig_atlas import renderers as R
    cu.instrument_renderers()
    cu.instrument_renderers()                                # idempotent
    assert R.render_stacked_share_hbar._fa_tracked
    fig, ax = plt.subplots()
    counts = pd.DataFrame({"a": [3, 1], "b": [1, 3]}, index=["g1", "g2"])
    R.render_stacked_share_hbar(ax, counts, {"colors": {"a": "#000000", "b": "#ffffff"}})
    plt.close(fig)
    used = cu.DEFAULTS["renderer:render_stacked_share_hbar"]
    assert used and "colors" not in used                    # given keys are not defaults
    assert all(isinstance(k, str) for k in used)


def test_packs_are_wrapped_only_when_a_script_imports_them():
    """A build that never uses the omics pack must not load it (its files would
    join the figure's provenance as code); one that does gets it wrapped."""
    import subprocess
    import sys
    code = (
        "import sys\n"
        "from fig_atlas import config_usage as cu\n"
        "cu.instrument_renderers()\n"
        "print('loaded_before', 'fig_atlas_omics' in sys.modules)\n"
        "from fig_atlas_omics.renderers import render_volcano\n"
        "print('wrapped_after', getattr(render_volcano, '_fa_tracked', False))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert "loaded_before False" in out and "wrapped_after True" in out
