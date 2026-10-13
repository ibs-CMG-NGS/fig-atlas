"""Repository procedures as commands (roadmap Phase 7).

Each ``plan_*`` function reads the repository and returns a ChangeSet (what
would be created, moved or edited); the CLI shows it with ``--dry-run`` or
applies it. The rules they follow are the ones AGENTS.md states in prose:
naming and namespaces (section 2), project registration in .vscode/tasks.json,
promotion and retirement (section 5).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path
from string import Template

from .changeset import TASKS, ChangeConflict, ChangeSet, tasks_with
from .projects import ProjectError, list_projects

NAME = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
CATEGORIES = ("exploratory", "paper")
TEMPLATES = Path(__file__).parent / "templates"


def _template(template: str, **values) -> str:
    return Template((TEMPLATES / template).read_text(encoding="utf-8")).safe_substitute(values)


def project_paths(name: str, domain: str | None, category: str | None) -> dict[str, Path]:
    """Where a project's files live (AGENTS.md section 2): namespaced under
    <domain>/<category>/, or flat for a sandbox project."""
    ns = Path(domain, category) if domain else Path()
    return {
        "config": Path("configs") / ns / f"config_{name}.yaml",
        "analysis": Path("analysis") / ns / f"{name}_analysis.py",
        "spec": Path("figure_specs") / ns / f"figure_01_{name}.py",
        "outputs": Path(*ns.parts, name) if ns.parts else Path(name),
    }


INIT_GITIGNORE = """# fig-atlas project repository
# Input bundles: read-only, kept out of git (share them by other means).
raw_data/
# Built figures: rebuilt from configs + data (`fa build`).
outputs/
__pycache__/
*.pyc
site/
"""

INIT_README = """# Figure projects

Publication figures built with [fig-atlas](https://github.com/ibs-cmg-ngs/fig-atlas).
Rules for people and AI agents: [AGENTS.md](AGENTS.md).

| Folder | What |
|---|---|
| `configs/<domain>/<category>/` | one commented config per project: every visual value of its figures |
| `analysis/<domain>/<category>/` | one analysis script per project |
| `figure_specs/<domain>/<category>/` | one figure spec per figure: title, panel notes, claim boundary |
| `raw_data/` | input bundles (read-only; not in git) |
| `styles/` | this repository's own style presets (optional; fig-atlas ships the defaults) |
| `outputs/` | built figures, records and checks (`fa build`; not in git) |

Start: `fa new project <name> --domain <domain> --category exploratory`, then
`fa ingest bundle raw_data/<...>/<bundle> --project <name>` and `fa build <name> --preflight`.
"""


def plan_init(target: Path) -> ChangeSet:
    """An empty project repository: the folders, a .fig-atlas marker, .gitignore,
    README, the project rules (AGENTS.md, imported by CLAUDE.md and read by
    Gemini CLI). Files already there are kept; a different one is a conflict."""
    from .projects import MARKER
    target = Path(target)
    cs = ChangeSet(target)
    marker = ("# Marks this folder as a fig-atlas project repository (configs/, analysis/, figure_specs/, ...).\n"
              "# `fa` finds the repository by this file.\n")
    cs.create(Path(MARKER), marker)
    for d in ("configs", "analysis", "figure_specs", "raw_data", "styles"):
        if not (target / d).is_dir():
            cs.create(Path(d) / ".gitkeep", "")
    cs.create(Path(".gitignore"), INIT_GITIGNORE)
    cs.create(Path("README.md"), INIT_README)
    cs.create(Path("AGENTS.md"), (TEMPLATES / "init_AGENTS.md.tmpl").read_text(encoding="utf-8"))
    cs.create(Path("CLAUDE.md"), "# Claude Code\n\nThe project rules live in `AGENTS.md`.\n\n@AGENTS.md\n")
    cs.create(Path(".gemini") / "settings.json",
              json.dumps({"context": {"fileName": ["AGENTS.md", "GEMINI.md"]}}, indent=2) + "\n")
    cs.notes.append("next: `fa new project <name> --domain <domain> --category exploratory` (run inside the folder)")
    return cs


def plan_new_project(root: Path, name: str, domain: str | None = None, category: str | None = None,
                     raw_root: str | None = None, slug: str = "main", today: str | None = None) -> ChangeSet:
    """Config, analysis script and figure spec for a new project, registered
    in .vscode/tasks.json. Flat (sandbox) when no domain is given."""
    if not NAME.fullmatch(name):
        raise ProjectError(f"project name {name!r}: use lower-case letters, digits and '-'")
    if bool(domain) != bool(category):
        raise ProjectError("give both --domain and --category, or neither (a flat sandbox project)")
    if category and category not in CATEGORIES:
        raise ProjectError(f"--category must be one of {', '.join(CATEGORIES)}")
    if domain and not NAME.fullmatch(domain):
        raise ProjectError(f"domain {domain!r}: use lower-case letters and digits")
    if not re.fullmatch(r"[a-z0-9_]+", slug):
        raise ProjectError(f"slug {slug!r}: use lower-case letters, digits and '_'")
    clash = [p for p in list_projects(root) if p.name == name]
    if clash and clash[0].config != (root / project_paths(name, domain, category)["config"]).resolve():
        raise ProjectError(f"a project called {name!r} already exists: {clash[0].config_rel(root)}")

    paths = project_paths(name, domain, category)
    values = dict(name=name, date=today or _dt.date.today().isoformat(), slug=slug,
                  raw_root=raw_root or f"raw_data/{name}", config=paths["config"].as_posix(),
                  analysis_script=paths["analysis"].as_posix(),
                  source_stem=f"{paths['outputs'].as_posix()}/figures/figure1_{slug}")
    cs = ChangeSet(root)
    cs.create(paths["config"], _template("project_config.yaml.tmpl", **values))
    cs.create(paths["analysis"], _template("project_analysis.py.tmpl", **values))
    cs.create(paths["spec"], _template("project_spec.py.tmpl", **values))
    tasks = root / TASKS
    if tasks.is_file():
        cs.edit(TASKS, tasks_with(tasks.read_bytes().decode("utf-8"), add=(name,)))
    else:
        cs.notes.append(".vscode/tasks.json not found; the project is not added to the build dropdown")
    if category == "paper" and not re.fullmatch(rf"{re.escape(domain)}-paper-(main|supp)-fig\d+-[a-z0-9-]+", name):
        cs.notes.append(f"paper projects are named {domain}-paper-main-fig<N>-<slug> (AGENTS.md 5.1); "
                        "or create it as exploratory and `fa promote` it later")
    cs.notes.append(f"next: add a panel per data bundle with `fa ingest bundle <bundle> --project {name}` (bundles "
                    f"go under {values['raw_root']}/; `fa bundle check` them first), or write load() in "
                    f"{values['analysis_script']} for data you prepare yourself; then `fa build {name} --preflight`")
    return cs


# ------------------------------------------------------------- shared edits --
def _set_project_field(text: str, key: str, value: str) -> str:
    """Set ``project.<key>`` in a config, editing that one line (comments and
    layout kept); the result is checked by parsing it."""
    import yaml
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    try:
        start = next(i for i, ln in enumerate(lines) if re.match(r"^project:\s*(#.*)?$", ln))
    except StopIteration as exc:
        raise ChangeConflict("config has no top-level project: block") from exc
    pat = re.compile(rf"^(\s+{re.escape(key)}:\s*)(\"[^\"]*\"|'[^']*'|[^\s#]+)(\s*(#.*)?)$")
    for i in range(start + 1, len(lines)):
        if lines[i] and not lines[i][0].isspace() and not lines[i].lstrip().startswith("#"):
            break                                           # next top-level key
        m = pat.match(lines[i])
        if m:
            lines[i] = f'{m.group(1)}"{value}"{m.group(3)}'
            out = nl.join(lines)
            if (yaml.safe_load(out) or {}).get("project", {}).get(key) != value:
                raise ChangeConflict(f"could not set project.{key}")
            return out
    raise ChangeConflict(f"config has no project.{key}")


def _references(root: Path, needle: str, own: set[Path]) -> list[str]:
    """Files outside the project's own that mention ``needle`` (configs, analysis,
    specs, scripts, storylines) -- reported, never edited automatically."""
    hits = []
    # The whole name only: lab-dose must not match lab-dose-qc.
    whole = re.compile(rf"(?<![\w-]){re.escape(needle)}(?![\w-])")
    for d, pattern in (("configs", "*.yaml"), ("analysis", "*.py"), ("figure_specs", "*.py"), ("scripts", "*.py"),
                       ("docs/storylines", "*.yaml")):
        for p in sorted((root / d).rglob(pattern)) if (root / d).is_dir() else []:
            if p.resolve() in own or "__pycache__" in p.parts:
                continue
            if whole.search(p.read_text(encoding="utf-8", errors="replace")):
                hits.append(p.relative_to(root).as_posix())
    return hits


def _project_files(root: Path, name: str):
    from .projects import find_project
    p = find_project(root, name)
    if not p.namespace:
        raise ProjectError(f"{name} is a flat sandbox project (no <domain>/<category>); this command needs a namespace")
    domain, category = p.namespace.split("/")[:2]
    spec_dir = root / "figure_specs" / p.namespace
    specs = sorted(spec_dir.glob(f"figure_*_{name}.py")) if spec_dir.is_dir() else []
    script = root / p.analysis_script if p.analysis_script else None
    return p, domain, category, script, specs


def _moved_spec_text(text: str, old_ns: str, old_name: str, new_ns: str, new_name: str, new_script: str) -> str:
    text = re.sub(r'(primary_code\s*=\s*["\'])[^"\']*(["\'])', lambda m: f"{m.group(1)}{new_script}{m.group(2)}", text)
    return text.replace(f"{old_ns}/{old_name}/", f"{new_ns}/{new_name}/")


# ------------------------------------------------------------------- retire --
def plan_retire(root: Path, name: str) -> ChangeSet:
    """Move a project to <domain>/archive/ (AGENTS.md 5.3): config, analysis
    script and specs; their paths inside updated; dropped from the build list."""
    p, domain, category, script, specs = _project_files(root, name)
    cs = ChangeSet(root)
    if category == "archive":
        return cs                                           # already retired
    old_ns, new_ns = p.namespace, f"{domain}/archive"
    new_script = f"analysis/{new_ns}/{script.name}" if script else None
    cfg_text = p.config.read_bytes().decode("utf-8")
    if new_script:
        cfg_text = _set_project_field(cfg_text, "analysis_script", new_script)
    cs.move(p.config, root / "configs" / new_ns / p.config.name, cfg_text)
    if script and script.is_file():
        cs.move(script, root / new_script)
    for s in specs:
        txt = _moved_spec_text(s.read_bytes().decode("utf-8"), old_ns, name, new_ns, name, new_script or "")
        cs.move(s, root / "figure_specs" / new_ns / s.name, txt)
    tasks = root / TASKS
    if tasks.is_file():
        cs.edit(TASKS, tasks_with(tasks.read_bytes().decode("utf-8"), remove=(name,)))
    own = {p.config.resolve(), *(s.resolve() for s in specs)} | ({script.resolve()} if script else set())
    refs = _references(root, name, own)
    if refs:
        cs.notes.append(f"{len(refs)} other file(s) mention {name}; check they do not need it: " + ", ".join(refs[:8])
                        + (" ..." if len(refs) > 8 else ""))
    cs.notes.append(f"outputs will be written to outputs/{new_ns}/{name}/; the old outputs/{old_ns}/{name}/ "
                    "becomes an orphan in the master manifest")
    cs.notes.append("if a storyline lists it, move it to `retired:` in docs/storylines/<topic>/storyline.yaml "
                    "and run `fa storyline registry` and `fa storyline check`")
    return cs


# ------------------------------------------------------------------ promote --
def paper_name(domain: str, figure: int, slug: str, supp: bool = False) -> str:
    return f"{domain}-paper-{'supp' if supp else 'main'}-fig{int(figure)}-{slug}"


def plan_promote(root: Path, name: str, figure: int, slug: str, supp: bool = False) -> ChangeSet:
    """Promote an exploratory project to a paper figure (AGENTS.md 5.2): new
    name <domain>-paper-main-fig<N>-<slug>, files moved to <domain>/paper/ and
    renamed, project.name / spec_pattern / analysis_script, the script's
    CONFIG_PATH fallback, the specs' source_stem / primary_code, and the build
    list updated."""
    if not NAME.fullmatch(slug):
        raise ProjectError(f"slug {slug!r}: use lower-case letters, digits and '-'")
    try:
        p, domain, category, script, specs = _project_files(root, name)
    except ProjectError:
        suffix = f"-paper-{'supp' if supp else 'main'}-fig{int(figure)}-{slug}"
        if any(x.name.endswith(suffix) and x.namespace.endswith("/paper") for x in list_projects(root)):
            return ChangeSet(root)                          # already promoted
        raise
    new = paper_name(domain, figure, slug, supp)
    cs = ChangeSet(root)
    if name == new:
        return cs
    if category != "exploratory":
        raise ProjectError(f"{name} is in {p.namespace}; only exploratory projects are promoted")
    if any(x.name == new for x in list_projects(root)):
        raise ProjectError(f"a project called {new} already exists")
    old_ns, new_ns = p.namespace, f"{domain}/paper"
    new_script = f"analysis/{new_ns}/{new}_analysis.py"
    cfg_text = p.config.read_bytes().decode("utf-8")
    cfg_text = _set_project_field(cfg_text, "name", new)
    cfg_text = _set_project_field(cfg_text, "spec_pattern", f"figure_*_{new}.py")
    cfg_text = _set_project_field(cfg_text, "analysis_script", new_script)
    cs.move(p.config, root / "configs" / new_ns / f"config_{new}.yaml", cfg_text)
    if script and script.is_file():
        stext = script.read_bytes().decode("utf-8").replace(f"config_{name}.yaml", f"config_{new}.yaml")
        cs.move(script, root / new_script, stext)
    for s in specs:
        txt = _moved_spec_text(s.read_bytes().decode("utf-8"), old_ns, name, new_ns, new, new_script)
        cs.move(s, root / "figure_specs" / new_ns / s.name.replace(name, new), txt)
    tasks = root / TASKS
    if tasks.is_file():
        cs.edit(TASKS, tasks_with(tasks.read_bytes().decode("utf-8"), add=(new,), remove=(name,)))
    own = {p.config.resolve(), *(s.resolve() for s in specs)} | ({script.resolve()} if script else set())
    refs = _references(root, name, own)
    if refs:
        cs.notes.append(f"{len(refs)} other file(s) still name {name}; update them to {new} if they depend on it: "
                        + ", ".join(refs[:8]) + (" ..." if len(refs) > 8 else ""))
    cs.notes.append(f"record figure {figure} -> {new} in docs/storylines/<topic>/storyline.yaml, then run "
                    "`fa storyline registry` and `fa storyline check`")
    return cs


# ------------------------------------------------------------ ingest bundle --
def _value_from_bundle(param, value):
    """Bundle metadata sometimes stores lists/dicts as Python-literal strings,
    and counts as floats (30.0)."""
    import ast
    if isinstance(value, str) and param.type in (list, dict):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value
    if param.type is int and isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def plot_block(name: str, target: str, bundle_rel: str, schema, plot_params: dict, extra: dict,
               plot_type: str, today: str, style: dict | None = None) -> list[str]:
    """The config lines for one plots.<name> block: renderer, bundle, then every
    schema parameter -- the bundle's value where it gives one, else the default
    -- each with its description (AGENTS.md 1.2, 1.6). A default that follows
    the style (``StyleRef``, e.g. ``typography.title_size``) is written with the
    value the project's presets give (``style``: its merged config), so panels
    from different renderers start at the same text sizes."""
    from .param_tools import _yaml_value, comment_for
    from .schema import CODE_DEFAULT, StyleRef

    def line(key, value, comment, commented=False):
        body = f"{key}: {_yaml_value(value)}"
        return f"    {'# ' if commented else ''}{body:<34} # {comment}"

    out = [f"  # [{name}] {plot_type} from {bundle_rel} (fa ingest bundle, {today})",
           f"  {name}:",
           f'    renderer: "{target}"',
           f'    bundle: "{bundle_rel}"']
    given = dict(plot_params or {})
    for k, v in extra.items():
        given.setdefault(k, v)
    params = schema.all() if schema is not None else {}
    for key, p in params.items():
        if key in given:
            out.append(line(key, _value_from_bundle(p, given.pop(key)), comment_for(p) + " (from the bundle)"))
        elif p.default is CODE_DEFAULT:
            out.append(line(key, None, comment_for(p) + " (computed when unset)", commented=True))
        else:
            if isinstance(p.default, StyleRef):
                unset = object()
                d = StyleRef(p.default.path, unset).resolve(style)
                if d is unset:
                    out.append(line(key, p.default.fallback, comment_for(p)))
                else:
                    out.append(line(key, d, comment_for(p) + " (from the style preset)"))
            else:
                out.append(line(key, p.default, comment_for(p)))
    for key, v in given.items():          # bundle keys this renderer does not read
        out.append(f"    # {key}: {_yaml_value(v)}   # in the bundle metadata; not a parameter of this renderer")
    return out


def _insert_plot_block(text: str, name: str, block_lines: list[str]) -> str:
    """Add a block under the top-level plots: key (creating it if needed),
    leaving every other line as it was."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    idx = next((i for i, ln in enumerate(lines) if re.match(r"^plots:\s*(\{\s*\})?\s*(#.*)?$", ln)), None)
    if idx is None:
        while lines and lines[-1] == "":
            lines.pop()
        lines += ["", "plots:", *block_lines, ""]
        return nl.join(lines)
    if "{" in lines[idx]:
        lines[idx] = "plots:"
    end = idx + 1
    while end < len(lines) and (not lines[end] or lines[end][0].isspace() or lines[end].lstrip().startswith("#")):
        end += 1
    while end > idx + 1 and not lines[end - 1].strip():
        end -= 1                                              # keep trailing blank lines after the block
    return nl.join(lines[:end] + block_lines + lines[end:])


def plan_ingest_bundle(root: Path, bundle: Path, project: str, name: str | None = None,
                       today: str | None = None) -> ChangeSet:
    """Case B as a command: check the bundle, find its renderer from plot_type,
    and add a plots.<name> block with the renderer's full, commented parameter
    set (bundle values where given) to the project's config."""
    import yaml

    from .bundle_figure import drawable, resolve
    from .contracts import all_contracts, check_bundle, ingest_map
    from .projects import find_project
    # Normalise without following links: raw_data/ is often a link to other storage,
    # and the block must name the bundle by its path inside the repository.
    import os
    root_abs = Path(os.path.abspath(root))
    bundle = Path(os.path.abspath(bundle if Path(bundle).is_absolute() else root_abs / bundle))
    try:
        rel = bundle.relative_to(root_abs).as_posix()
    except ValueError as exc:
        raise ChangeConflict(f"{bundle} is outside the repository; put the bundle under raw_data/") from exc
    report = check_bundle(bundle, all_contracts(), ingest_map(), rel_to=root_abs)
    errors = [f.message for f in report.findings if f.level == "error"]
    if errors:
        raise ChangeConflict(f"{rel} fails its contract: " + "; ".join(errors))
    if not report.renderer:
        raise ChangeConflict(f"{rel}: no renderer for plot_type {report.plot_type!r} (`fa bundle contracts` lists them)")
    p = find_project(root, project)
    name = name or re.sub(r"[^a-z0-9_]+", "_", bundle.name.lower().removesuffix("_bundle")).strip("_")
    cfg_text = p.config.read_bytes().decode("utf-8")
    current = (yaml.safe_load(cfg_text) or {}).get("plots") or {}
    cs = ChangeSet(root)
    if name in current:
        if (current[name] or {}).get("bundle") == rel:
            return cs                                         # already ingested
        raise ChangeConflict(f"plots.{name} already exists in {p.config_rel(root)}; pass --name")
    meta = yaml.safe_load((bundle / "metadata" / "metadata.yaml").read_text(encoding="utf-8")) or {}
    fn = resolve(report.renderer)
    extra = {}
    if report.plot_type == "image_panel":
        chans = [c for c in meta.get("channels", []) if isinstance(c, dict)]
        extra = {k: v for k, v in (("pixel_size", meta.get("pixel_size")), ("pixel_unit", meta.get("pixel_unit")),
                                   ("channel_labels", [c.get("label", "") for c in chans] or None),
                                   ("channel_colors", [c.get("color") for c in chans] if chans and all(c.get("color") for c in chans) else None))
                 if v is not None}
    from .config import ProjectConfig
    style = ProjectConfig(p.config).settings                  # the config merged with its presets
    block = plot_block(name, report.renderer, rel, getattr(fn, "SCHEMA", None), meta.get("plot_params") or {},
                       extra, report.plot_type, today or _dt.date.today().isoformat(), style=style)
    new_text = _insert_plot_block(cfg_text, name, block)
    got = ((yaml.safe_load(new_text) or {}).get("plots") or {}).get(name) or {}
    if got.get("bundle") != rel or got.get("renderer") != report.renderer:
        raise ChangeConflict("the new plots block did not parse back as written")
    cs.edit(p.config, new_text)
    for f in report.findings:
        if f.level == "warn":
            cs.notes.append(f"bundle: {f.message}")
    if not drawable(fn):
        cs.notes.append(f"{fn.__name__} needs data prepared in the analysis script (it takes "
                        f"{', '.join(__import__('inspect').signature(fn).parameters)}); the block is written, "
                        "draw it in the script")
    script = (root / p.analysis_script) if p.analysis_script else None
    if script and script.is_file() and "draw_plots(" not in script.read_text(encoding="utf-8"):
        cs.notes.append(f"{p.analysis_script} does not call draw_plots(); draw plots.{name} there")
    return cs


# ------------------------------------------------------------- new renderer --
RENDERER_NAME = re.compile(r"^[a-z][a-z0-9_]*[a-z0-9]$")


def _source_dir(root: Path, module: str) -> Path | None:
    """A package's folder inside this repository (None if it lives elsewhere)."""
    d = root.joinpath(*module.split("."))
    if d.is_dir():
        return d
    from .renderer_registry import _package_dir
    found = _package_dir(module)
    if found and found.resolve().is_relative_to(root.resolve()):
        return found
    return None


def _module_file(root: Path, module: str) -> Path | None:
    d = _source_dir(root, module)
    if d is not None and (d / "__init__.py").is_file():
        return d / "__init__.py"
    parent = _source_dir(root, module.rpartition(".")[0]) if "." in module else root
    f = parent / f"{module.rpartition('.')[2]}.py" if parent is not None else None
    return f if f is not None and f.is_file() else None


def _with_export(text: str, name: str) -> str:
    """Add ``from .<name> import render_<name>`` and its ``__all__`` entry to a
    renderer package's __init__, each in sorted place; nothing else changes."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    if f"from .{name} import render_{name}" in lines:
        return text                                        # already exported
    imports = [i for i, ln in enumerate(lines) if re.match(r"^from \.\w+ import ", ln)]
    if not imports:
        raise ChangeConflict("no `from .<module> import ...` lines in the package __init__; add the export by hand")
    after = [i for i in imports if re.match(r"^from \.(\w+)", lines[i]).group(1) > name]
    if after:
        at = after[0]
    else:
        at = imports[-1]
        if lines[at].rstrip().endswith("("):
            while not lines[at].startswith(")"):
                at += 1
        at += 1
    lines.insert(at, f"from .{name} import render_{name}")
    start = next((i for i, ln in enumerate(lines) if ln.startswith("__all__ = [")), None)
    if start is None:
        raise ChangeConflict("no `__all__ = [` list in the package __init__; add the export by hand")
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "]")
    entry = f'    "render_{name}",'
    at = next((i for i in range(start + 1, end) if lines[i].strip() > entry.strip()), end)
    lines.insert(at, entry)
    return nl.join(lines)


def _with_ingest(text: str, attr: str, plot_type: str, target: str) -> str:
    """Add ``"<plot_type>": "<target>",`` at the end of the dict ``<attr> = {``."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    if f'    "{plot_type}": "{target}",' in lines:
        return text                                        # already registered
    start = next((i for i, ln in enumerate(lines)
                  if re.match(rf"^{re.escape(attr)}(\s*:[^=]+)?\s*=\s*\{{\s*$", ln)), None)
    if start is None:
        raise ChangeConflict(f"no `{attr} = {{` mapping found; register the plot_type by hand")
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "}")
    lines.insert(end, f'    "{plot_type}": "{target}",')
    return nl.join(lines)


def _from_existing(source: str, name: str, date: str) -> str:
    """The module of an existing renderer, renamed for ``name``: render_<src> and
    its SCHEMA name become the new name, relative imports become absolute (the
    copy may live in another package), and the docstring says where it started."""
    import inspect
    from .renderer_registry import find
    where, fn = find(source)
    if where == "recipe":
        raise ChangeConflict(f"{source!r} is a recipe (a core shape with preset columns); start from its shape "
                             "instead (`fa renderers` names it)")
    fn = inspect.unwrap(fn)                          # uses_schema wraps the function; copy its own module
    module = sys.modules[fn.__module__]
    src_name = fn.__name__.removeprefix("render_")
    text = Path(module.__file__).read_text(encoding="utf-8").replace("\r\n", "\n")
    pkg = module.__package__ or ""
    parent = pkg.rpartition(".")[0]
    text = re.sub(r"^from \.\.(\w)", lambda m: f"from {parent}.{m.group(1)}", text, flags=re.M)
    text = re.sub(r"^from \.(\w)", lambda m: f"from {pkg}.{m.group(1)}", text, flags=re.M)
    text = re.sub(rf"\brender_{src_name}\b", f"render_{name}", text)
    text = re.sub(rf'Schema\("{re.escape(src_name)}"', f'Schema("{name}"', text)
    note = (f'"""{name}: started from render_{src_name} (`fa new renderer {name} --from {src_name}`, {date}).\n'
            f"Change the drawing and its SCHEMA to the new shape; the copy keeps every Param of the original.\n\n")
    if text.startswith('"""'):
        return note + text[3:]
    return note + '"""\n' + text


def plan_new_renderer(root: Path, name: str, package: str = "fig_atlas.renderers", plot_type: str | None = None,
                      doc: str | None = None, today: str | None = None, start_from: str | None = None) -> ChangeSet:
    """A renderer skeleton with its SCHEMA, its test, the package export and,
    with ``plot_type``, the bundle mapping that lets `fa ingest bundle` find it."""
    from .plugins import PROJECT_PACKAGE
    from .renderer_registry import CORE, available, modules
    if not RENDERER_NAME.fullmatch(name):
        raise ProjectError(f"renderer name {name!r}: use lower-case letters, digits and '_' (a Python name)")
    project = False
    if package in (None, CORE) and _source_dir(root, CORE) is None:
        # A project repository (not the fig-atlas source): the renderer goes in
        # its own renderers/ folder, found by fig_atlas.plugins without installing.
        package, project = PROJECT_PACKAGE, True
    package = package or CORE
    pkg_dir = root / PROJECT_PACKAGE if project else _source_dir(root, package)
    new_pkg = project and not (pkg_dir / "__init__.py").is_file()
    if not project and (pkg_dir is None or not (pkg_dir / "__init__.py").is_file()):
        raise ChangeConflict(f"renderer package {package!r} is not a folder in this repository")
    rerun = (pkg_dir / f"{name}.py").is_file()       # a second run: the files below must match
    if not rerun and name in {r["name"] for r in available()} | set(modules()):
        raise ChangeConflict(f"a renderer, module or recipe called {name!r} already exists (`fa renderers`)")
    values = dict(name=name, package=package, date=today or _dt.date.today().isoformat(),
                  doc=doc or "describe what this plot shows and which data it takes.")
    cs = ChangeSet(root)
    if start_from:
        cs.create(pkg_dir / f"{name}.py", _from_existing(start_from, name, values["date"]))
        cs.create(Path("tests") / "renderers" / f"test_{name}.py",
                  _template("renderer_from_test.py.tmpl", **values, source=start_from.removeprefix("render_")))
    else:
        cs.create(pkg_dir / f"{name}.py", _template("renderer.py.tmpl", **values))
        cs.create(Path("tests") / "renderers" / f"test_{name}.py", _template("renderer_test.py.tmpl", **values))
    init = pkg_dir / "__init__.py"
    init_text = (_template("project_renderers_init.py.tmpl", **values) if new_pkg
                 else _with_export(init.read_bytes().decode("utf-8"), name))
    if plot_type and project:
        from .contracts import ingest_map
        if not RENDERER_NAME.fullmatch(plot_type):
            raise ProjectError(f"plot_type {plot_type!r}: use lower-case letters, digits and '_'")
        target = f"{PROJECT_PACKAGE}.{name}:render_{name}"
        if ingest_map().get(plot_type, target) != target:
            raise ChangeConflict(f"plot_type {plot_type!r} is already drawn by {ingest_map()[plot_type]}")
        init_text = _with_ingest(init_text, "INGEST", plot_type, target)
        cs.notes.append(f"bundles with plot_type: {plot_type} now go to render_{name} (renderers/__init__.py INGEST)")
    if new_pkg:
        cs.create(init, init_text)
    else:
        cs.edit(init, init_text)
    if plot_type and not project:
        from .contracts import ingest_map
        if not RENDERER_NAME.fullmatch(plot_type):
            raise ProjectError(f"plot_type {plot_type!r}: use lower-case letters, digits and '_'")
        if ingest_map().get(plot_type, f"{package}:render_{name}") != f"{package}:render_{name}":
            raise ChangeConflict(f"plot_type {plot_type!r} is already drawn by {ingest_map()[plot_type]}")
        if package == CORE:
            module, attr = "fig_atlas.contracts", "CORE_INGEST"
        else:
            from .plugins import entry_points
            top = package.split(".")[0]
            eps = [e for e in entry_points("ingest") if e.value.split(":")[0].split(".")[0] == top]
            if not eps:
                raise ChangeConflict(f"{top} declares no fig_atlas.ingest entry point; add one "
                                     "(docs/howto/new_domain_pack.md)")
            module, _, attr = eps[0].value.partition(":")
        mfile = _module_file(root, module)
        if mfile is None:
            raise ChangeConflict(f"{module} is not a file in this repository; register the plot_type by hand")
        cs.edit(mfile, _with_ingest(mfile.read_bytes().decode("utf-8"), attr, plot_type, f"{package}:render_{name}"))
        cs.notes.append(f"bundles with plot_type: {plot_type} now go to render_{name}; describe their columns in a "
                        "contract (docs/contracts/) so `fa bundle check` can check them")
    if project:
        cs.notes.append("a project renderer lives in this repository only; a shape other projects could use "
                        "(a bar, line, scatter, heatmap) is worth offering to the fig-atlas core later")
    elif package != CORE:
        cs.notes.append("a pack renderer is for a shape that means nothing outside its field (AGENTS.md section 3); "
                        "a bar, line, scatter or heatmap belongs in the core")
    module_rel = (pkg_dir / f"{name}.py").resolve().relative_to(root.resolve()).as_posix()
    what = (f"change the copied drawing in {module_rel} to the new shape" if start_from
            else f"replace the placeholder drawing in {module_rel}")
    if project:
        cs.notes.append(f"next: {what} (every visual value a Param in SCHEMA), "
                        f"then `python -m pytest tests/renderers/test_{name}.py` and `fa lint --hardcoded`; "
                        f"`fa param scaffold` writes its config block")
    else:
        cs.notes.append(f"next: {what} (every visual value a Param in SCHEMA), "
                        f"then `python -m pytest tests/renderers/test_{name}.py tests/test_renderer_schemas.py`, "
                        "`fa lint --hardcoded`, and `fa inventory` (CI checks that the renderer list is current)")
    return cs


__all__ = ["ChangeConflict", "paper_name", "plan_ingest_bundle", "plan_new_project", "plan_new_renderer", "plan_promote",
           "plan_retire", "plot_block", "project_paths"]
