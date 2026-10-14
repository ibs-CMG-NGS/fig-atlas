# How-to: write a domain pack

The core of fig-atlas (`fig_atlas`) is independent of any field. Knowledge of a particular field — electrophysiology, imaging, clinical — goes into a separate package, a **domain pack**, and the core finds packs only through entry points. The omics pack `fig_atlas_omics` is the first example.

This page shows how to make a pack from scratch, with an electrophysiology pack `fig_atlas_ephys` as the example. `tests/test_example_pack.py` takes the code blocks marked `<!-- file: ... -->` below as they are, builds a real pack from them and checks that it is recognised. So this page's example always works.

## 1. What goes into a pack

| What goes into a pack | Examples |
|---|---|
| Data readers and ingest adapters | Reading ABF/NWB files, converting an instrument's export format |
| Bundle contracts | Which columns, files and metadata must be there |
| Recipes | A core renderer (a shape) + this field's column roles, vocabulary and defaults |
| Analysis helpers | Spike detection, computing input resistance |
| Shapes that mean something only in this field | (rare) a sequence logo, genome tracks |

**Renderers are shapes.** Lines, bars, scatter plots and heatmaps go in the core even if the first data they draw are electrophysiology (AGENTS.md §3). For most of a field's figures, a recipe on a core shape is enough. `fa renderers` lists the shapes you can use.

## 2. Package layout

```
fig_atlas_ephys/
  __init__.py
  contracts.py        # bundle contracts + plot_type -> renderer mapping
  recipes.py          # recipes
  cli.py              # (optional) `fa ephys ...` commands
```

A pack may import the core, but the core never imports a pack.

<!-- file: fig_atlas_ephys/__init__.py -->
```python
"""Electrophysiology pack for fig-atlas (example from docs/howto/new_domain_pack.md)."""
```

## 3. Contracts

A bundle's contract is chosen by the `plot_type` in its `metadata.yaml`. `required` are the columns drawing cannot do without (missing: an error), `expected` the other columns the documentation asks for (missing: a warning). `INGEST` links a `plot_type` to the function (or recipe name) that draws it.

<!-- file: fig_atlas_ephys/contracts.py -->
```python
from fig_atlas.contracts import Contract

CONTRACTS = [
    Contract("ephys.iv", ("iv_curve",),
             required=("voltage_mV", "current_pA"),
             expected=("cell",),
             doc="docs/howto/new_domain_pack.md",
             title="Current-voltage steps: one row per (cell, voltage step)"),
]

# plot_type -> "module:function" that draws it
INGEST = {"iv_curve": "fig_atlas_ephys.recipes:render_iv_curve"}
```

## 4. Recipes

A recipe is data that ties one core renderer to this field's column roles and defaults. Below, a recipe draws an I-V curve with the core's `line_band` (a line with an error band). `surface` names the parameters a project config uses, and `aliases` maps those names to the generic ones.

<!-- file: fig_atlas_ephys/recipes.py -->
```python
from fig_atlas.recipes import recipe, render

IV_CURVE = recipe(
    "iv_curve", "fig_atlas.renderers.line_band:render_line_band",
    defaults={"x_col": "voltage_mV", "y_col": "current_pA", "error": "sem",
              "labels_xlabel": "Membrane potential (mV)", "labels_ylabel": "Current (pA)",
              "zero_line": True, "show_points": True},
    surface=("error", "show_points", "line_width", "labels_title"),
    aliases={},
)

RECIPES = [IV_CURVE]


def render_iv_curve(ax, df, params=None):
    return render(IV_CURVE, ax, df, params=params)
```

## 5. (Optional) commands

A pack can add its own commands under `fa`. `register` creates the subcommands and returns `{name: handler}`. If a name is the same as a core command, the core wins.

<!-- file: fig_atlas_ephys/cli.py -->
```python
import json


def register(subparsers):
    p = subparsers.add_parser("ephys", help="electrophysiology pack: what it provides")
    p.add_argument("action", choices=("list",))
    return {"ephys": run}


def run(args, root):
    from .contracts import CONTRACTS
    from .recipes import RECIPES
    print(json.dumps({"contracts": [c.name for c in CONTRACTS], "recipes": [r.name for r in RECIPES]}))
    return 0
```

## 6. Registering the entry points

Write the entry points in the pack's `pyproject.toml`. There are five groups; use only those you need.

<!-- file: entry_points.toml -->
```toml
[project.entry-points."fig_atlas.contracts"]
ephys = "fig_atlas_ephys.contracts:CONTRACTS"

[project.entry-points."fig_atlas.ingest"]
ephys = "fig_atlas_ephys.contracts:INGEST"

[project.entry-points."fig_atlas.recipes"]
ephys = "fig_atlas_ephys.recipes:RECIPES"

[project.entry-points."fig_atlas.commands"]
ephys = "fig_atlas_ephys.cli:register"
```

| Group | Value | Used by |
|---|---|---|
| `fig_atlas.renderers` | A renderer package (`"pack.renderers"`) | Only when the field has shapes of its own |
| `fig_atlas.contracts` | A list of `Contract` | `fa bundle check` |
| `fig_atlas.ingest` | `{plot_type: "module:function"}` | `fa bundle check` shows the renderer that draws it |
| `fig_atlas.recipes` | A list of `Recipe` | `fig_atlas.render("name", ...)`, `fa renderers` |
| `fig_atlas.commands` | A `register(subparsers)` function | `fa <pack command>` |

Then install it. Entry points are registered at installation, so run it again after each change to them.

```bash
pip install -e .
```

## 7. Checking

```bash
fa renderers                    # iv_curve should appear as a recipe
fa bundle contracts             # ephys.iv should appear
fa bundle check <bundle-folder>  # checks a plot_type: iv_curve bundle against its contract
fa ephys list                   # the pack's command
```

In an analysis script you draw by name, without knowing which pack the recipe is in.

```python
import fig_atlas
fig_atlas.render("iv_curve", ax, df, params={"error": "sem"})
```

If the pack has renderers, each must have a `SCHEMA` (`tests/test_renderer_schemas.py` checks every registered package) and no hardcoded style values (`fa lint --hardcoded`).

## Checklist

- [ ] Shapes use core renderers; the field's knowledge is in recipes, contracts and helpers
- [ ] Each contract has a human-readable document (`doc`)
- [ ] Recipes' `defaults` and `aliases` use only the core renderer's parameter names
- [ ] The entry points are in `pyproject.toml`, and `pip install -e .` was run again
- [ ] The pack's entries appear in `fa renderers` and `fa bundle contracts`
