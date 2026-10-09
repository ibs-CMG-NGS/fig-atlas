"""Where renderers live: the core package plus any domain pack (roadmap 6a.1b/6a.2).

The core renderers are ``fig_atlas.renderers``. A domain pack adds its own
renderer package by declaring an entry point in the ``fig_atlas.renderers``
group, e.g. in its pyproject.toml::

    [project.entry-points."fig_atlas.renderers"]
    omics = "fig_atlas_omics.renderers"

Tools that need every renderer (schemas for ``fa param``, key tracking in
``fa build``, ``fa lint --hardcoded``, the inventory) ask this module, so the
core never names a pack. The entry points are read from the installed
package metadata: after adding a pack, re-run ``pip install -e .``.
"""
from __future__ import annotations

import functools
import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

GROUP = "fig_atlas.renderers"
CORE = "fig_atlas.renderers"


def packages() -> list[str]:
    """Renderer package names: the core first, then the installed packs (sorted)."""
    from .plugins import entry_points
    found = sorted({p.value for p in entry_points("renderers")} - {CORE})
    return [CORE, *found]


def package_modules() -> list[ModuleType]:
    """The renderer packages, imported (a pack that fails to import is skipped)."""
    out = []
    for name in packages():
        try:
            out.append(importlib.import_module(name))
        except ImportError:
            continue
    return out


def modules() -> dict[str, ModuleType]:
    """{short module name: module} for every renderer module of every package.
    Short names are unique across packages (a pack must not reuse a core name)."""
    out: dict[str, ModuleType] = {}
    for pkg in package_modules():
        for m in pkgutil.iter_modules(pkg.__path__):
            if m.name in out:
                raise ValueError(f"renderer module name {m.name!r} defined twice ({pkg.__name__})")
            out[m.name] = importlib.import_module(f"{pkg.__name__}.{m.name}")
    return out


def _package_dir(name: str) -> Path | None:
    """Source folder of a package, found without importing it (or its parents):
    the top-level package's location plus the remaining dotted parts."""
    import importlib.util
    top, *rest = name.split(".")
    try:
        spec = importlib.util.find_spec(top)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    d = Path(list(spec.submodule_search_locations)[0]).joinpath(*rest)
    return d if d.is_dir() else None


@functools.lru_cache(maxsize=1)
def _directories() -> tuple[Path, ...]:
    # Found without importing the packs: a build that never uses a pack must
    # not load it (its files would join the figure's provenance as "code").
    return tuple(d for d in (_package_dir(n) for n in packages()) if d is not None)


def directories() -> list[Path]:
    """Source folders of the renderer packages (for scans that read files)."""
    return list(_directories())


def _exported(pkg: ModuleType) -> dict[str, object]:
    """{plot name: render function} a renderer package exports (render_<name>)."""
    return {n.removeprefix("render_"): getattr(pkg, n) for n in getattr(pkg, "__all__", [])
            if n.startswith("render_")}


def find(name: str):
    """The function that draws plot ``name`` (``"volcano"`` or ``"render_volcano"``),
    and where it lives: ``("core" | "<package>" | "recipe", function)``.

    Looked up in the core renderers first (no pack is imported for them), then
    in the installed packs, then among the recipes (fig_atlas.recipes). A pack
    renderer wins over a recipe of the same name: it keeps the plot's own
    parameter names and schema (``volcano`` is both; the function draws the recipe).
    """
    name = name.removeprefix("render_")
    core = importlib.import_module(CORE)
    if name in _exported(core):
        return "core", _exported(core)[name]
    for pkg_name in packages()[1:]:
        try:
            pkg = importlib.import_module(pkg_name)
        except ImportError:
            continue
        if name in _exported(pkg):
            return pkg_name, _exported(pkg)[name]
    from . import recipes
    found = recipes.all_recipes()
    if name in found:
        r = found[name]
        return "recipe", lambda *args, params=None, **kw: recipes.render(r, *args, params=params, **kw)
    raise KeyError(f"no renderer or recipe called {name!r}; `fa renderers` lists them")


def available() -> list[dict]:
    """Every plot name that ``fig_atlas.render`` can draw, with where it lives."""
    rows = []
    for pkg in package_modules():
        where = "core" if pkg.__name__ == CORE else pkg.__name__
        rows += [{"name": n, "source": where, "function": f"{pkg.__name__}:render_{n}"} for n in _exported(pkg)]
    seen = {r["name"] for r in rows}
    from . import recipes
    for n, r in sorted(recipes.all_recipes().items()):
        rows.append({"name": n, "source": "recipe" if n not in seen else "recipe (also a pack renderer)",
                     "function": r.renderer})
    return sorted(rows, key=lambda r: (r["name"], r["source"]))


def render(name: str, *args, **kwargs):
    """Draw plot ``name`` wherever its renderer lives (see ``find``)."""
    return find(name)[1](*args, **kwargs)


def path_marker(path: str) -> str | None:
    """If ``path`` (a source file, '/' separators) is a renderer module, its
    short name; else None. Used to attribute config reads to a renderer."""
    p = path.replace("\\", "/")
    for d in directories():
        prefix = d.as_posix().rstrip("/") + "/"
        if p.startswith(prefix) and "/" not in p[len(prefix):]:
            return p[len(prefix):].removesuffix(".py")
    return None
