"""docs/howto/new_domain_pack.md is a test: the code blocks it marks with
``<!-- file: ... -->`` are written out verbatim as a pack, the pack is made
visible through package metadata (a dist-info folder with entry_points.txt,
so nothing is installed), and everything the how-to promises must work."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "howto" / "new_domain_pack.md"
tomllib = pytest.importorskip("tomllib")


def _blocks() -> dict[str, str]:
    text = DOC.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- file: (\S+) -->\s*\n```[a-z]*\n(.*?)\n```", re.S)
    return {m.group(1): m.group(2) + "\n" for m in pattern.finditer(text)}


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    blocks = _blocks()
    toml = tomllib.loads(blocks.pop("entry_points.toml"))
    for name, code in blocks.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(code, encoding="utf-8")
    dist = tmp_path / "fig_atlas_ephys-0.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: fig-atlas-ephys\nVersion: 0.0\n", encoding="utf-8")
    eps = toml["project"]["entry-points"]
    (dist / "entry_points.txt").write_text(
        "".join(f"[{group}]\n" + "".join(f"{k} = {v}\n" for k, v in items.items()) + "\n"
                for group, items in eps.items()), encoding="utf-8")
    bundle = tmp_path / "bundle"
    (bundle / "inputs").mkdir(parents=True)
    (bundle / "metadata").mkdir()
    (bundle / "metadata" / "metadata.yaml").write_text("plot_type: iv_curve\n", encoding="utf-8")
    rows = "".join(f"c{c},{v},{(v + 70) * (1.5 + 0.1 * c)}\n" for c in range(3) for v in range(-90, 41, 10))
    (bundle / "inputs" / "data.csv").write_text("cell,voltage_mV,current_pA\n" + rows, encoding="utf-8")
    return tmp_path


CHECK = """
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, pandas as pd
import fig_atlas
from fig_atlas import contracts, renderer_registry
from fig_atlas.cli import main
pack = sys.argv[1]
out = {}
out["recipe"] = [r["source"] for r in renderer_registry.available() if r["name"] == "iv_curve"]
rep = contracts.check_bundle(pack + "/bundle")
out["contract"], out["renderer"], out["findings"] = rep.contract, rep.renderer, len(rep.findings)
fig, ax = plt.subplots()
summary = fig_atlas.render("iv_curve", ax, pd.read_csv(pack + "/bundle/inputs/data.csv"), params={"error": "sem"})
out["points"] = len(summary)
print(json.dumps(out))
sys.exit(main(["--root", sys.argv[2], "ephys", "list"]))
"""


def test_the_how_to_pack_works(pack: Path):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(pack), os.environ.get("PYTHONPATH", "")]))
    res = subprocess.run([sys.executable, "-c", CHECK, str(pack), str(ROOT)], capture_output=True, text=True, env=env)
    assert res.returncode == 0, res.stderr[-2000:]
    first, second = res.stdout.strip().splitlines()[:2]
    got = json.loads(first)
    assert got == {"recipe": ["recipe"], "contract": "ephys.iv",
                   "renderer": "fig_atlas_ephys.recipes:render_iv_curve", "findings": 0, "points": 14}
    assert json.loads(second) == {"contracts": ["ephys.iv"], "recipes": ["iv_curve"]}
