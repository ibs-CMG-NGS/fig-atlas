"""Bundle contracts, machine-checkable (roadmap Phase 6a, step 6a.2).

A data bundle is ``<bundle>/inputs/data.csv`` + ``<bundle>/metadata/metadata.yaml``
(docs/contracts/new_plot_type_contract.md). Its ``plot_type`` selects a
contract and the renderer that draws it. A contract has two levels:

    required   columns the renderer needs -- missing one is an error
    expected   columns the contract document lists -- missing one is a warning

The core ships the contracts and plot types it can draw itself; domain packs
add theirs through the ``fig_atlas.contracts`` and ``fig_atlas.ingest`` entry
points (fig_atlas.plugins). ``fa bundle check`` runs them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Contract:
    name: str                          # e.g. "de_go.volcano"
    plot_types: tuple[str, ...]        # metadata.yaml plot_type values it covers
    required: tuple[str, ...] = ()     # columns the renderer needs (error if missing)
    expected: tuple[str, ...] = ()     # further columns the document requires (warning if missing)
    optional: tuple[str, ...] = ()     # recommended columns (never warned; not counted as samples)
    min_numeric: int = 0               # numeric columns beyond the named ones (e.g. sample columns)
    doc: str = ""                      # the human contract document, repository-relative
    title: str = ""
    required_meta: tuple[str, ...] = ()  # metadata.yaml keys that must be present (null allowed: stated as unknown)
    input_glob: str = ""               # inputs are files matching this (e.g. "*.tif") instead of inputs/data.csv
    meta_files: str = ""               # metadata key listing input files (strings or {file: ...}); each must exist
    # Generic shapes name their columns by parameter (x_col, y_col, ...). The
    # column a role needs is plot_params[<param>], else the renderer's default
    # given here (None: the bundle must name it); a role_optional parameter,
    # when set, must name a column that exists.
    role_columns: tuple[tuple[str, str | None], ...] = ()
    role_optional: tuple[str, ...] = ()


@dataclass
class Finding:
    level: str                         # error | warn | info
    check: str                         # structure | contract | renderer
    message: str


@dataclass
class BundleReport:
    bundle: str
    plot_type: str | None
    contract: str | None
    renderer: str | None
    rows: int | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(f.level == "error" for f in self.findings)

    @property
    def warnings(self) -> int:
        return sum(f.level == "warn" for f in self.findings)

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update(errors=self.errors, warnings=self.warnings)
        return d


# The core's own contracts and plot types (domain-neutral renderers).
CORE_CONTRACTS = [
    Contract("core.venn", ("venn",), required=("dataset", "item"),
             doc="docs/contracts/new_plot_type_contract.md",
             title="Set membership: one row per (set, item); 2-3 sets"),
    Contract("core.image", ("image_panel",), input_glob="*.*", required_meta=("pixel_size", "channels"),
             meta_files="channels",
             doc="docs/contracts/image_bundle_contract.md",
             title="Image files (one per channel) with pixel size and channel list in metadata.yaml"),
    Contract("core.line_band", ("line_band",), role_columns=(("x_col", "x"), ("y_col", "y")),
             role_optional=("group_col", "lower_col", "upper_col"),
             doc="docs/contracts/table_bundle_contract.md",
             title="Lines with error bands: replicate rows (x, value, optional group), or summarised rows"),
    Contract("core.threshold_scatter", ("threshold_scatter",),
             role_columns=(("x_col", None), ("y_col", None), ("effect_col", None), ("sig_col", None)),
             doc="docs/contracts/table_bundle_contract.md",
             title="Effect vs significance points: one row per item, columns named in plot_params"),
    Contract("core.violin", ("violin",), role_columns=(("x_col", "group"), ("y_col", "value")),
             doc="docs/contracts/table_bundle_contract.md",
             title="Distribution per category: one row per observation (category, value)"),
    Contract("core.histogram", ("histogram",), role_columns=(("x_col", "value"),), role_optional=("group_col",),
             doc="docs/contracts/table_bundle_contract.md",
             title="Distribution of a value: one row per observation, optional group"),
    Contract("core.dose_response", ("dose_response",), role_columns=(("x_col", "dose"), ("y_col", "response")),
             role_optional=("group_col",), doc="docs/contracts/table_bundle_contract.md",
             title="Dose series: one row per replicate (dose > 0, response), optional group"),
    Contract("core.survival", ("survival",), role_columns=(("time_col", "time"), ("event_col", "event")),
             role_optional=("group_col",), doc="docs/contracts/table_bundle_contract.md",
             title="Time to event: one row per subject (time, event 1/0), optional group"),
    Contract("core.boxplot", ("boxplot",), role_columns=(("x_col", "Sample"), ("y_col", "Expression")),
             doc="docs/contracts/table_bundle_contract.md",
             title="Values per category: one row per observation (category, value)"),
    Contract("core.stacked_bar", ("stacked_bar",),
             role_columns=(("x_col", "category"), ("stack_col", "part"), ("value_col", "count")),
             doc="docs/contracts/table_bundle_contract.md",
             title="Composition: one row per (category, part) with a count"),
]
CORE_INGEST = {
    "venn": "fig_atlas.renderers:render_venn",
    "image_panel": "fig_atlas.renderers:render_image_panel",
    "multi_group_heatmap": "fig_atlas.renderers:render_multi_group_heatmap",
    "line_band": "fig_atlas.renderers:render_line_band",
    "threshold_scatter": "fig_atlas.renderers:render_threshold_scatter",
    "violin": "fig_atlas.renderers:render_violin",
    "histogram": "fig_atlas.renderers:render_histogram",
    "dose_response": "fig_atlas.renderers:render_dose_response",
    "survival": "fig_atlas.renderers:render_survival",
    "stacked_bar": "fig_atlas.renderers:render_stacked_bar",
    "boxplot": "fig_atlas.renderers:render_boxplot",
}


def all_contracts() -> list[Contract]:
    """Core contracts plus every installed pack's (fig_atlas.contracts entry points)."""
    from .plugins import load_all
    out = list(CORE_CONTRACTS)
    for _, contracts in load_all("contracts"):
        out.extend(contracts)
    return out


def ingest_map() -> dict[str, str]:
    """plot_type -> "module:render_function", core plus installed packs. A
    plot type claimed twice with different renderers is an error."""
    from .plugins import load_all
    out = dict(CORE_INGEST)
    for plugin, mapping in load_all("ingest"):
        for plot_type, target in mapping.items():
            if out.get(plot_type, target) != target:
                raise ValueError(f"plot_type {plot_type!r} mapped twice: {out[plot_type]} and {target} "
                                 f"({plugin.group}:{plugin.name})")
            out[plot_type] = target
    return out


def contract_for(plot_type: str | None, contracts: list[Contract] | None = None) -> Contract | None:
    for c in contracts if contracts is not None else all_contracts():
        if plot_type in c.plot_types:
            return c
    return None


def find_bundles(root: Path) -> list[Path]:
    """Folders under ``root`` that look like bundles (metadata/metadata.yaml present)."""
    return sorted(p.parent.parent for p in Path(root).rglob("metadata/metadata.yaml"))


def check_bundle(path: Path, contracts: list[Contract] | None = None,
                 ingest: dict[str, str] | None = None, rel_to: Path | None = None) -> BundleReport:
    """Structure, contract and renderer checks for one bundle folder."""
    import pandas as pd
    import yaml
    path = Path(path)
    shown = path.relative_to(rel_to).as_posix() if rel_to and path.is_relative_to(rel_to) else path.as_posix()
    rep = BundleReport(shown, None, None, None)
    meta_f, data_f = path / "metadata" / "metadata.yaml", path / "inputs" / "data.csv"

    # structure
    meta = {}
    if not meta_f.is_file():
        rep.findings.append(Finding("error", "structure", "metadata/metadata.yaml missing"))
    else:
        try:
            meta = yaml.safe_load(meta_f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            rep.findings.append(Finding("error", "structure", f"metadata.yaml is not valid YAML: {exc}"))
    rep.plot_type = meta.get("plot_type") if isinstance(meta, dict) else None
    if meta_f.is_file() and not rep.plot_type:
        rep.findings.append(Finding("warn", "structure", "metadata.yaml has no plot_type (no contract or renderer can be chosen)"))
    df = None
    c = contract_for(rep.plot_type, contracts)
    others = sorted(p.name for p in (path / "inputs").glob("*.csv")) if (path / "inputs").is_dir() else []
    if c is not None and c.input_glob:
        # A file bundle (e.g. images): inputs are files matching the glob, not one table.
        files = sorted((path / "inputs").glob(c.input_glob)) if (path / "inputs").is_dir() else []
        if not files:
            rep.findings.append(Finding("error", "structure", f"no input files matching inputs/{c.input_glob}"))
        else:
            rep.rows = len(files)
    elif not data_f.is_file() and others:
        # Several input tables, read by a project script: a valid bundle, but
        # the single-table column contract does not apply.
        rep.findings.append(Finding("info", "structure",
                                    f"multi-file bundle ({len(others)} CSV files in inputs/); column contract not checked"))
    elif not data_f.is_file() or data_f.stat().st_size == 0:
        rep.findings.append(Finding("error", "structure", "inputs/data.csv missing or empty"))
    else:
        try:
            df = pd.read_csv(data_f, nrows=500)
            rep.rows = sum(1 for _ in data_f.open(encoding="utf-8", errors="replace")) - 1
        except Exception as exc:                       # noqa: BLE001 -- any parse failure is a finding
            rep.findings.append(Finding("error", "structure", f"inputs/data.csv cannot be read: {exc}"))
        if df is not None and rep.rows == 0:
            rep.findings.append(Finding("warn", "structure", "inputs/data.csv has a header but no rows"))

    # contract
    if c is None:
        if rep.plot_type:
            rep.findings.append(Finding("info", "contract", f"no contract for plot_type {rep.plot_type!r}"))
    else:
        rep.contract = c.name
        missing_meta = [k for k in c.required_meta if not (isinstance(meta, dict) and k in meta)]
        if missing_meta:
            rep.findings.append(Finding("error", "contract",
                                        f"metadata.yaml lacks {', '.join(missing_meta)} "
                                        "(write null, with a note, if the source does not give it)"))
        if c.meta_files and isinstance(meta, dict) and isinstance(meta.get(c.meta_files), list):
            names = [x.get("file") if isinstance(x, dict) else x for x in meta[c.meta_files]]
            gone = [str(n) for n in names if not n or not (path / "inputs" / str(n)).is_file()]
            if gone:
                rep.findings.append(Finding("error", "contract",
                                            f"{c.meta_files} names file(s) not in inputs/: {', '.join(gone)}"))
        if df is not None:
            cols = set(df.columns)
            missing = [x for x in c.required if x not in cols]
            if missing:
                rep.findings.append(Finding("error", "contract", f"missing required column(s): {', '.join(missing)}"))
            absent = [x for x in c.expected if x not in cols]
            if absent:
                rep.findings.append(Finding("warn", "contract",
                                            f"missing column(s) the contract lists: {', '.join(absent)}"))
            pp = (meta.get("plot_params") if isinstance(meta, dict) else None) or {}
            unnamed = [p for p, d in c.role_columns if not pp.get(p) and d is None]
            if unnamed:
                rep.findings.append(Finding("error", "contract", "plot_params must name the column for "
                                            f"{', '.join(unnamed)}"))
            roles = [(p, pp.get(p) or d) for p, d in c.role_columns if pp.get(p) or d]
            roles += [(p, pp[p]) for p in c.role_optional if pp.get(p)]
            gone = [f"{col} ({p})" for p, col in roles if col not in cols]
            if gone:
                rep.findings.append(Finding("error", "contract", f"missing column(s) named by plot_params: "
                                            f"{', '.join(gone)}"))
            if c.min_numeric:
                named = set(c.required) | set(c.expected) | set(c.optional)
                numeric = [x for x in df.columns if x not in named and pd.api.types.is_numeric_dtype(df[x])]
                if len(numeric) < c.min_numeric:
                    rep.findings.append(Finding("warn", "contract",
                                                f"{len(numeric)} numeric column(s) besides the named ones; "
                                                f"the contract expects at least {c.min_numeric}"))

    # renderer
    m = ingest if ingest is not None else ingest_map()
    if rep.plot_type:
        rep.renderer = m.get(rep.plot_type)
        if rep.renderer is None:
            rep.findings.append(Finding("info", "renderer",
                                        f"no renderer registered for plot_type {rep.plot_type!r}"))
    return rep
