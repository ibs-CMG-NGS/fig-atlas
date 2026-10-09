"""Parameter tools (fig_atlas.param_tools, roadmap 2.3): scaffold, explain,
sync (writing the defaults a build used) and the hard-coded literal lint."""
from __future__ import annotations

from pathlib import Path

import yaml

from fig_atlas import param_tools as pt


def test_scaffold_writes_a_commented_block_from_the_schema():
    text = pt.scaffold("grouped_hbar")
    block = yaml.safe_load("plots:\n  x:\n" + text)["plots"]["x"]
    assert block["bar_height"] == 0.36 and block["legend_loc"] == "lower right"
    assert "legend_fontsize" not in block                    # computed default: listed commented out
    assert "# legend_fontsize:  # computed by the renderer when unset" in text
    assert "bar_height: 0.36  # Height of each bar" in text and "data units" in text


CONFIG = """\
# [Panel a] dot plot
plots:
  go_dotplot:
    top_n: 10                     # terms per class
    colorbar_label: "-log10(padj)" # colour scale title

  # ------------------------------------------------------------------
  # [Panel b] next block header -- must stay above motif_dotplot
  motif_dotplot:
    top_n: 5
"""

RECORD = {"config": {"usage": {
    "defaults": {"plots.go_dotplot.show_size_legend": True, "plots.go_dotplot.mystery_knob": 3,
                 "paths.figures_root": None},
    "missed": ["plots.go_dotplot.xtick_ha", "plots.motif_dotplot.dot_alpha", "plots.go_dotplot.show_size_legend",
               "plots.go_dotplot.mystery_knob", "paths.figures_root"],
    "read": ["plots.go_dotplot.top_n"]}},
    "renderer_defaults": {"render_cross_condition_dotplot": {"xtick_ha": "right", "dot_alpha": 0.9}}}


def test_sync_plan_takes_defaults_and_matching_renderer_defaults():
    plan = {i["path"]: i for i in pt.sync_plan(RECORD)}
    assert plan["plots.go_dotplot.show_size_legend"]["value"] is True and not plan["plots.go_dotplot.show_size_legend"]["skip"]
    assert plan["plots.go_dotplot.xtick_ha"]["value"] == "right"
    assert plan["plots.go_dotplot.xtick_ha"]["via"] == "render_cross_condition_dotplot"
    assert "Horizontal alignment of rotated condition labels" in plan["plots.go_dotplot.xtick_ha"]["comment"]
    assert plan["plots.go_dotplot.mystery_knob"]["skip"].startswith("no schema describes it")
    assert plan["paths.figures_root"]["skip"] == "tooling block"


def test_sync_inserts_inside_the_block_and_keeps_comments(tmp_path):
    f = tmp_path / "config_x.yaml"
    f.write_text(CONFIG, encoding="utf-8")
    written = pt.apply_sync(f, pt.sync_plan(RECORD))
    assert sorted(written) == ["plots.go_dotplot.show_size_legend", "plots.go_dotplot.xtick_ha",
                               "plots.motif_dotplot.dot_alpha"]
    out = f.read_text(encoding="utf-8")
    lines = out.split("\n")
    i = lines.index('    colorbar_label: "-log10(padj)" # colour scale title')
    assert lines[i + 1].startswith("    show_size_legend: true") and lines[i + 2].startswith('    xtick_ha: "right"')
    assert lines[i + 3] == ""                                 # the blank line and next header stay below
    assert lines[i + 4].startswith("  # ----") and "must stay above motif_dotplot" in lines[i + 5]
    assert "(was the code default)" in lines[i + 1] and lines[i + 1].index("#") == lines[i].index("#")
    data = yaml.safe_load(out)["plots"]
    assert data["motif_dotplot"] == {"top_n": 5, "dot_alpha": 0.9}
    assert out.startswith(CONFIG.split("\n")[0])
    assert pt.apply_sync(f, pt.sync_plan(RECORD)) == []       # idempotent


def test_explain_walks_the_layers(tmp_path):
    root = tmp_path
    (root / "styles").mkdir()
    (root / "styles" / "house.yaml").write_text("plots:\n  go_dotplot:\n    top_n: 8\n")
    cfg = root / "config_x.yaml"
    cfg.write_text('project:\n  style: ["house"]\n' + CONFIG.split("\n", 1)[1], encoding="utf-8")
    lines = pt.explain(root, cfg, "plots.go_dotplot.top_n", RECORD)
    assert any("style house" in l and "8" in l for l in lines)
    assert lines[-1] == "  => 10 from project config"
    lines = pt.explain(root, cfg, "plots.go_dotplot.xtick_ha", RECORD)
    assert lines[-1] == "  => 'right' from renderer default (render_cross_condition_dotplot)"


def test_hardcoded_literals_are_found_unless_allowed(tmp_path):
    f = tmp_path / "render_x.py"
    f.write_text("def r(ax, params):\n"
                 "    ax.set_title('t', fontsize=13)\n"
                 "    ax.plot([0], linewidth=params.get('lw', 1.0))\n"
                 "    ax.text(0, 0, 'x', fontsize=6)  # fa: allow-literal tiny watermark by design\n"
                 "    ax.grid(alpha=1)\n")
    hits = pt.hardcoded([f])
    assert [(h["line"], h["kwarg"], h["value"]) for h in hits] == [(2, "fontsize", 13)]


def test_sync_takes_comments_only_from_the_schema_of_the_reader():
    record = {"config": {"usage": {
        "defaults": {"plots.motif.y_margin": 0.5, "plots.schematic.tick_len": 0.4},
        "readers": {"plots.motif.y_margin": "script", "plots.schematic.tick_len": "treatment_schematic"},
        "missed": ["plots.motif.y_margin", "plots.schematic.tick_len"], "read": []}}}
    plan = {i["path"]: i for i in pt.sync_plan(record)}
    # dumbbell's schema also has y_margin, but the script read this one: no borrowed comment
    assert plan["plots.motif.y_margin"]["skip"].startswith("no schema describes it")
    assert plan["plots.schematic.tick_len"]["comment"].startswith("Tick length on the timeline")
    assert not plan["plots.schematic.tick_len"]["skip"]


def test_tracker_names_the_renderer_that_asked():
    from fig_atlas import config_usage as cu
    from fig_atlas.renderers import two_set_euler
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cu.DEFAULTS.clear(); cu.READERS.clear()
    params = cu.TrackingDict({"a_label": "pathway"}, owner="cfg.yaml", prefix="plots.venn.")
    params.get("script_only_key", 1)                       # asked here, in test (script) code
    fig, ax = plt.subplots()
    two_set_euler.render_two_set_euler(ax, 10, 3, 2, 1, params=params)
    plt.close(fig)
    readers = cu.READERS["cfg.yaml"]
    assert readers["plots.venn.script_only_key"] == "script"
    assert readers["plots.venn.b_label"] == "two_set_euler"
    cu.DEFAULTS.clear(); cu.READERS.clear()


def test_layout_schema_is_read_without_running_the_script(tmp_path):
    script = tmp_path / "proj_analysis.py"
    script.write_text(
        "raise SystemExit('the script must not run')\n"
        "from fig_atlas.schema import Param, Schema\n"
        "LAYOUT_SCHEMA = Schema('proj layout', params=[\n"
        "    Param('figures.flow.*.text_color', 'color', '#1E293B', unit='hex color', role='Box text colour'),\n"
        "    Param('plots.legend.columnspacing', float, 1.0, unit='x font size', role='Gap between legend columns'),\n"
        "])\n")
    layout = pt.layout_schema(script)
    assert [p.name for p in layout] == ["figures.flow.*.text_color", "plots.legend.columnspacing"]
    assert pt.layout_param(layout, "figures.flow.motif.text_color").role == "Box text colour"
    assert pt.layout_param(layout, "figures.flow.motif.deep.text_color") is None     # * is one level

    record = {"config": {"usage": {
        "defaults": {"figures.flow.motif.text_color": "#1E293B", "plots.groups.line_y": 1.02,
                     "plots.legend.columnspacing": 1.0},
        "readers": {"figures.flow.motif.text_color": "script", "plots.groups.line_y": "cross_condition_heatmap",
                    "plots.legend.columnspacing": "script"},
        "missed": [], "read": []}}}
    config = {"figures": {"flow": {"motif": {"fill": "#fff"}}}, "plots": {"groups": [{"label": "a"}], "legend": {}}}
    plan = {i["path"]: i for i in pt.sync_plan(record, layout, config)}
    assert plan["figures.flow.motif.text_color"]["comment"].startswith("Box text colour") and not plan["figures.flow.motif.text_color"]["skip"]
    assert plan["plots.groups.line_y"]["skip"] == "inside a list item (set it per item)"
    assert plan["plots.legend.columnspacing"]["comment"].startswith("Gap between legend columns")
