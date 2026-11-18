"""What a renderer outside fig-atlas may rely on (docs/decisions/0009).

A project repository's own renderers (its ``renderers/`` folder) stay there; they
are not expected to come back to the core. So the names they import are a
public contract: a release removes or changes one only with a deprecation
warning for at least one release before, and says so in the changelog under
"Changed".

The contract:

- the calling convention: ``render_<name>(ax, df, params)`` draws on a matplotlib
  Axes from a pandas DataFrame and a dict of parameters and returns the rows it
  drew; the module sets ``SCHEMA`` (and ``FAMILY``, the gallery family);
- a repository's ``renderers/__init__.py`` exports its renderers and may carry an
  ``INGEST`` table {plot_type: "renderers.module:render_function"};
- the names in ``API`` below, and every public renderer function
  (``fig_atlas.renderers.render_*``, or by name with ``fig_atlas.render``).

Anything else -- a module or name starting with ``_``, a helper inside another
renderer's module -- may change in any release. ``fa new renderer --from`` copies
a core renderer whole, so it reports the imports of the copy that are outside
the contract (:func:`outside`).
"""
from __future__ import annotations

import re

API: dict[str, frozenset[str]] = {
    "fig_atlas": frozenset({"render"}),
    "fig_atlas.schema": frozenset({"Schema", "Param", "CODE_DEFAULT", "StyleRef", "typography", "uses_schema"}),
    "fig_atlas.params": frozenset({"text_param"}),
    "fig_atlas.stats": frozenset({"stars"}),
}

_IMPORT = re.compile(r"^from\s+(fig_atlas[\w.]*)\s+import\s+\(?([^)\n]+(?:\n[^)\n]+)*?)\)?\s*(?:#.*)?$", re.M)


def _public_renderer(module: str, name: str) -> bool:
    parts = module.split(".")
    return (parts[:2] == ["fig_atlas", "renderers"] and not any(p.startswith("_") for p in parts)
            and name.startswith("render_"))


def outside(text: str) -> list[str]:
    """``module.name`` for each fig-atlas name the module source ``text``
    imports that is not part of the contract (sorted)."""
    out = set()
    for module, names in _IMPORT.findall(text):
        for raw in names.replace("\n", ",").split(","):
            name = raw.split("#")[0].strip().split(" as ")[0].strip()
            if not name:
                continue
            if (name in API.get(module, ()) or f"{module}.{name}" in API      # a name, or a listed module
                    or _public_renderer(module, name)):
                continue
            out.add(f"{module}.{name}")
    return sorted(out)
