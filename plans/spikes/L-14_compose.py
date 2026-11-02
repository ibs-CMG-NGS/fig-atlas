"""L-14 spike: a layout inside a cell of another, finish across two levels.

Kept with the plan so the findings in plans/PLAN_LAYOUT_CATALOG.md section 16
can be rerun; nothing here is package code. From the fig-atlas root:
    python plans/spikes/L-14_compose.py <outdir>
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "examples" / "layouts"))
from _panels import draw  # noqa: E402

from fig_atlas import layouts  # noqa: E402
from fig_atlas.layouts._core import Layout  # noqa: E402
from fig_atlas.preflight import preflight  # noqa: E402

OUT = Path(sys.argv[1])
RC = {"font.size": 7, "axes.titlesize": 8, "axes.labelsize": 7, "xtick.labelsize": 6,
      "ytick.labelsize": 6, "legend.fontsize": 6}


def flatten(outer: Layout, inner: dict) -> Layout:
    """``inner`` maps a container letter of ``outer`` to the layout drawn in its cell.
    The container's first inner letter takes its place in the outer column and row;
    the inner layout's other columns and rows join as groups of their own."""
    cells, columns, rows = {}, [], []
    for letter, cell in outer.cells.items():
        if letter in inner:
            cells.update(inner[letter].cells)
        else:
            cells[letter] = cell
    def splice(groups, inner_groups_of):
        out = []
        for group in groups:
            new = []
            extra = []
            for letter in group:
                if letter in inner:
                    first, *rest = inner_groups_of(inner[letter])
                    new += first
                    extra += rest
                else:
                    new.append(letter)
            out.append(new)
            out += extra
        return out
    columns = splice(outer.columns, lambda lay: lay.columns)
    rows = splice(outer.rows, lambda lay: lay.rows)
    return Layout(cells, columns, rows, outer.shape + " (composed)")


def check(name, fig, lay):
    bad = [f"{f.severity} {f.check}: {f.message}" for f in preflight(fig, saved_bbox_in=None)
           if f.severity in ("error", "warn")]
    tags = {t.get_text(): t for t in fig.texts if t.get_gid() == "panel-tag"}
    fig.canvas.draw()
    xs = {l: round(t.get_window_extent().x0, 1) for l, t in tags.items()}
    ys = {l: round(t.get_window_extent().y0, 1) for l, t in tags.items()}
    print(f"[{name}] tags {sorted(tags)}  x {xs}  y {ys}")
    print(f"[{name}] columns {lay.columns} rows {lay.rows}")
    print(f"[{name}] preflight error/warn: {bad or 'none'}")
    fig.savefig(OUT / f"{name}.png", dpi=150)


def stack_of_rows():
    fcfg = {"hspace": 0.12, "wspace": 0.1, "panel_pad_mm": 1.0, "tags": {"size": 9.0, "pad_pt": 2.0}}
    fig = plt.figure(figsize=(180 / 25.4, 150 / 25.4))
    outer = layouts.stack(fig, fcfg, letters=("a", "b", "e"), height_ratios=[1.0, 1.0, 1.1])
    inner_row = layouts.row(outer.cells["b"], fcfg, letters=("b", "c", "d"))   # the one line per split cell
    for letter, panel in {"a": "dose_response", "b": "violin", "c": "histogram",
                          "d": "column_scatter", "e": "correlation_scatter"}.items():
        cell = inner_row.cells[letter] if letter in inner_row.cells else outer.cells[letter]
        draw(cell, panel)
    lay = flatten(outer, {"b": inner_row})
    layouts.finish(fig, lay, fcfg)
    check("stack_of_rows", fig, lay)
    inside = outer.cells["b"].bbox
    for l in "bcd":
        c = inner_row.cells[l].bbox
        assert inside.x0 - 1e-6 <= c.x0 and c.x1 <= inside.x1 + 1e-6 and inside.y0 - 1e-6 <= c.y0 and c.y1 <= inside.y1 + 1e-6, l
    print("[stack_of_rows] inner cells lie inside the container: yes")
    plt.close(fig)


def tall_left():
    fcfg = {"wspace": 0.12, "hspace": 0.12, "panel_pad_mm": 1.0, "tags": {"size": 9.0, "pad_pt": 2.0}}
    fig = plt.figure(figsize=(180 / 25.4, 100 / 25.4))
    outer = layouts.row(fig, fcfg, letters=("a", "b"), width_ratios=[1.2, 1.0])
    right = layouts.stack(outer.cells["b"], fcfg, letters=("b", "c"))
    draw(outer.cells["a"], "raincloud")
    draw(right.cells["b"], "paired_plot")
    draw(right.cells["c"], "bland_altman")
    lay = flatten(outer, {"b": right})
    layouts.finish(fig, lay, fcfg)
    check("tall_left", fig, lay)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(RC):
        stack_of_rows()
        tall_left()
