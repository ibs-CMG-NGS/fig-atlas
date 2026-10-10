"""Which config keys a build actually read (roadmap Phase 2, step 2.1).

Scripts and renderers read config values with ``cfg.get("key", default)``; a
key the code never asks for is silently ignored, and a key the code asks for
but the config lacks silently falls back to a default typed in Python. Both
defeat "the config is the source of truth" (AGENTS.md 1.2) without a sound.

While ``fa build`` runs an analysis script (fig_atlas.provenance), every
ProjectConfig wraps its values in ``TrackingDict``, which notes each key path
that is read and each one that is asked for but missing. The provenance
record keeps both lists; ``fa lint`` compares them with the config file:

- unread   keys in the config that nothing read during the build (dead keys,
           or typos of a key the code wanted)
- missed   keys the code asked for that the config does not have (a Python
           default was used)
- typo     an unread key that is close to a missed key under the same parent

Copying a dict (``{**cfg}``, ``dict(cfg)``) counts as reading the keys copied,
so bulk merges never make keys look unused; the reads inside the copy are not
seen, which can only hide a dead key, never invent one.
"""
from __future__ import annotations

import difflib
import functools

ENABLED = False
READ: dict[str, set[str]] = {}     # config file -> dotted key paths read
MISSED: dict[str, set[str]] = {}   # config file -> dotted key paths asked for but absent
DEFAULTS: dict[str, dict[str, object]] = {}   # owner -> key path -> default value the code fell back on
READERS: dict[str, dict[str, str]] = {}       # owner -> key path -> renderer module that read it, or 'script'


def _reader() -> str:
    """The renderer module whose code asked for a missing key (its schema
    describes the key), or 'script' for analysis-script code."""
    import sys
    f = sys._getframe(2)
    while f is not None:
        name = f.f_code.co_filename.replace(chr(92), "/")
        # recipes.py reads a domain renderer's keys on its behalf: look past it.
        if not name.endswith(("fig_atlas/config_usage.py", "fig_atlas/schema.py", "fig_atlas/recipes.py")):
            from .renderer_registry import path_marker
            return path_marker(name) or "script"
        f = f.f_back
    return "script"


def _plain(v):
    """A JSON-safe copy of a default value (for the provenance record)."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    return repr(v)


def instrument_renderers() -> None:
    """Wrap every exported ``render_*`` of every renderer package (core and
    installed packs, fig_atlas.renderer_registry) so the ``params`` dict it
    receives is a TrackingDict (owner ``renderer:<name>``): the build then
    knows which renderer defaults each figure actually fell back on.
    Call before the analysis script imports the renderers."""
    import sys

    from .renderer_registry import CORE, packages
    # Packages -- the core one too -- are wrapped when the analysis script
    # imports them, not before: a figure that never uses a package must not
    # load it. Its files would become the figure's "code" in the provenance
    # record (and make it go stale), and importing every renderer up front
    # (seaborn, scipy) cost about 2 s per build (paper evidence E11).
    lazy = []
    for name in dict.fromkeys([CORE, *packages()]):
        if name in sys.modules:
            _instrument_package(sys.modules[name])
        else:
            lazy.append(name)
    if lazy and not any(isinstance(f, _InstrumentOnImport) for f in sys.meta_path):
        sys.meta_path.insert(0, _InstrumentOnImport(lazy))


class _InstrumentOnImport:
    """Meta-path hook: when a listed renderer package is imported, run the
    normal import and then wrap its exported renderers."""

    def __init__(self, names):
        self.names = set(names)

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.names:
            return None
        import importlib.util
        self.names.discard(fullname)                  # let the regular finders locate it
        spec = importlib.util.find_spec(fullname)
        if spec is None or spec.loader is None:
            return spec
        run = spec.loader.exec_module

        def exec_module(module):
            run(module)
            _instrument_package(module)
        spec.loader.exec_module = exec_module
        return spec


def _instrument_package(R) -> None:
    import inspect
    for name in list(getattr(R, "__all__", dir(R))):
        fn = getattr(R, name)
        if not (name.startswith("render_") and callable(fn)) or getattr(fn, "_fa_tracked", False):
            continue
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            continue
        if "params" not in sig.parameters:
            continue

        def make(fn=fn, sig=sig, owner=f"renderer:{name}"):
            def wrapper(*args, **kwargs):
                try:
                    bound = sig.bind_partial(*args, **kwargs)
                except TypeError:
                    return fn(*args, **kwargs)
                p = bound.arguments.get("params")
                if isinstance(p, dict) and not isinstance(p, TrackingDict):
                    bound.arguments["params"] = TrackingDict(p, owner)
                return fn(*bound.args, **bound.kwargs)
            functools.update_wrapper(wrapper, fn)   # name, doc, __wrapped__ and attributes such as SCHEMA
            wrapper._fa_tracked = True
            return wrapper
        setattr(R, name, make())


def _wrap(value, owner: str, prefix: str):
    if isinstance(value, dict) and not isinstance(value, TrackingDict):
        return TrackingDict(value, owner, prefix)
    if isinstance(value, list):
        return [_wrap(v, owner, prefix) for v in value]
    return value


class TrackingDict(dict):
    """A dict that records which of its keys are read (see module docstring)."""

    def __init__(self, data: dict, owner: str, prefix: str = ""):
        super().__init__({k: _wrap(v, owner, f"{prefix}{k}.") for k, v in data.items()})
        self._fa_owner = owner
        self._fa_prefix = prefix

    def _mark(self, key, hit: bool) -> None:
        (READ if hit else MISSED).setdefault(self._fa_owner, set()).add(f"{self._fa_prefix}{key}")

    def _mark_all(self) -> None:
        for k in dict.keys(self):
            self._mark(k, True)

    def get(self, key, default=None):
        hit = dict.__contains__(self, key)
        self._mark(key, hit)
        if not hit:
            DEFAULTS.setdefault(self._fa_owner, {})[f"{self._fa_prefix}{key}"] = _plain(default)
            READERS.setdefault(self._fa_owner, {})[f"{self._fa_prefix}{key}"] = _reader()
        return dict.get(self, key, default)

    def __getitem__(self, key):
        self._mark(key, dict.__contains__(self, key))
        return dict.__getitem__(self, key)

    def __contains__(self, key):
        self._mark(key, dict.__contains__(self, key))
        return dict.__contains__(self, key)

    def setdefault(self, key, default=None):
        self._mark(key, dict.__contains__(self, key))
        return dict.setdefault(self, key, default)

    # Bulk access: every key counts as read.
    def __iter__(self):
        self._mark_all()
        return dict.__iter__(self)

    def keys(self):
        self._mark_all()
        return dict.keys(self)

    def items(self):
        self._mark_all()
        return dict.items(self)

    def values(self):
        self._mark_all()
        return dict.values(self)

    def copy(self):
        self._mark_all()
        return dict(dict.items(self))

    def __reduce__(self):                        # pickling / deepcopy: a plain dict
        return (dict, (dict(dict.items(self)),))


def leaf_paths(d: dict, prefix: str = "") -> list[str]:
    """Dotted paths of the values in a config mapping (lists count as values)."""
    out = []
    for k, v in d.items():
        if isinstance(v, dict) and v:
            out += leaf_paths(v, f"{prefix}{k}.")
        else:
            out.append(f"{prefix}{k}")
    return out


# Structural blocks read by the build tooling (fa build, publish, verify) in
# other processes, not by the analysis script: never reported as unread.
TOOLING_BLOCKS = ("project", "paths", "publish")


def _node(config: dict, path: str):
    node = config
    for p in path.split(".") if path else []:
        node = node[p]
    return node


def classify_unread(config: dict, unread: list[str], read: set[str], code_text: str | None) -> list[dict]:
    """Group unread keys (a block whose keys are all unread is one entry) and
    say why each is unread:

    - ``no_code``        no code the build ran mentions the key's name -- the
                         code that read it is gone; editing it changes nothing
    - ``switched_off``   a ``show_X`` / ``X_enabled`` toggle beside it is false
                         and the code reads that toggle
    - ``not_reached``    the code knows the name but this build did not get
                         there (an alternative panel, a data-dependent branch)
    """
    leaves = [p for p in leaf_paths(config)]
    unread_set = set(unread)
    groups: list[str] = []
    for u in sorted(unread):
        parts = u.split(".")
        top = u
        for i in range(len(parts) - 1, 0, -1):
            anc = ".".join(parts[:i])
            under = [l for l in leaves if l == anc or l.startswith(anc + ".")]
            if under and all(l in unread_set for l in under):
                top = anc
            else:
                break
        if top not in groups and not any(top.startswith(g + ".") for g in groups):
            groups.append(top)
    out = []
    for g in groups:
        parent, _, name = g.rpartition(".")
        sib = _node(config, parent)
        toggle = None
        for k, v in (sib.items() if isinstance(sib, dict) else []):
            if v is False and (k.startswith("show_") or k.endswith("_enabled")):
                feat = k[5:] if k.startswith("show_") else k[: -len("_enabled")]
                path = f"{parent}.{k}" if parent else k
                if (name == feat or name.startswith(feat)) and path in read:
                    toggle = path
        n = sum(1 for l in leaves if l == g or l.startswith(g + "."))
        if toggle:
            why = "switched_off"
        elif code_text is not None and f'"{name}"' not in code_text and f"'{name}'" not in code_text:
            why = "no_code"
        else:
            why = "not_reached"
        out.append({"key": g, "keys": n, "why": why, **({"toggle": toggle} if toggle else {})})
    return out


def lint(config: dict, read: set[str], missed: set[str]) -> dict:
    """Compare a config file's keys with what a build read and asked for."""
    leaves = [p for p in leaf_paths(config) if p.split(".", 1)[0] not in TOOLING_BLOCKS]
    # A path counts as read if it, or any key below it, was read.
    read_or_below = set(read)
    for r in read:
        parts = r.split(".")
        read_or_below.update(".".join(parts[:i]) for i in range(1, len(parts)))
    unread = [p for p in leaves if p not in read_or_below]
    typos = []
    for u in unread:
        parent, _, name = u.rpartition(".")
        siblings = [m.rpartition(".")[2] for m in missed if m.rpartition(".")[0] == parent]
        close = difflib.get_close_matches(name, siblings, n=1, cutoff=0.75)
        if close:
            typos.append({"key": u, "code_reads": f"{parent}.{close[0]}" if parent else close[0]})
    return {"unread": unread, "missed": sorted(missed), "typos": typos}
