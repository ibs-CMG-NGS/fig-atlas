"""Plugin points and bundle contracts (roadmap 6a.2): fig_atlas.plugins,
fig_atlas.contracts, `fa bundle`, and the omics pack's registrations."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from fig_atlas import contracts as C
from fig_atlas import plugins
from fig_atlas.cli import main

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ plugins --
@pytest.mark.parametrize("group", ["renderers", "contracts", "ingest", "commands"])
def test_the_omics_pack_registers_each_group(group):
    names = {p.name for p in plugins.entry_points(group)}
    assert "omics" in names, f"fig_atlas.{group}: omics entry point missing -- re-run `pip install -e .`"


def test_recipes_group_is_known_and_may_be_empty():
    assert plugins.GROUPS["recipes"] == "fig_atlas.recipes"
    assert isinstance(plugins.entry_points("recipes"), list)


def test_a_broken_plugin_is_skipped_with_a_warning(monkeypatch):
    good = plugins.Plugin("contracts", "good", "fig_atlas.contracts:CORE_CONTRACTS", "x")
    bad = plugins.Plugin("contracts", "bad", "no_such_module_xyz:THING", "x")
    monkeypatch.setattr(plugins, "entry_points", lambda group: [bad, good])
    with pytest.warns(RuntimeWarning, match="contracts:bad .* failed to load"):
        loaded = plugins.load_all("contracts")
    assert [p.name for p, _ in loaded] == ["good"]


# ----------------------------------------------------------------- registry --
def test_every_ingest_target_is_a_callable_renderer():
    for plot_type, target in C.ingest_map().items():
        module, _, attr = target.partition(":")
        assert callable(getattr(importlib.import_module(module), attr)), plot_type


def test_every_contract_names_an_existing_document_and_a_renderer():
    ingest = C.ingest_map()
    for c in C.all_contracts():
        assert (ROOT / c.doc).is_file(), f"{c.name}: {c.doc} missing"
        assert c.required or c.role_columns or c.min_numeric or (c.input_glob and c.required_meta), \
            f"{c.name}: no required or numeric columns (table bundle) or required metadata (file bundle)"
        for t in c.plot_types:
            assert t in ingest, f"{c.name}: no renderer for plot_type {t}"


def test_a_plot_type_mapped_twice_is_an_error(monkeypatch):
    clash = plugins.Plugin("ingest", "clash", "x:y", "x")
    monkeypatch.setattr(plugins, "load_all", lambda group: [(clash, {"venn": "somewhere:else"})])
    with pytest.raises(ValueError, match="mapped twice"):
        C.ingest_map()


# ---------------------------------------------------------------- contracts --
def _bundle(tmp_path: Path, plot_type: str | None, csv: str | None, name: str = "b") -> Path:
    b = tmp_path / name
    (b / "metadata").mkdir(parents=True)
    (b / "inputs").mkdir()
    (b / "metadata" / "metadata.yaml").write_text(f"plot_type: {plot_type}\n" if plot_type else "app_version: x\n")
    if csv is not None:
        (b / "inputs" / "data.csv").write_text(csv)
    return b


def _levels(rep):
    return sorted((f.level, f.check) for f in rep.findings)


def test_a_matching_bundle_has_no_findings(tmp_path):
    rep = C.check_bundle(_bundle(tmp_path, "venn", "dataset,item\nA,g1\nB,g1\n"))
    assert rep.contract == "core.venn" and rep.renderer == "fig_atlas.renderers:render_venn"
    assert rep.findings == [] and rep.rows == 2


def test_missing_required_is_an_error_missing_expected_a_warning(tmp_path):
    rep = C.check_bundle(_bundle(tmp_path, "volcano", "log2FC,gene_id\n1,a\n"))
    assert ("error", "contract") in _levels(rep)            # padj missing
    rep = C.check_bundle(_bundle(tmp_path, "volcano", "log2FC,padj,s1,s2\n1,0.01,3,4\n", "b2"))
    assert _levels(rep) == [("warn", "contract")]           # gene_id/symbol/... missing, samples present
    assert "gene_id" in rep.findings[0].message


def test_too_few_sample_columns_warns(tmp_path):
    csv = "gene_id,symbol,base_mean,log2FC,lfcse,stat,pvalue,padj,s1\na,A,1,1,0.1,2,0.01,0.02,5\n"
    rep = C.check_bundle(_bundle(tmp_path, "volcano", csv))
    assert len(rep.findings) == 1 and "at least 2" in rep.findings[0].message   # lfcse/stat not counted


def test_structure_findings(tmp_path):
    multi = _bundle(tmp_path, "custom_multipanel", None, "multi")
    (multi / "inputs" / "a.csv").write_text("x\n1\n")
    assert _levels(C.check_bundle(multi)) == [("info", "contract"), ("info", "renderer"), ("info", "structure")]
    assert ("error", "structure") in _levels(C.check_bundle(_bundle(tmp_path, "venn", None, "empty")))
    assert ("warn", "structure") in _levels(C.check_bundle(_bundle(tmp_path, None, "a\n1\n", "noplot")))


# ---------------------------------------------------------------------- cli --
def test_fa_bundle_check_exit_codes(tmp_path, capsys):
    ok = _bundle(tmp_path, "venn", "dataset,item\nA,g\n", "ok")
    bad = _bundle(tmp_path, "venn", "dataset\nA\n", "bad")
    assert main(["--root", str(ROOT), "bundle", "check", str(ok)]) == 0
    assert main(["--root", str(ROOT), "bundle", "check", str(ok), str(bad)]) == 1
    assert "1 with errors" in capsys.readouterr().out


def test_fa_bundle_check_names_contract_and_renderer(tmp_path, capsys):
    """A bundle named on the command line gets a line even when it is ok:
    what it is, the contract it matched and the renderer that draws it."""
    ok = _bundle(tmp_path, "venn", "dataset,item\nA,g\n", "ok")
    capsys.readouterr()
    assert main(["--root", str(ROOT), "bundle", "check", str(ok)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("ok ") and "plot_type venn -> contract core.venn, renderer " in out


def test_fa_bundle_check_json(tmp_path, capsys):
    bad = _bundle(tmp_path, "venn", "dataset\nA\n", "bad")
    capsys.readouterr()
    assert main(["--root", str(ROOT), "bundle", "check", str(bad), "--json"]) == 1
    (rep,) = json.loads(capsys.readouterr().out)
    assert rep["errors"] == 1 and rep["contract"] == "core.venn"


def test_fa_omics_list_is_a_plugin_command(capsys):
    assert main(["--root", str(ROOT), "omics", "list", "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert "volcano" in info["plot_types"] and "render_volcano" in info["renderers"]


# ------------------------------------------------------------ image bundles --
def _image_bundle(tmp_path, meta: str, files=("dna.png",)):
    from PIL import Image
    import numpy as np
    b = tmp_path / "img"
    (b / "inputs").mkdir(parents=True)
    (b / "metadata").mkdir()
    for f in files:
        Image.fromarray(np.zeros((4, 4), np.uint8)).save(b / "inputs" / f)
    (b / "metadata" / "metadata.yaml").write_text(meta, encoding="utf-8")
    return b


def test_image_bundle_contract(tmp_path):
    ok = _image_bundle(tmp_path, "plot_type: image_panel\npixel_size: 0.3\nchannels:\n  - file: dna.png\n")
    rep = C.check_bundle(ok)
    assert rep.contract == "core.image" and rep.renderer == "fig_atlas.renderers:render_image_panel"
    assert rep.findings == [] and rep.rows == 1


def test_image_bundle_needs_pixel_size_and_existing_channels(tmp_path):
    rep = C.check_bundle(_image_bundle(tmp_path, "plot_type: image_panel\nchannels:\n  - file: gfp.png\n"))
    msgs = " | ".join(f.message for f in rep.findings if f.level == "error")
    assert "pixel_size" in msgs and "gfp.png" in msgs
    stated = _image_bundle(tmp_path / "s", "plot_type: image_panel\npixel_size: null\n"
                                           "pixel_size_note: not published\nchannels: [dna.png]\n")
    assert C.check_bundle(stated).findings == []           # null, stated on purpose, is accepted


# ------------------------------------------------- column roles (table bundles) --
def _table_bundle(tmp_path: Path, plot_type: str, params: str, csv: str) -> Path:
    b = tmp_path / plot_type
    (b / "metadata").mkdir(parents=True)
    (b / "inputs").mkdir()
    (b / "metadata" / "metadata.yaml").write_text(f"plot_type: {plot_type}\nplot_params:\n{params}", encoding="utf-8")
    (b / "inputs" / "data.csv").write_text(csv, encoding="utf-8")
    return b


def test_column_roles_follow_plot_params(tmp_path):
    ok = C.check_bundle(_table_bundle(tmp_path, "line_band", "  x_col: dose\n  y_col: v\n  group_col: g\n",
                                      "dose,v,g\n1,2,a\n"))
    assert ok.contract == "core.line_band" and ok.findings == []
    defaults = C.check_bundle(_table_bundle(tmp_path / "d", "line_band", "  error: sd\n", "x,y\n1,2\n"))
    assert defaults.findings == []                          # x / y: the renderer's default names
    gone = C.check_bundle(_table_bundle(tmp_path / "g", "line_band", "  x_col: dose\n  group_col: grp\n",
                                        "dose,y\n1,2\n"))
    assert "grp (group_col)" in gone.findings[0].message and gone.errors == 1
    unnamed = C.check_bundle(_table_bundle(tmp_path / "u", "threshold_scatter", "  x_col: e\n  y_col: p\n",
                                           "e,p\n1,0.1\n"))
    assert unnamed.errors == 1 and "effect_col, sig_col" in unnamed.findings[0].message


def test_role_defaults_match_the_renderer_schema():
    """A contract's default column name is the renderer's own default."""
    from fig_atlas.bundle_figure import resolve
    ingest = C.ingest_map()
    for c in C.CORE_CONTRACTS:
        if not c.role_columns:
            continue
        schema = resolve(ingest[c.plot_types[0]]).SCHEMA.all()
        for param, default in c.role_columns:
            assert schema[param].default == default, (c.name, param)
        assert all(p in schema for p in c.role_optional), c.name
