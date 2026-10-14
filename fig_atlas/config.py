from __future__ import annotations

import os
from pathlib import Path

import yaml


def _expand(value: str) -> str:
    return os.path.expandvars(value)


def _deep_merge(base: dict, over: dict) -> dict:
    """Recursively merge ``over`` onto ``base``; ``over`` wins on conflicts."""
    out = dict(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def style_path(root: Path, name: str) -> Path:
    """A style preset: the project's ``styles/<name>.yaml`` if it has one, else
    the preset shipped with the package (``fig_atlas/styles/``). The returned
    path may not exist (an unknown name)."""
    own = Path(root) / "styles" / f"{name}.yaml"
    return own if own.exists() else Path(__file__).with_name("styles") / f"{name}.yaml"


class ProjectConfig:
    """Loads config.yaml and exposes typed accessors.

    Environment variables override path values: set RAW_ROOT or OUTPUT_ROOT
    to redirect data without editing config.yaml.

    A config may reference reusable named style presets via ``project.style``
    (a string or a list). Each preset is a ``styles/<name>.yaml`` file whose
    ``figures``/``plots`` blocks are deep-merged *underneath* this config, so
    the config always wins and shared styling accumulates as a named asset.
    """

    def __init__(self, config_path: Path) -> None:
        self._path = config_path.resolve()
        with self._path.open(encoding="utf-8") as f:
            self._raw: dict = yaml.safe_load(f) or {}
        self._apply_style_presets()
        self._apply_rcparams()
        # Under `fa build`, note which keys the run reads (fa lint; config_usage).
        from . import config_usage
        if config_usage.ENABLED:
            self._raw = config_usage.TrackingDict(self._raw, owner=str(self._path))

    def _apply_rcparams(self) -> None:
        """The ``rcparams:`` block (from the config or a style preset): matplotlib
        settings no script sets itself, applied when the config is loaded --
        e.g. a journal preset making maths text (exponents, subscripts) use the
        journal's font instead of matplotlib's DejaVu."""
        rc = self._raw.get("rcparams")
        if rc:
            import matplotlib
            matplotlib.rcParams.update(dict(rc))

    def _apply_style_presets(self) -> None:
        names = self._raw.get("project", {}).get("style")
        if not names:
            return
        if isinstance(names, str):
            names = [names]
        merged: dict = {}
        for name in names:
            # The project's own styles/ first (its presets and overrides), then
            # the presets shipped with the package (fig_atlas/styles/).
            preset_path = style_path(self.project_root, name)
            if not preset_path.exists():
                raise FileNotFoundError(
                    f"Style preset not found: {name!r} in {self.project_root / 'styles'} or the package's "
                    f"built-in presets (referenced by project.style in {self._path.name})"
                )
            with preset_path.open(encoding="utf-8") as f:
                preset = yaml.safe_load(f) or {}
            # Later presets override earlier ones; the config overrides all.
            merged = _deep_merge(merged, preset)
        self._raw = _deep_merge(merged, self._raw)

    @property
    def project_root(self) -> Path:
        """Repo root: the parent of whichever ancestor directory is named ``configs``.

        Config files may live directly under ``configs/`` (flat layout) or nested
        arbitrarily deep (e.g. ``configs/lab/paper/``) under a namespace subfolder;
        either way, the ancestor literally named ``configs`` marks the boundary.
        """
        for ancestor in [self._path.parent, *self._path.parents]:
            if ancestor.name == "configs":
                return ancestor.parent
        return self._path.parent

    @property
    def _namespace(self) -> Path:
        """Domain/category subpath inferred from where this config file lives
        under ``configs/`` (e.g. ``lab/paper``). ``Path(".")`` for flat configs
        directly under ``configs/``."""
        for ancestor in [self._path.parent, *self._path.parents]:
            if ancestor.name == "configs":
                return self._path.parent.relative_to(ancestor)
        return Path(".")

    def _resolve(self, path_str: str) -> Path:
        """Expand env vars, then anchor relative paths at the project root."""
        p = Path(_expand(path_str))
        return p if p.is_absolute() else self.project_root / p

    @property
    def settings(self) -> dict:
        """The whole config as a dict, merged with its style presets: the
        ``figures``, ``plots``, ``paths`` and any other blocks a script reads
        (``CONFIG.settings["plots"]["volcano"]``)."""
        return self._raw

    @property
    def project_name(self) -> str:
        """``project.name``: the project identifier."""
        return str(self._raw.get("project", {}).get("name", "default"))

    @property
    def raw_root(self) -> Path:
        """Absolute path to the raw-data root.

        Order: RAW_ROOT env var > paths.raw_root in config. Relative values are
        anchored at the project root, so callers can use this directly without a
        further ``project_root /`` join.
        """
        env = os.environ.get("RAW_ROOT")
        if env:
            return self._resolve(env)
        return self._resolve(self._raw["paths"]["raw_root"])

    @property
    def output_root(self) -> Path:
        """Root for all generated, rebuildable outputs (git-ignored).

        Order: OUTPUT_ROOT env var > paths.output_root in config > "outputs".
        An unset ``${OUTPUT_ROOT}`` placeholder in config falls back to "outputs".
        """
        env = os.environ.get("OUTPUT_ROOT")
        if env:
            return self._resolve(env)
        raw = self._raw.get("paths", {}).get("output_root", "outputs")
        expanded = _expand(raw)
        if not expanded or expanded.startswith("${"):
            expanded = "outputs"
        return self._resolve(expanded)

    @property
    def _project_output_dir(self) -> Path:
        """Per-project namespace under output_root, e.g. outputs/<project>/ for a
        flat config, or outputs/<domain>/<category>/<project>/ for a namespaced one."""
        return self.output_root / self._namespace / self.project_name

    @property
    def figure_count(self) -> int:
        """``project.figure_count``: how many figures the project publishes."""
        return int(self._raw["project"]["figure_count"])

    @property
    def figures_root(self) -> Path:
        """Where the script saves its figures: ``paths.figures_root``, else
        ``outputs/<domain>/<category>/<project>/figures``."""
        path_str = self._raw.get("paths", {}).get("figures_root")
        if path_str:
            return self._resolve(path_str)
        return self._project_output_dir / "figures"

    @property
    def supplementary_root(self) -> Path:
        """Where supplementary tables go (``paths.supplementary_root``, else
        the project's ``supplementary_tables`` output folder)."""
        path_str = self._raw.get("paths", {}).get("supplementary_root")
        if path_str:
            return self._resolve(path_str)
        return self._project_output_dir / "supplementary_tables"

    @property
    def manifests_root(self) -> Path:
        """Where build reports go (manifest, verification, preflight)."""
        path_str = self._raw.get("paths", {}).get("manifests_root")
        if path_str:
            return self._resolve(path_str)
        return self._project_output_dir / "manifests"

    @property
    def dpi(self) -> int:
        """``figures.dpi`` (default 300): resolution of the PNG files."""
        return int(self._raw.get("figures", {}).get("dpi", 300))

    @property
    def formats(self) -> list[str]:
        """``figures.formats`` (default png, pdf, svg): the files to save."""
        return list(self._raw.get("figures", {}).get("formats", ["png", "pdf", "svg"]))

    @property
    def readme_template(self) -> Path | None:
        """Optional project template for published figure READMEs
        (``publish.readme_template``, repository-relative); None = the
        package default, fig_atlas/templates/figure_README.md."""
        rel = (self._raw.get("publish") or {}).get("readme_template")
        return self._resolve(rel) if rel else None

    @property
    def page(self):
        """Final-print page geometry (``fig_atlas.page.PageSpec``) from a
        ``page:`` block (usually supplied by a ``styles/page_*.yaml`` preset),
        or None for configs not yet migrated to final-size rendering. With
        ``figures.page_columns`` (1, 1.5, 2, ...) the page is narrowed to that
        many of its named columns (``page.columns_mm``), so the figure is drawn
        at the journal's column width."""
        block = self._raw.get("page")
        if not block:
            return None
        from .page import PageSpec
        page = PageSpec.from_dict(block)
        span = (self._raw.get("figures") or {}).get("page_columns")
        return page.spanning(span) if span is not None else page

    @property
    def print_check(self) -> dict:
        """Minimum printed font/line sizes (``styles/print.yaml``'s
        ``print_check`` block), with conservative fallbacks."""
        block = self._raw.get("print_check", {}) or {}
        return {
            "min_font_pt": float(block.get("min_font_pt", 5.0)),
            "min_line_pt": float(block.get("min_line_pt", 0.25)),
        }

    def require_path(self, path: Path, label: str) -> None:
        """Raise FileNotFoundError naming ``label`` if ``path`` is missing."""
        if not path.exists():
            raise FileNotFoundError(f"{label} does not exist: {path}")


def find_config_file(project_root: Path | str, filename: str) -> Path:
    """Locate a shared settings file under ``configs/`` by name, at any depth.

    Library helpers that read study-level settings (e.g. ``anchor_classes.yaml``)
    use this instead of a hardcoded ``configs/<domain>/...`` path, the same way
    configs are discovered by filename (``get_config``). Raises if the name is
    missing or ambiguous -- pass an explicit path to the helper then.
    """
    root = Path(project_root)
    found = sorted((root / "configs").rglob(filename))
    found = [p for p in found if "archive" not in p.relative_to(root / "configs").parts]
    if len(found) != 1:
        where = ", ".join(str(p.relative_to(root)) for p in found) or "none"
        raise FileNotFoundError(
            f"Expected exactly one configs/**/{filename}, found {len(found)} ({where}); "
            f"pass the settings path explicitly.")
    return found[0]


def repo_root(start: Path | None = None) -> Path:
    """Locate the project repository by walking up from ``start`` (default: this
    file) to the first ancestor with a ``.fig-atlas`` marker (`fa init`) -- or,
    in the fig-atlas source tree and older repositories, a ``fig_atlas/`` directory.

    Depth-independent alternative to hardcoding ``Path(__file__).resolve().parents[N]``,
    which silently breaks if a script's own directory nesting ever changes (e.g. a
    project moving into a domain/category namespace subfolder under analysis/).
    """
    here = (start or Path(__file__)).resolve()
    for p in [here.parent, *here.parents]:
        if (p / ".fig-atlas").is_file() or (p / "fig_atlas").is_dir():
            return p
    raise RuntimeError(f"Could not locate the project repository (.fig-atlas) from {here}")


def get_config(config_path: Path | None = None) -> ProjectConfig:
    """Find and load config.yaml (or CONFIG_PATH), walking up from CWD if not given."""
    if config_path is not None:
        return ProjectConfig(config_path)

    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        path = Path(env_path)
        if not path.exists():
            for parent in [Path.cwd()] + list(Path.cwd().parents):
                for candidate in [parent / "configs" / env_path, parent / env_path]:
                    if candidate.exists():
                        return ProjectConfig(candidate)
        return ProjectConfig(path)

    for parent in [Path.cwd()] + list(Path.cwd().parents):
        for candidate in [parent / "configs" / "config.yaml", parent / "config.yaml"]:
            if candidate.exists():
                return ProjectConfig(candidate)
    raise FileNotFoundError(
        "Configuration file not found. Set CONFIG_PATH or ensure configs/config.yaml "
        "exists in current directory or any parent."
    )
