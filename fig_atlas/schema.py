"""Renderer parameter schemas (roadmap Phase 2, step 2.0).

A renderer declares, next to its code, every parameter it reads: type,
default, unit, what it does and how to tune it -- the three things AGENTS.md
1.6 asks every config comment to say. From that single definition the tools
can validate a config, write its commented YAML block, explain where a value
came from, and keep code defaults from drifting apart.

    SCHEMA = Schema("volcano", params=[
        Param("fc_threshold", float, 1.0, unit="log2FC (data coords)",
              role="Vertical cut-off lines at +/- threshold", tune="raise to show only stronger changes",
              range=(0, None)),
        Param("title_size", float, StyleRef("figures.title_size", 8.0), unit="pt",
              role="Panel title font size", tune="lower if the title wraps"),
    ])

    @uses_schema(SCHEMA)
    def render_volcano(ax, df, params): ...

The renderer's ``params.get("key", default)`` calls stay as they are: the
decorator hands the renderer a ``BoundParams``, a dict that checks values
against the schema (warn by default, raise under ``FA_SCHEMA=strict``) and
answers a missing key with the schema default -- a ``StyleRef`` resolves to
the style preset's value, so one shared default replaces the copies typed in
each renderer. Renderers without a schema behave exactly as before.
"""
from __future__ import annotations

import functools
import os
import warnings
from dataclasses import dataclass, field
from typing import Any


class SchemaWarning(UserWarning):
    pass


class _CodeDefault:
    """Schema default meaning "whatever the renderer's own call passes":
    for defaults derived from other values (``a_sz * 0.8``) or that differ
    between code branches. A missing key then behaves exactly as before."""

    def __repr__(self) -> str:
        return "CODE_DEFAULT"


CODE_DEFAULT = _CodeDefault()


@dataclass(frozen=True)
class StyleRef:
    """A default taken from the merged style/config (``figures.title_size``),
    with ``fallback`` when no preset sets it."""
    path: str
    fallback: Any = None

    def resolve(self, style: dict | None) -> Any:
        node: Any = style or {}
        for part in self.path.split("."):
            if not isinstance(node, dict) or part not in node:
                return self.fallback
            node = node[part]
        return node


@dataclass(frozen=True)
class Param:
    """One parameter a renderer or script reads from the config.

    ``type`` is float, int, bool, str, list, dict, ``"color"``, ``"cmap"`` or
    a tuple of allowed values. ``default`` is the value used when the config
    has none (a number, a ``StyleRef`` to a style preset key, or
    ``CODE_DEFAULT``). ``unit``, ``role`` and ``tune`` are the three parts of
    the config comment (AGENTS.md 1.6): `fa param scaffold` writes them next
    to the key. ``range`` is (min, max), ``aliases`` old names still
    accepted, and ``open_keys`` marks a dict whose keys are free (rename
    maps, per-group colours).
    """
    name: str
    type: Any                     # float, int, bool, str, "color", "cmap", list, dict, or a tuple of choices
    default: Any = None
    unit: str = ""                # pt, mm, inches, "data coords", "[0-1] figure fraction", "hex color", ...
    role: str = ""                # what it controls, in the figure's terms
    tune: str = ""                # what raising / lowering it does
    range: tuple | None = None    # (min, max); None = open
    aliases: tuple = ()           # deprecated names still accepted
    open_keys: bool = False       # dict parameters whose keys are free (rename maps, per-class colours)

    def check(self, value: Any) -> str | None:
        """None if ``value`` fits, else a message."""
        if value is None:
            return None
        t = self.type
        if isinstance(t, tuple):
            return None if value in t else f"{self.name}={value!r} is not one of {', '.join(map(repr, t))}"
        if t == "color":
            from matplotlib.colors import is_color_like
            return None if is_color_like(value) else f"{self.name}={value!r} is not a colour"
        if t == "cmap":
            from matplotlib import colormaps
            return None if (isinstance(value, str) and value in colormaps) else f"{self.name}={value!r} is not a colormap"
        if t is float:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return f"{self.name}={value!r} should be a number"
        elif t is int:
            # 30.0 is accepted: YAML exporters often write whole numbers as floats,
            # and the renderers convert with int(); 30.5 is not.
            whole = isinstance(value, float) and value.is_integer()
            if isinstance(value, bool) or not (isinstance(value, int) or whole):
                return f"{self.name}={value!r} should be an integer"
        elif t is list:
            if not isinstance(value, (list, tuple)):          # scripts pass (lo, hi) pairs as tuples
                return f"{self.name}={value!r} should be a list"
        elif t in (bool, str, dict) and not isinstance(value, t):
            return f"{self.name}={value!r} should be {t.__name__}"
        if self.range and isinstance(value, (int, float)):
            lo, hi = self.range
            if (lo is not None and value < lo) or (hi is not None and value > hi):
                return f"{self.name}={value!r} is outside [{lo}, {hi}]"
        return None


@dataclass
class Schema:
    """The parameters of one renderer (or, as ``LAYOUT_SCHEMA``, the keys an
    analysis script reads itself): a list of ``Param`` plus shared groups in
    ``extends`` (e.g. ``typography()``). `fa param` and `fa lint` read it, and
    ``uses_schema`` checks the values a renderer receives against it."""
    name: str
    params: list[Param] = field(default_factory=list)
    extends: list["Schema"] = field(default_factory=list)

    def all(self) -> dict[str, Param]:
        out: dict[str, Param] = {}
        for base in self.extends:
            out.update(base.all())
        out.update({p.name: p for p in self.params})
        return out

    def default(self, name: str, style: dict | None = None) -> Any:
        d = self.all()[name].default
        return d.resolve(style) if isinstance(d, StyleRef) else d

    def validate(self, params: dict) -> list[str]:
        known = self.all()
        aliases = {a: p.name for p in known.values() for a in p.aliases}
        problems = []
        for k, v in dict.items(params):        # dict-level: no tracked bulk read
            if k in aliases:
                problems.append(f"{k} is deprecated; use {aliases[k]}")
                k = aliases[k]
            p = known.get(k)
            if p is not None:
                msg = p.check(v)
                if msg:
                    problems.append(msg)
        return problems


class BoundParams(dict):
    """The params dict a schema-declared renderer receives: values checked on
    entry; a missing key answered with the schema default (CODE_DEFAULT:
    the caller's own default). Reads go through the original dict, so a
    config TrackingDict still records exactly which keys were used."""

    def __init__(self, data: dict, schema: Schema, style: dict | None = None):
        super().__init__(dict.items(data))       # dict-level copy: no tracked bulk read
        self._src, self.schema, self.style = data, schema, style
        problems = schema.validate(data)
        if problems:
            text = f"{schema.name}: " + "; ".join(problems)
            if os.environ.get("FA_SCHEMA") == "strict":
                raise ValueError(text)
            warnings.warn(text, SchemaWarning, stacklevel=3)

    def _default(self, key, default):
        known = self.schema.all()
        if key not in known:
            return default
        d = self.schema.default(key, self.style)
        return default if d is CODE_DEFAULT else d

    def get(self, key, default=None):
        if dict.__contains__(self, key):
            return self._src.get(key, default)
        known = self.schema.all()
        if key in known:                         # a config still using a deprecated name
            for alias in known[key].aliases:
                if dict.__contains__(self, alias):
                    return self._src.get(alias, default)
        canonical = next((p.name for p in known.values() if key in p.aliases), None)
        if canonical and dict.__contains__(self, canonical):   # code still asking for the old name
            return self._src.get(canonical, default)
        return self._src.get(key, self._default(key, default))    # records the default actually used


def uses_schema(schema: Schema):
    """Decorate a renderer whose signature has a ``params`` argument: it
    receives a BoundParams. A ``_style`` entry in params (merged
    figures/plots/typography config) feeds StyleRef defaults."""
    import inspect

    def deco(fn):
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            bound = sig.bind_partial(*args, **kwargs)
            p = bound.arguments.get("params")
            if isinstance(p, dict) and not isinstance(p, BoundParams):
                bound.arguments["params"] = BoundParams(p, schema, dict.get(p, "_style") or active_style())
            elif p is None and "params" in sig.parameters:
                bound.arguments["params"] = BoundParams({}, schema, active_style())
            return fn(*bound.args, **bound.kwargs)
        wrapper.SCHEMA = schema
        return wrapper
    return deco


_STYLE_CACHE: dict = {}


def active_style() -> dict | None:
    """The build's project config (CONFIG_PATH), merged with its style
    presets, for StyleRef defaults; None outside a build."""
    path = os.environ.get("CONFIG_PATH")
    if not path:
        return None
    if path not in _STYLE_CACHE:
        try:
            import yaml
            from .config import _deep_merge, ProjectConfig
            cfg = ProjectConfig.__new__(ProjectConfig)       # without usage tracking
            from pathlib import Path as _P
            cfg._path = _P(path).resolve()
            cfg._raw = yaml.safe_load(cfg._path.read_text(encoding="utf-8")) or {}
            cfg._apply_style_presets()
            _STYLE_CACHE[path] = cfg._raw
        except Exception:
            _STYLE_CACHE[path] = None
    return _STYLE_CACHE[path]


# ------------------------------------------------------------- shared fragments --
TYPOGRAPHY_KEYS = ("title_size", "axes_label_size", "tick_label_size", "legend_fontsize")


def typography(**fallbacks) -> list[Param]:
    """The shared text sizes a renderer reads, e.g. ``typography(title_size=13,
    tick_label_size=8)``: each defaults to the style preset's ``typography:``
    block (final-size presets such as styles/print.yaml define it) and,
    where a preset has none, to the renderer's own historical default given
    here (CODE_DEFAULT: computed in the code) -- so projects without the
    block draw exactly as before."""
    spec = {"title_size": ("Panel title font size", "lower if the title wraps or crowds the panel"),
            "axes_label_size": ("Axis title (x/y label) font size", "lower if axis titles clip or crowd"),
            "tick_label_size": ("Tick label font size", "lower if tick labels overlap"),
            "legend_fontsize": ("Legend text font size", "lower if the legend covers data")}
    unknown = set(fallbacks) - set(spec)
    if unknown:
        raise ValueError(f"not typography keys: {sorted(unknown)}; use one of {TYPOGRAPHY_KEYS}")
    return [Param(k, float, StyleRef(f"typography.{k}", fb), unit="pt", role=spec[k][0], tune=spec[k][1])
            for k, fb in fallbacks.items()]
