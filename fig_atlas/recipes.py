"""Recipes: a domain plot as a generic renderer + settings (roadmap 6a.3).

Many domain figures are a generic shape with domain defaults -- a volcano plot
is a threshold scatter with x = log2 fold change, y = -log10(padj). A recipe
records that as data:

    renderer   "module:function" of a generic renderer
    defaults   its parameters for this plot (column roles, transforms, colours, ...)
    surface    the parameter names a project uses for this plot (the domain
               renderer's schema); only these are taken from the project's params
    aliases    domain name -> generic name (e.g. log2fc_threshold -> effect_threshold),
               so existing configs keep their keys

Each surface key is read from the project's params one by one, with the
recipe's value as the default -- so ``fa build`` still records exactly which
config keys a figure used, and keys the plot never used (say a global
``tick_label_size`` a volcano ignored) stay out.

Domain packs register recipes through the ``fig_atlas.recipes`` entry point
(a list of Recipe); ``render("volcano", ax, df, params=...)`` draws one.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from types import MappingProxyType


_UNSET = object()


def _schema_defaults(fn) -> dict:
    """Plain defaults of a schema-declared renderer (computed / style-preset
    defaults left out: the renderer resolves those itself)."""
    from .schema import CODE_DEFAULT, StyleRef
    schema = getattr(fn, "SCHEMA", None)
    if schema is None:
        return {}
    return {name: p.default for name, p in schema.all().items()
            if p.default is not CODE_DEFAULT and not isinstance(p.default, StyleRef)}


@dataclass(frozen=True)
class Recipe:
    name: str
    renderer: str                                   # "module:function"
    defaults: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))
    surface: frozenset = frozenset()                # empty: take every key the project passes
    aliases: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))
    doc: str = ""

    def params(self, user: dict | None) -> dict:
        """The generic renderer's params: its schema defaults, the recipe's
        defaults over them, then the project's values for the surface keys
        (translated through ``aliases``)."""
        out = _schema_defaults(self.function())
        out.update(self.defaults)
        user = user if user is not None else {}
        keys = sorted(self.surface) if self.surface else list(dict.keys(user))
        for k in keys:
            generic = self.aliases.get(k, k)
            v = user.get(k, out.get(generic, _UNSET))        # one tracked read per key
            if v is not _UNSET:
                out[generic] = v
        return out

    def function(self):
        module, _, attr = self.renderer.partition(":")
        return getattr(importlib.import_module(module), attr)


def recipe(name: str, renderer: str, defaults: dict | None = None, surface=(), aliases: dict | None = None,
           doc: str = "") -> Recipe:
    """Build a Recipe (read-only mappings, so a shared recipe cannot be edited by a caller)."""
    return Recipe(name, renderer, MappingProxyType(dict(defaults or {})), frozenset(surface),
                  MappingProxyType(dict(aliases or {})), doc)


CORE_RECIPES: list[Recipe] = []


def all_recipes() -> dict[str, Recipe]:
    """{name: Recipe}: the core's plus every installed pack's (fig_atlas.recipes)."""
    from .plugins import load_all
    out = {r.name: r for r in CORE_RECIPES}
    for plugin, recipes in load_all("recipes"):
        for r in recipes:
            if r.name in out and out[r.name] != r:
                raise ValueError(f"recipe {r.name!r} defined twice ({plugin.group}:{plugin.name})")
            out[r.name] = r
    return out


def get(name: str) -> Recipe:
    recipes = all_recipes()
    if name not in recipes:
        raise KeyError(f"no recipe {name!r}; installed: {', '.join(sorted(recipes)) or 'none'}")
    return recipes[name]


def render(name_or_recipe, *args, params: dict | None = None, **kwargs):
    """Draw a recipe: its generic renderer with the recipe's params."""
    r = name_or_recipe if isinstance(name_or_recipe, Recipe) else get(name_or_recipe)
    return r.function()(*args, params=r.params(params), **kwargs)
