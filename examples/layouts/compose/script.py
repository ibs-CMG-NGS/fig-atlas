"""Layout example: compose -- a layout inside a cell of another (a stack whose middle row is split).

    python examples/layouts/compose/script.py [out.png]
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import yaml

from fig_atlas import layouts

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _panels import draw  # noqa: E402  -- stands in for your data and renderers

CFG = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))


def build():
    fcfg = CFG["figures"]
    plt.rcParams.update(CFG["rc"])          # once, before drawing (AGENTS.md 1.4)
    fig = plt.figure(figsize=(fcfg["width_mm"] / 25.4, fcfg["height_mm"] / 25.4))
    lay = layouts.stack(fig, fcfg, letters=("a", "b", "e"))
    layouts.row(lay.cells["b"], fcfg, letters=("b", "c", "d"))    # split cell b into b | c | d
    cells = layouts.panel_cells(lay)        # every panel's cell, the split ones included
    for letter, panel in CFG["panels"].items():
        draw(cells[letter], panel)
    layouts.finish(fig, lay, fcfg)          # once, on the outer layout
    return fig


if __name__ == "__main__":
    build().savefig(sys.argv[1] if len(sys.argv) > 1 else "compose.png", dpi=200)
