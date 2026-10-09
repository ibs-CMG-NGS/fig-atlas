"""Parameter tools on top of the renderer schemas (roadmap Phase 2, step 2.3).

    fa param scaffold <renderer>          commented YAML block for a renderer's params
    fa param explain <project> <key>      where a config value comes from
    fa param sync <project> [--apply]     write the defaults the build fell back on into the config
    fa lint --hardcoded                   literal style values in renderer / analysis code

``sync`` makes the config the source of truth (AGENTS.md 1.2) without
guessing: the provenance record of the last ``fa build`` lists every config
path the code asked for but did not find, with the default it used
(``config.usage.defaults``). Writing exactly those values changes no figure;
comments come from the schema when a renderer declares the key. Edits go
through fig_atlas.yamledit, so comments and layout survive.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

from . import yamledit
from .schema import CODE_DEFAULT, Param, StyleRef


# ------------------------------------------------------------------ schemas --
def renderer_schemas() -> dict:
    """{module name: Schema} for every renderer module that declares one, in
    the core and in every installed pack (fig_atlas.renderer_registry)."""
    from .renderer_registry import modules
    return {name: mod.SCHEMA for name, mod in modules().items() if hasattr(mod, "SCHEMA")}


def renderer_function_modules() -> dict[str, tuple[str, ...]]:
    """{module: names of its render_* functions without the prefix}, so a
    renderer_defaults key (a function name) maps to the module's schema."""
    from .renderer_registry import modules
    return {name: tuple(n.removeprefix("render_") for n in dir(mod) if n.startswith("render_"))
            for name, mod in modules().items()}


def find_param(name: str) -> list[tuple[str, Param]]:
    """Schema'd renderers declaring a parameter called ``name``."""
    return [(r, s.all()[name]) for r, s in renderer_schemas().items() if name in s.all()]


def comment_for(p: Param) -> str:
    parts = [p.role]
    if p.unit:
        parts.append(p.unit)
    if p.tune:
        parts.append(p.tune)
    return "; ".join(x for x in parts if x)


def _yaml_value(v) -> str:
    return json.dumps(v, ensure_ascii=False) if not isinstance(v, bool) else ("true" if v else "false")


# ----------------------------------------------------------------- scaffold --
def scaffold(module: str, indent: int = 4) -> str:
    """The renderer's parameters as a commented YAML block (paste under
    ``plots.<name>:``). Computed defaults are listed commented out."""
    schema = renderer_schemas()[module]
    pad = " " * indent
    from .renderer_registry import modules
    pkg = modules()[module].__name__.rsplit(".", 1)[0].replace(".", "/")
    lines = [f"{pad[:-2]}# [{module}] parameters ({pkg}/{module}.py SCHEMA)"]
    for p in schema.all().values():
        d = p.default
        if isinstance(d, StyleRef):
            d = d.fallback
            note = f" (preset typography.{p.name} overrides this)"
        else:
            note = ""
        if d is CODE_DEFAULT:
            lines.append(f"{pad}# {p.name}:  # computed by the renderer when unset -- {comment_for(p)}")
        elif d is None:
            lines.append(f"{pad}# {p.name}: null  # {comment_for(p)}")
        else:
            lines.append(f"{pad}{p.name}: {_yaml_value(list(d) if isinstance(d, tuple) else d)}  # {comment_for(p)}{note}")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ explain --
def _lookup(d: dict, path: str):
    node = d
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def explain(root: Path, config_path: Path, key: str, record: dict | None, layout: list | None = None) -> list[str]:
    """Layer by layer, where ``key`` (dotted) gets its value; last one wins."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    names = (raw.get("project") or {}).get("style") or []
    names = [names] if isinstance(names, str) else names
    lines, final = [], None
    used = ((record or {}).get("config") or {}).get("usage") or {}
    defaults = used.get("defaults") or {}
    if key in defaults:
        lines.append(f"  code default      {defaults[key]!r}  (the build asked for it and the config lacked it)")
        final = ("code default", defaults[key])
    for n in names:
        from .config import style_path
        f = style_path(root, n)
        hit, v = _lookup(yaml.safe_load(f.read_text(encoding="utf-8")) or {}, key) if f.is_file() else (False, None)
        lines.append(f"  style {n:<12} {v!r}" if hit else f"  style {n:<12} -")
        if hit:
            final = (f"style {n}", v)
    hit, v = _lookup(raw, key)
    lines.append(f"  project config    {v!r}" if hit else "  project config    -")
    if hit:
        final = ("project config", v)
    if used:
        read = key in set(used.get("read") or [])
        missed = key in set(used.get("missed") or [])
        state = ("read it" if read else "fell back on the code default" if key in defaults
                 else "checked for it and found none (a renderer then used its own default)" if missed
                 else "did not read it")
        lines.append(f"  last build        {state}")
        leaf = key.rsplit(".", 1)[-1]
        for r, d in ((record or {}).get("renderer_defaults") or {}).items():
            if missed and leaf in d:
                lines.append(f"  renderer default  {d[leaf]!r}  ({r})")
                final = final or (f"renderer default ({r})", d[leaf])
    own = layout_param(layout or [], key)
    if own is not None:
        lines.append(f"  script layout: {comment_for(own)}")
    leaf = key.rsplit(".", 1)[-1]
    for r, p in ([] if own is not None else find_param(leaf)):
        lines.append(f"  schema {r}: {comment_for(p)}")
    lines.append(f"  => {final[1]!r} from {final[0]}" if final else "  => not set anywhere the tools can see")
    return lines


# --------------------------------------------------------------------- sync --
def sync_plan(record: dict, layout: list | None = None, config: dict | None = None) -> list[dict]:
    """The keys to add: each config path the build fell back on, its value,
    and a comment. Keys whose schema default is computed (CODE_DEFAULT) are
    flagged: writing them freezes today's computed value."""
    usage = (record.get("config") or {}).get("usage") or {}
    readers = usage.get("readers") or {}
    # (value, renderer module that read it); "script" = analysis-script code,
    # whose keys no renderer schema describes.
    found = {p: (v, readers.get(p, "script") if "readers" in usage else None)
             for p, v in (usage.get("defaults") or {}).items()}
    # Keys a script forwards only when set (``if k in cfg``): absent, the
    # renderer used its own default on a copy. Take it from renderer_defaults
    # when exactly one value is recorded under that name.
    by_name: dict[str, set] = {}
    origin: dict[str, str] = {}
    for r, d in (record.get("renderer_defaults") or {}).items():
        for k, v in d.items():
            by_name.setdefault(k, set()).add(json.dumps(v, sort_keys=True))
            origin[k] = r
    for path in usage.get("missed") or []:
        leaf = path.rsplit(".", 1)[-1]
        if path not in found and len(by_name.get(leaf, ())) == 1:
            found[path] = (json.loads(next(iter(by_name[leaf]))), origin[leaf])
    plan = []
    for path, (value, renderer) in sorted(found.items()):
        leaf = path.rsplit(".", 1)[-1]
        hits = find_param(leaf)
        if renderer == "script":
            hits = []                             # read by script code: no renderer schema describes it
        elif renderer:                            # only the schema of the renderer that read it
            mod = renderer.removeprefix("render_")
            hits = [h for h in hits if h[0] == mod or mod in renderer_function_modules().get(h[0], ())]
        own = layout_param(layout or [], path)    # the project's own description wins
        if own is not None:
            hits = [("layout", own)]
        computed = any(_is_computed(p) for _, p in hits) and own is None
        comment = comment_for(hits[0][1]) if hits else None
        skip = ("tooling block" if path.split(".", 1)[0] in ("paths", "project", "publish")
                else "default is null or empty (absent = derived or off)" if value in (None, {}, [])
                else "inside a list item (set it per item)" if config is not None and _under_list(config, path)
                else "computed by the renderer (writing freezes today's value)" if computed
                else "no schema describes it (add it to the script's LAYOUT_SCHEMA)" if comment is None
                else None)
        plan.append({"path": path, "value": value, "comment": comment, "computed": computed,
                     "schema": hits[0][0] if hits else None, "via": renderer, "skip": skip})
    return plan


def _under_list(config: dict, path: str) -> bool:
    node = config
    for part in path.split(".")[:-1]:
        if isinstance(node, list):
            return True
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return isinstance(node, list)


# ------------------------------------------------------------- LAYOUT_SCHEMA --
def layout_schema(script: Path) -> list[Param]:
    """An analysis script's ``LAYOUT_SCHEMA`` -- the config keys the script
    itself reads, by dotted path (``*`` matches one level) -- read from the
    source without running the script."""
    if not script or not Path(script).is_file():
        return []
    tree = ast.parse(Path(script).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "LAYOUT_SCHEMA" for t in node.targets):
            from .schema import Schema
            code = compile(ast.Expression(node.value), str(script), "eval")
            names = {"Schema": Schema, "Param": Param, "CODE_DEFAULT": CODE_DEFAULT,
                     "float": float, "int": int, "bool": bool, "str": str, "list": list, "dict": dict}
            schema = eval(code, {"__builtins__": {}, **names})  # noqa: S307 -- a literal Schema(...) only
            return list(schema.params)
    return []


def layout_param(layout: list[Param], path: str) -> Param | None:
    import fnmatch
    parts = path.split(".")
    for p in layout:
        pat = p.name.split(".")
        if len(pat) == len(parts) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, pat)):
            return p
    return None


def _is_computed(p: Param) -> bool:
    d = p.default.fallback if isinstance(p.default, StyleRef) else p.default
    return d is CODE_DEFAULT


def _insert_key(text: str, data, path: str, line_text: str) -> str | None:
    """Insert ``line_text`` (without indent) as the last key of the block
    mapping at ``path``'s parent: after the last content line of that
    block's last child, so comment lines that introduce the next block stay
    where they are. None if the parent is missing, empty or flow-style."""
    parts = path.split(".")
    node = data
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    if not isinstance(node, dict) or not node or node.fa.flow_style() or parts[-1] in node:
        return None
    last = list(node.keys())[-1]
    line, col = node.lc.key(last)
    lines = text.split("\n")
    end = line
    for k in range(line + 1, len(lines)):
        s_ = lines[k]
        if not s_.strip() or s_.lstrip().startswith("#"):
            continue
        if len(s_) - len(s_.lstrip()) <= col:
            break
        end = k
    new = " " * col + line_text
    prev = lines[end]
    if " # " in prev and " # " in new:                     # align with the neighbour's comment column
        target = prev.index(" # ")
        head, _, tail = new.partition(" # ")
        if len(head) < target:
            new = head.ljust(target) + " # " + tail
    lines.insert(end + 1, new)
    return "\n".join(lines)


def apply_sync(config_path: Path, plan: list[dict], include_computed: bool = False) -> list[str]:
    """Add the planned keys to the config by inserting lines (comments,
    order and layout untouched); returns the paths written. Each insertion is
    checked: the parsed config equals the old one plus exactly that key."""
    written = []
    for item in plan:
        if item["skip"] and not (include_computed and item["computed"] and item["comment"]):
            continue
        doc = yamledit.load(config_path)
        raw = config_path.read_bytes().decode("utf-8")
        nl = "\r\n" if "\r\n" in raw else "\n"
        text = raw.replace("\r\n", "\n")
        key = item["path"].rsplit(".", 1)[-1]
        line_text = f"{key}: {_yaml_value(item['value'])} # {item['comment']} (was the code default)"
        new = _insert_key(text, doc.data, item["path"], line_text)
        if new is None:
            continue
        before, after = yaml.safe_load(text), yaml.safe_load(new)
        node = before
        for part in item["path"].split(".")[:-1]:
            node = node[part]
        node[key] = item["value"]
        if before != after:
            raise ValueError(f"{config_path.name}: inserting {item['path']} would change other values; not written")
        config_path.write_bytes(new.replace("\n", nl).encode("utf-8"))
        yamledit.load(config_path)                  # still round-trips
        written.append(item["path"])
    return written


# ---------------------------------------------------------------- hardcoded --
STYLE_KWARGS = {"fontsize", "linewidth", "lw", "linewidths", "markersize", "ms", "s", "pad", "labelpad",
                "rotation", "alpha", "size", "width", "height", "headwidth", "mutation_scale", "labelsize",
                "length", "markeredgewidth", "mew", "elinewidth", "capsize"}
ALLOW = "fa: allow-literal"


def hardcoded(paths: list[Path]) -> list[dict]:
    """Calls passing a number literal to a visual keyword (fontsize=7,
    linewidth=0.5, ...) instead of a config value. A line carrying
    ``# fa: allow-literal <reason>`` is skipped."""
    out = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg in STYLE_KWARGS and isinstance(kw.value, ast.Constant) \
                        and isinstance(kw.value.value, (int, float)) and not isinstance(kw.value.value, bool):
                    line = lines[kw.value.lineno - 1]
                    if ALLOW in line:
                        continue
                    if kw.arg in ("alpha", "rotation") and kw.value.value in (0, 1):
                        continue           # identity values: no styling decision
                    out.append({"file": path.as_posix(), "line": kw.value.lineno, "kwarg": kw.arg,
                                "value": kw.value.value, "code": line.strip()[:110]})
    return out
