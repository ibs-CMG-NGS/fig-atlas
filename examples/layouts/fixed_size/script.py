"""Layout example: fixed_size -- panel b kept at its printed size (figures.cells.b.size_mm), a and c fitted.

    python examples/layouts/fixed_size/script.py [out.png]
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
    lay = layouts.wide_bottom(fig, fcfg, top=("a", "b"), bottom="c")
    for letter, panel in CFG["panels"].items():
        draw(lay.cells[letter], panel)
    layouts.finish(fig, lay, fcfg)          # fits a and c to their cells; b keeps its size
    return fig


if __name__ == "__main__":
    build().savefig(sys.argv[1] if len(sys.argv) > 1 else "fixed_size.png", dpi=200)
