"""`fa layouts` and the `fa_layouts` MCP tool describe the layouts from their
docstrings (fig_atlas.layouts._catalog; plans/PLAN_LAYOUT_CATALOG.md card L-12).
The keys a docstring lists must be the keys its example configures, so the
command, the reference page and the examples cannot drift apart."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from fig_atlas import layouts
from fig_atlas.cli import main as fa_main
from fig_atlas.layouts._catalog import catalog
from fig_atlas.mcp_server import SPECS

ROOT = Path(__file__).resolve().parents[1]
INFO = catalog()
NAMES = [e["name"] for e in INFO["layouts"]]


def _keys(block: dict, prefix: str = "") -> set[str]:
    out = set()
    for key, value in block.items():
        out.add(prefix + key)
        if isinstance(value, dict):
            out |= _keys(value, prefix + key + ".")
    return out


def test_every_public_layout_is_listed():
    assert NAMES == list(layouts.LAYOUTS)
    assert set(layouts.__all__) == {"Layout", "finish", "panel_cells", *layouts.LAYOUTS}


@pytest.mark.parametrize("entry", INFO["layouts"], ids=NAMES)
def test_entry_has_shape_call_and_config(entry):
    assert entry["summary"] and entry["usage"]
    assert "+---" in entry["shape"] and entry["call"].startswith(f"layouts.{entry['name']}(fig, fcfg")
    assert entry["config"] and all(item["keys"] for item in entry["config"])
    assert (ROOT / entry["example"]).is_dir()


@pytest.mark.parametrize("entry", INFO["layouts"], ids=NAMES)
def test_documented_keys_are_the_examples_keys(entry):
    """Every key the docstring lists is set, with a comment, in the layout's example config."""
    config = yaml.safe_load((ROOT / entry["example"] / "config.yaml").read_text(encoding="utf-8"))["figures"]
    documented = {k for item in entry["config"] for k in item["keys"]}
    missing = documented - _keys(config)
    assert not missing, f"{entry['name']}: keys in the docstring but not in its example config: {sorted(missing)}"


def test_composition_is_described():
    comp = INFO["composition"]
    assert comp["max_depth"] == 2 and comp["values"] == "figures.cells.<letter>"
    assert "layouts.finish" in comp["example"] and comp["summary"][0].isupper()


def test_command_lists_one_and_composition(capsys):
    assert fa_main(["layouts"]) == 0
    listing = capsys.readouterr().out
    assert all(f"{name} " in listing for name in NAMES)
    assert fa_main(["layouts", "row"]) == 0
    assert "row.width_ratios" in capsys.readouterr().out
    assert fa_main(["layouts", "composition", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["max_depth"] == 2
    assert fa_main(["layouts", "nope"]) == 2


def test_the_mcp_tool_comes_from_the_command():
    assert any(s.name == "fa_layouts" and s.command == "layouts" for s in SPECS)


def test_no_matplotlib_to_describe_layouts():
    code = "import sys; from fig_atlas.layouts._catalog import catalog; catalog(); print('matplotlib' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "False"
