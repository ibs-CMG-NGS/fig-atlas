from __future__ import annotations

import dataclasses
import json
import re
import shutil
from pathlib import Path
from string import Template

from .config import ProjectConfig
from .spec import FigureSpec

DEFAULT_TEMPLATE = Path(__file__).with_name("templates") / "figure_README.md"


def _display_path(path: Path, root: Path) -> str:
    """Path relative to ``root`` when possible, else the absolute path.

    Outputs can live outside the project (e.g. an external OUTPUT_ROOT), in which
    case ``relative_to`` would raise; fall back to the absolute path there.
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def publish(spec: FigureSpec, config: ProjectConfig) -> dict[str, str]:
    """Copy source figure files to a clean output folder and write a panel README.

    Source files are resolved as {output_root}/{spec.source_stem}.{ext}, i.e.
    source_stem is relative to the configured output_root (OUTPUT_ROOT).
    Raises FileNotFoundError if any expected format file is missing.
    """
    out_dir = spec.out_dir(config.figures_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_stem = config.output_root / spec.source_stem
    copied: list[str] = []

    for fmt in config.formats:
        src = source_stem.with_suffix(f".{fmt}")
        if not src.exists():
            raise FileNotFoundError(f"Missing source figure file: {src}")
        dst = out_dir / f"figure_{spec.number:02d}.{fmt}"
        shutil.copy2(src, dst)
        if dst.stat().st_size <= 0:
            raise RuntimeError(f"Empty copied figure file: {dst}")
        copied.append(_display_path(dst, config.project_root))

    # Provenance record written by `python -m fig_atlas.provenance` (fa build):
    # published beside the figure, with the figure's statistics tables added
    # (declared in the spec + listed by the data bundles it read), and
    # summarised in its README.
    from .provenance import statistics_tables
    record = None
    rec_src = Path(str(source_stem) + ".provenance.json")
    if rec_src.is_file():
        try:
            record = json.loads(rec_src.read_text(encoding="utf-8"))
        except ValueError:
            record = None
    tables = statistics_tables(config.project_root, record, list(spec.statistics_tables))

    # Live numbers: {name} placeholders in the spec text take the values the
    # build recorded (fig_atlas.claims). Unfilled ones stay visible in the
    # README, where verify fails on them.
    from .claims import fill
    values = (record or {}).get("claims") or {}

    def _fill(text: str) -> str:
        return fill(text, values)[0]

    spec = dataclasses.replace(spec, title=_fill(spec.title), panel_notes=[_fill(n) for n in spec.panel_notes],
                               claim_boundary=_fill(spec.claim_boundary))
    # Source data (fig_atlas.source_data): the tables each panel plots, written
    # by the build; published as figure_NN_source_data/ with an index.
    sd_dir = out_dir / f"figure_{spec.number:02d}_source_data"
    if sd_dir.exists():
        shutil.rmtree(sd_dir)                        # never keep tables of an older build
    sd_entries: list[dict] = []
    if record and record.get("source_data"):
        from .source_data import index_markdown
        sd_dir.mkdir()
        for e in record["source_data"]:
            dst = sd_dir / Path(e["path"]).name
            shutil.copy2(config.project_root / e["path"], dst)
            sd_entries.append({**e, "published": _display_path(dst, config.project_root).replace("\\", "/")})
        (sd_dir / "README.md").write_text(index_markdown(sd_entries, spec.number, spec.title), encoding="utf-8")

    # Test tables (fig_atlas.stats): written by the build beside the figure,
    # published as figure_NN_statistics/; the statistics-table entries then
    # name the published copy, so verify checks what readers get.
    st_dir = out_dir / f"figure_{spec.number:02d}_statistics"
    if st_dir.exists():
        shutil.rmtree(st_dir)                        # never keep tables of an older build
    if record and record.get("statistics"):
        st_dir.mkdir()
        meta = {e["path"]: e for e in record["statistics"]}
        for t in tables:
            e = meta.get(t["path"])
            if t["source"] != "stats_layer" or e is None:
                continue
            src = config.project_root / e["path"]
            if src.is_file():
                dst = st_dir / src.name
                shutil.copy2(src, dst)
                t.update(path=_display_path(dst, config.project_root).replace("\\", "/"), built=e["path"],
                         title=e.get("title", ""), rows=e.get("rows"), exists=dst.stat().st_size > 0)

    if rec_src.is_file():
        rec_dst = out_dir / f"figure_{spec.number:02d}.provenance.json"
        if record is not None:
            published = {**record, "statistics_tables": tables,
                         **({"source_data": sd_entries} if sd_entries else {})}
            rec_dst.write_text(json.dumps(published, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        else:
            shutil.copy2(rec_src, rec_dst)
        copied.append(_display_path(rec_dst, config.project_root))

    _write_readme(spec, config, out_dir, copied, record, tables, sd_entries)

    result: dict[str, str] = {
        "figure": str(spec.number),
        "title": spec.title,
        "folder": _display_path(out_dir, config.project_root),
        "primary_code": spec.primary_code,
        "source_stem": spec.source_stem,
    }
    for fmt, path in zip(config.formats, copied):
        result[fmt] = path
    return result


def _image_lines(record: dict | None) -> list[str]:
    """README 'Images' section from the record's image adjustments (fig_atlas.images)."""
    from .images import readme_lines
    return readme_lines((record or {}).get("images") or [])


def _write_readme(
    spec: FigureSpec,
    config: ProjectConfig,
    out_dir: Path,
    copied: list[str],
    record: dict | None = None,
    tables: list[dict] | None = None,
    source_data: list[dict] | None = None,
) -> None:
    """Fill the README template (the project's ``publish.readme_template`` or
    fig_atlas/templates/figure_README.md). Placeholders: number, title,
    primary_code, source_stem, panel_notes, statistics, source_data, images,
    claim_boundary, provenance, published_files; empty sections drop out."""
    sd_lines = []
    if source_data:
        sd_lines = ["## Source data",
                    f"Values each panel plots: `figure_{spec.number:02d}_source_data/` (index in its README)."]
        sd_lines += [f"- Panel {e['panel']}: `{Path(e['path']).name}` ({e['rows']:,} rows) {e['title']}".rstrip()
                     for e in source_data]
    tables = tables if tables is not None else [
        {"path": t, "source": "declared", "exists": True} for t in spec.statistics_tables]
    present = [t for t in tables if t["exists"] or t["source"] == "declared"]
    stats = []
    if present:
        stats = ["## Statistics and supplementary tables"] + [
            f"- `{t['path']}`" + ("  (from the data bundle)" if t["source"] == "bundle" else "")
            + (f"  (tests run by the build: {t.get('title') or 'statistics'})" if t["source"] == "stats_layer" else "")
            for t in present]
    missing = [t for t in tables if t["source"] == "bundle" and not t["exists"]]
    if missing:
        stats += ["", f"Not delivered: {len(missing)} statistics table(s) listed by the upstream bundle metadata "
                      "are missing from the bundle (see the provenance record)."]
    values = {
        "number": spec.number, "title": spec.title, "primary_code": spec.primary_code,
        "source_stem": spec.source_stem,
        "panel_notes": "\n".join(f"- {note}" for note in spec.panel_notes),
        "statistics": "\n".join(stats).strip(),
        "source_data": "\n".join(sd_lines),
        "images": "\n".join(_image_lines(record)),
        "claim_boundary": f"## Claim boundary\n{spec.claim_boundary}" if spec.claim_boundary else "",
        "provenance": "\n".join(_provenance_lines(record, spec)) if record else "",
        "published_files": "\n".join(f"- `{item}`" for item in copied),
    }
    template = config.readme_template or DEFAULT_TEMPLATE
    text = Template(template.read_text(encoding="utf-8")).safe_substitute(values)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def _provenance_lines(record: dict, spec: FigureSpec, max_inputs: int = 25) -> list[str]:
    """README summary of a provenance record (the full record is the JSON)."""
    git = record.get("git", {})
    commit = (git.get("commit") or "")[:7] or "no git"
    if git.get("uncommitted_code"):
        commit += f" + {git['uncommitted_code']} uncommitted code file(s)"
    cfg = record.get("config") or {}
    env = record.get("environment", {})
    pk = env.get("packages", {})
    run = record.get("run", {})
    lines = [
        "## Provenance",
        f"Recorded while the figure was built ({run.get('finished', '?')}); full record: "
        f"`figure_{spec.number:02d}.provenance.json`.",
        "",
        f"- Code: commit `{commit}`; script `{run.get('script', '?')}`",
        f"- Config: `{cfg.get('path', '?')}` (sha256 `{(cfg.get('sha256') or '')[:12]}`)",
        f"- Environment: Python {env.get('python', '?')}, matplotlib {pk.get('matplotlib', '?')}, "
        f"numpy {pk.get('numpy', '?')}, pandas {pk.get('pandas', '?')}",
        "",
        "| Input read by the build | sha256 | Upstream |",
        "|---|---|---|",
    ]
    inputs = record.get("inputs", [])
    for item in inputs[:max_inputs]:
        b = item.get("bundle") or {}
        up = b.get("app_version", "")
        lines.append(f"| `{item['path']}` | `{(item.get('sha256') or '')[:12]}` | {up} |")
    if len(inputs) > max_inputs:
        lines.append(f"| ... {len(inputs) - max_inputs} more in the JSON record | | |")
    bundles = {}
    for item in inputs:
        b = item.get("bundle") or {}
        if b.get("bundle"):
            bundles.setdefault(b["bundle"], b)
    if bundles:
        lines += ["", "| Data bundle read | Exported by | Plot type |", "|---|---|---|"]
        lines += [f"| `{k}` | {b.get('app_version', '')} | {b.get('plot_type', '')} |" for k, b in sorted(bundles.items())]
    return lines
