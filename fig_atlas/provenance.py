"""Provenance records for figures (roadmap Phase 3P, step P.1).

Run an analysis script through the recorder instead of directly:

    python -m fig_atlas.provenance analysis/<...>/<project>_analysis.py

and every figure it saves gets a ``<stem>.provenance.json`` next to it --
without changing the script. The recorder observes, rather than trusts the
config to declare:

- inputs     every repository file the run actually opened for reading
             (Python audit hook on ``open``: pandas, numpy, yaml, PIL, open()
             alike), with sha256, size, and the bundle's upstream metadata
             (``app_version``, ``plot_type``) when the file sits in a data bundle
- code       every repository module the run imported, plus the script, with
             sha256 and whether it differs from the git HEAD commit
- config     the project config path, its sha256 and the effective (merged)
             config the run used
- environment Python, platform and key package versions
- outputs    the files written by ``savefig`` for that figure, with sha256;
             other files the run wrote are listed run-wide

``fig_atlas.publish`` copies the record next to the published figure as
``figure_NN.provenance.json`` and summarises it in the figure's README.
Hashes are cached by (path, size, mtime) in outputs/.fa_cache/hashes.json, so
large raw files are read once.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import runpy
import subprocess
import sys
from pathlib import Path

SCHEMA = "fig-atlas/provenance@1"
# Repository folders whose files count as data inputs when read.
INPUT_ROOTS = ("raw_data", "outputs", "configs", "styles", "docs", "manifests", "supplementary_tables")
SKIP_PARTS = {".git", "__pycache__", ".fa_cache", "fig-atlas", "fig-atlas-prev", "fig-atlas-next"}
# fig_atlas modules that run the pipeline but never shape a figure's content:
# left out of the code a figure depends on, so editing them doesn't mark every
# figure stale. Renderers, domain helpers, config loading and page geometry stay.
TOOLING = {f"fig_atlas/{m}.py" for m in ("__init__", "__main__", "cli", "projects", "provenance", "publish",
                                         "verify", "preflight", "print_check", "spec", "claims",
                                         "source_data", "export",
                                         "config_usage")}
PACKAGES = ("matplotlib", "numpy", "pandas", "scipy", "seaborn", "pyyaml", "pypdf", "adjustText",
            "matplotlib-venn", "squarify", "fig-atlas")


# ------------------------------------------------------------------ bundles --
def bundle_info(root: Path, p: Path) -> dict | None:
    """Upstream metadata of the data bundle (a folder with inputs/ and
    metadata/metadata.yaml) that file ``p`` belongs to: its path, the
    exporter's ``app_version``, ``plot_type``, ``figure_id`` and the
    ``statistics_tables`` it lists (repository-relative)."""
    root = root.resolve()
    for parent in p.resolve().parents:
        if parent == root:
            break
        meta = parent / "metadata" / "metadata.yaml"
        if (parent / "inputs").is_dir() and meta.is_file():
            rel = parent.relative_to(root).as_posix()
            try:
                import yaml
                m = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
            except Exception:
                return {"bundle": rel}
            keep = {k: m[k] for k in ("app_version", "plot_type", "figure_id") if k in m}
            tables = [f"{rel}/{t}" for t in (m.get("statistics_tables") or []) if isinstance(t, str)]
            return {"bundle": rel, **keep, **({"statistics_tables": tables} if tables else {})}
    return None


def statistics_tables(root: Path, record: dict | None, declared: list[str]) -> list[dict]:
    """A figure's statistics tables: the ones its FigureSpec declares plus the
    ones listed by the metadata of every data bundle the build read (looked up
    now, so records made before bundles listed tables are covered too), plus
    the test tables the build wrote (fig_atlas.stats). Each entry: path,
    source (declared | bundle | stats_layer), exists, sha256."""
    seen: dict[str, str] = {t: "declared" for t in declared}
    for e in (record or {}).get("statistics", []):
        seen.setdefault(e["path"], "stats_layer")
    for item in (record or {}).get("inputs", []):
        if not item["path"].startswith("raw_data/"):
            continue
        b = bundle_info(root, root / item["path"]) or {}
        for t in b.get("statistics_tables", []):
            seen.setdefault(t, "bundle")
    out = []
    for path, source in seen.items():
        f = root / path
        ok = f.is_file() and f.stat().st_size > 0
        out.append({"path": path, "source": source, "exists": ok,
                    "sha256": hashlib.sha256(f.read_bytes()).hexdigest() if ok else None})
    return out


# ------------------------------------------------------------------ hashing --
class HashCache:
    """sha256 of files, cached by (size, mtime_ns) across runs."""

    def __init__(self, root: Path):
        self.path = root / "outputs" / ".fa_cache" / "hashes.json"
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}
        self.dirty = False

    def sha256(self, f: Path) -> str | None:
        try:
            st = f.stat()
        except OSError:
            return None
        key = str(f)
        stamp = [st.st_size, st.st_mtime_ns]
        hit = self.data.get(key)
        if hit and hit[:2] == stamp:
            return hit[2]
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        self.data[key] = stamp + [h.hexdigest()]
        self.dirty = True
        return h.hexdigest()

    def save(self) -> None:
        if self.dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data), encoding="utf-8")


# ----------------------------------------------------------------- recorder --
class Recorder:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.reads: set[Path] = set()
        self.writes: set[Path] = set()
        self.figures: dict[Path, list[Path]] = {}   # stem -> saved files
        self.tables: dict[Path, list[dict]] = {}    # stem -> source-data tables (fig_atlas.source_data)
        self.stat_tables: dict[Path, list[dict]] = {}  # stem -> test tables (fig_atlas.stats)
        self.images: dict[Path, list[dict]] = {}       # stem -> image adjustments (fig_atlas.images)
        self._busy = False
        # A string test on the unresolved path first: resolve() costs a system
        # call, and a run opens over a thousand files (every module it imports),
        # nearly all outside the input folders (paper evidence E11).
        self._prefixes = {os.path.normcase(os.path.abspath(r)) + os.sep for r in (str(self.root), str(root))}
        self._input_roots = {os.path.normcase(r) for r in INPUT_ROOTS}
        self._skip_roots = {os.path.normcase(r) for r in SKIP_PARTS}

    def _top(self, path: str) -> str | None:
        """The first folder under the repository root of ``path`` (as spelled,
        not resolved; normcased), or None when it is not under the root."""
        s = os.path.normcase(os.path.abspath(path))
        for pre in self._prefixes:
            if s.startswith(pre):
                return s[len(pre):].split(os.sep, 1)[0]
        return None

    # Audit hooks can't be removed; ``_busy`` silences the recorder's own I/O.
    def hook(self, event: str, args) -> None:
        if event != "open" or self._busy or not args:
            return
        path = args[0]
        if isinstance(path, int) or path is None:
            return
        try:
            if self._top(os.fsdecode(path)) not in self._input_roots:
                return
            p = Path(os.fsdecode(path))
            p = (p if p.is_absolute() else Path.cwd() / p).resolve()
            rel = p.relative_to(self.root)
        except (ValueError, OSError, TypeError):
            return
        if not rel.parts or rel.parts[0] not in INPUT_ROOTS or SKIP_PARTS & set(rel.parts) or p.suffix == ".py":
            return
        mode, flags = (args[1] if len(args) > 1 else None), (args[2] if len(args) > 2 else 0)
        writing = (any(c in mode for c in "wax+") if isinstance(mode, str)
                   else bool((flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)))
        (self.writes if writing else self.reads).add(p)

    def patch_savefig(self) -> None:
        from matplotlib.figure import Figure
        original = Figure.savefig
        rec = self

        def savefig(fig, fname, *args, **kwargs):
            out = original(fig, fname, *args, **kwargs)
            if isinstance(fname, (str, os.PathLike)):
                p = Path(fname)
                fmt = kwargs.get("format")
                if not p.suffix and fmt:
                    p = p.with_suffix("." + fmt)
                p = (p if p.is_absolute() else Path.cwd() / p).resolve()
                rec.figures.setdefault(p.with_suffix(""), []).append(p)
                # Source-data tables registered since the last save belong to this figure.
                sd = sys.modules.get("fig_atlas.source_data")
                if sd is not None and sd.PENDING:
                    rec.tables.setdefault(p.with_suffix(""), []).extend(sd.take())
                # So do test tables (fig_atlas.stats).
                stt = sys.modules.get("fig_atlas.stats")
                if stt is not None and stt.PENDING:
                    rec.stat_tables.setdefault(p.with_suffix(""), []).extend(stt.take())
                # And image adjustments (fig_atlas.images).
                img = sys.modules.get("fig_atlas.images")
                if img is not None and img.PENDING:
                    rec.images.setdefault(p.with_suffix(""), []).extend(img.take())
            return out

        Figure.savefig = savefig

    # ------------------------------------------------------------- records --
    def _rel(self, p: Path) -> str:
        try:
            return p.relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def _git(self, *args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace").stdout.strip()
        except OSError:
            return ""

    def _bundle(self, p: Path) -> dict | None:
        """Upstream metadata of the data bundle a raw file belongs to."""
        return bundle_info(self.root, p)

    def build(self, script: Path, started: str) -> dict[Path, dict]:
        self._busy = True
        # Freeze the config-key usage before anything below reads the config.
        from . import config_usage
        config_usage.ENABLED = False
        usage = {k: (sorted(config_usage.READ.get(k, ())), sorted(config_usage.MISSED.get(k, ())))
                 for k in set(config_usage.READ) | set(config_usage.MISSED)}
        defaults = {k: dict(sorted(v.items())) for k, v in config_usage.DEFAULTS.items()}
        readers = {k: dict(sorted(v.items())) for k, v in config_usage.READERS.items()}
        renderer_defaults = {k.removeprefix("renderer:"): v for k, v in defaults.items() if k.startswith("renderer:")}
        cache = HashCache(self.root)
        try:
            saved = {f for fs in self.figures.values() for f in fs}
            inputs = []
            for p in sorted(self.reads - saved - self.writes):
                if not p.is_file():
                    continue
                item = {"path": self._rel(p), "sha256": cache.sha256(p), "bytes": p.stat().st_size,
                        "how": "observed"}
                b = self._bundle(p) if self._rel(p).startswith("raw_data/") else None
                if b:
                    item["bundle"] = b
                inputs.append(item)
            files = {m.__file__ for m in list(sys.modules.values()) if getattr(m, "__file__", None)}
            mods = {Path(f).resolve() for f in files
                    if f.endswith(".py") and self._top(f) not in (None, *self._skip_roots)}
            code_files = sorted({p for p in mods | {script.resolve()}
                                 if self._is_repo_code(p)})
            dirty = set(self._git("status", "--porcelain", "--", *[self._rel(p) for p in code_files]).splitlines())
            dirty_paths = {line[3:].strip().strip('"') for line in dirty if len(line) > 3}
            code = [{"path": self._rel(p), "sha256": cache.sha256(p),
                     "uncommitted": self._rel(p) in dirty_paths} for p in code_files]
            config = self._config(cache)
            if config and config.get("path"):
                own = str((self.root / config["path"]).resolve())
                if own in usage:
                    config["usage"] = {"read": usage[own][0], "missed": usage[own][1],
                                       "defaults": defaults.get(own, {}), "readers": readers.get(own, {})}
            env = self._environment()
            written = [{"path": self._rel(p), "sha256": cache.sha256(p)}
                       for p in sorted(self.writes - saved) if p.is_file()]
            run = {"started": started,
                   "finished": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                   "script": self._rel(script.resolve()),
                   "entrypoint": os.environ.get("FA_ENTRYPOINT", "python -m fig_atlas.provenance")}
            git = {"commit": self._git("rev-parse", "HEAD"),
                   "uncommitted_code": sum(c["uncommitted"] for c in code)}
            claims_mod = sys.modules.get("fig_atlas.claims")
            claims = dict(claims_mod.REGISTRY) if claims_mod else {}
            records = {}
            for stem, files in self.figures.items():
                outs = [{"path": self._rel(f), "sha256": cache.sha256(f), "bytes": f.stat().st_size}
                        for f in sorted(set(files)) if f.is_file()]
                if not outs:
                    continue
                records[stem] = {"schema": SCHEMA, "figure": {"source_stem": self._rel(stem)}, "run": run,
                                 "git": git, "inputs": inputs, "code": code, "config": config,
                                 "environment": env, "outputs": outs, "other_files_written": written,
                                 **({"renderer_defaults": renderer_defaults} if renderer_defaults else {}),
                                 **({"claims": claims} if claims else {})}
                if self.tables.get(stem):
                    from .source_data import write
                    records[stem]["source_data"] = write(self.tables[stem], Path(str(stem) + ".source_data"), self._rel)
                if self.stat_tables.get(stem):
                    from .stats import write as write_stats
                    records[stem]["statistics"] = write_stats(self.stat_tables[stem],
                                                              Path(str(stem) + ".statistics"), self._rel)
                if self.images.get(stem):
                    from .images import with_hashes
                    records[stem]["images"] = with_hashes(self.images[stem], self._rel, cache.sha256)
            return records
        finally:
            cache.save()

    def _is_repo_code(self, p: Path) -> bool:
        try:
            rel = p.relative_to(self.root)
        except ValueError:
            return False
        return p.suffix == ".py" and not (SKIP_PARTS & set(rel.parts)) and rel.as_posix() not in TOOLING

    def _config(self, cache: HashCache) -> dict | None:
        cfg_path = os.environ.get("CONFIG_PATH")
        if not cfg_path:
            return None
        p = Path(cfg_path)
        p = (p if p.is_absolute() else self.root / p).resolve()
        out = {"path": self._rel(p), "sha256": cache.sha256(p) if p.is_file() else None}
        try:
            from . import get_config
            out["effective"] = get_config(p)._raw     # after style presets were merged in
        except Exception as exc:                      # record the failure, don't break the build
            out["effective_error"] = repr(exc)
        return out

    @staticmethod
    def _environment() -> dict:
        from importlib import metadata
        pk = {}
        for name in PACKAGES:
            try:
                pk[name] = metadata.version(name)
            except metadata.PackageNotFoundError:
                pass
        try:
            from matplotlib import ft2font
            freetype = getattr(ft2font, "__freetype_version__", None)
        except Exception:
            freetype = None
        return {"python": platform.python_version(), "platform": platform.platform(terse=True),
                "packages": pk, "freetype": freetype}


def _write(records: dict[Path, dict]) -> list[Path]:
    written = []
    for stem, rec in records.items():
        out = Path(str(stem) + ".provenance.json")
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        written.append(out)
    return written


def run(script: str | Path, root: Path | None = None) -> list[Path]:
    """Run ``script`` as ``__main__`` with provenance recording; returns the
    record files written. A failing script raises and writes no records."""
    from .projects import find_root
    root = (root or find_root()).resolve()
    script = Path(script)
    script = (script if script.is_absolute() else Path.cwd() / script).resolve()
    rec = Recorder(root)
    sys.addaudithook(rec.hook)
    rec.patch_savefig()
    from . import config_usage
    config_usage.ENABLED = True                 # note which config keys the run reads (fa lint)
    config_usage.instrument_renderers()         # ... and which renderer defaults it falls back on
    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    sys.argv = [str(script)]
    sys.path.insert(0, str(script.parent))      # as `python script.py` would
    runpy.run_path(str(script), run_name="__main__")
    return _write(rec.build(script, started))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m fig_atlas.provenance <analysis_script.py>", file=sys.stderr)
        return 2
    written = run(argv[0])
    print(f"[provenance] {len(written)} figure record(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ------------------------------------------------- freshness & impact (P.3) --
def published_records(root: Path, figures_root: Path | None = None) -> list[tuple[Path, dict]]:
    """(record path, record) for every published figure record under
    ``figures_root`` (default: all of outputs/)."""
    base = figures_root or (root / "outputs")
    out = []
    for f in sorted(base.rglob("figure_*.provenance.json")):
        if f.parent.name.startswith("figure_"):          # published folder, not a source stem
            try:
                out.append((f, json.loads(f.read_text(encoding="utf-8"))))
            except (OSError, ValueError):
                continue
    return out


def check_freshness(root: Path, record: dict, cache: HashCache | None = None) -> list[str]:
    """Why a figure is stale: each recorded input, code file or config whose
    content no longer matches (empty list = fresh). Content hashes, not
    timestamps: touching a file without changing it keeps the figure fresh."""
    cache = cache or HashCache(root)
    reasons = []
    groups = [("input", record.get("inputs", [])),
              ("code", [c for c in record.get("code", []) if c["path"] not in TOOLING])]
    cfg = record.get("config") or {}
    if cfg.get("path"):
        groups.append(("config", [cfg]))
    for kind, items in groups:
        for item in items:
            p = root / item["path"]
            if not p.is_file():
                reasons.append(f"{kind} removed: {item['path']}")
            elif item.get("sha256") and cache.sha256(p) != item["sha256"]:
                reasons.append(f"{kind} changed: {item['path']}")
    return reasons


def impacted_by(root: Path, target: str | Path) -> list[dict]:
    """Published figures whose build read ``target`` (a file, or every file
    under a folder) as an input, config or code."""
    t = Path(target)
    t = (t if t.is_absolute() else Path.cwd() / t).resolve()
    try:
        rel = t.relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = Path(target).as_posix()
    hits = []
    for rec_path, rec in published_records(root):
        used = ([("input", i["path"]) for i in rec.get("inputs", [])]
                + [("code", c["path"]) for c in rec.get("code", [])]
                + ([("config", rec["config"]["path"])] if (rec.get("config") or {}).get("path") else []))
        matched = sorted({(k, p) for k, p in used if p == rel or p.startswith(rel.rstrip("/") + "/")})
        if matched:
            hits.append({"figure": rec_path.parent.relative_to(root).as_posix(),
                         "config": (rec.get("config") or {}).get("path"),
                         "via": [f"{k}: {p}" for k, p in matched]})
    return hits


# ------------------------------------------- index, lineage, record diff (P.3) --
INDEX_PATH = Path("outputs") / "provenance_index.json"


def build_index(root: Path, cache: HashCache | None = None) -> dict:
    """Every published figure record, summarised: what it is, when and from
    which commit it was built, what it read (by bundle) and whether it is
    fresh. Written to outputs/provenance_index.json; the master manifest and
    `fa lineage` read it."""
    cache = cache or HashCache(root)
    figures = {}
    for rec_path, rec in published_records(root):
        folder = rec_path.parent.relative_to(root).as_posix()
        inputs = rec.get("inputs", [])
        bundles = sorted({(i.get("bundle") or {}).get("bundle") for i in inputs} - {None})
        figures[folder] = {
            "record": rec_path.relative_to(root).as_posix(),
            "built": (rec.get("run") or {}).get("finished"),
            "commit": ((rec.get("git") or {}).get("commit") or "")[:7],
            "uncommitted_code": (rec.get("git") or {}).get("uncommitted_code", 0),
            "config": (rec.get("config") or {}).get("path"),
            "inputs": [{"path": i["path"], "sha256": i.get("sha256")} for i in inputs],
            "bundles": bundles,
            "outputs": rec.get("outputs", []),
            "statistics_tables": [t["path"] for t in rec.get("statistics_tables", []) if t.get("exists")],
            "claims": rec.get("claims") or {},
            "source_data": [e.get("published", e["path"]) for e in rec.get("source_data", [])],
            "stale_reasons": check_freshness(root, rec, cache),
        }
    cache.save()
    index = {"schema": "fig-atlas/provenance-index@1", "figures": figures}
    out = root / INDEX_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    return index


def lineage(record: dict) -> list[str]:
    """A figure's upstream tree, as text lines: outputs <- build run <- config
    and styles <- code <- inputs grouped by data bundle (with its exporter)."""
    run, git = record.get("run") or {}, record.get("git") or {}
    cfg = record.get("config") or {}
    lines = ["outputs"]
    lines += [f"  {o['path']}  sha256 {(o.get('sha256') or '')[:12]}" for o in record.get("outputs", [])]
    commit = (git.get("commit") or "")[:7] or "no git"
    if git.get("uncommitted_code"):
        commit += f" + {git['uncommitted_code']} uncommitted file(s)"
    lines += [f"<- built {run.get('finished', '?')} by {run.get('script', '?')} (commit {commit})"]
    if cfg.get("path"):
        styles = ((cfg.get("effective") or {}).get("project") or {}).get("style") or []
        styles = [styles] if isinstance(styles, str) else styles
        lines += [f"<- config {cfg['path']}  sha256 {(cfg.get('sha256') or '')[:12]}"
                  + (f"  styles: {', '.join(styles)}" if styles else "")]
    code = [c["path"] for c in record.get("code", []) if c["path"] not in TOOLING]
    if code:
        # renderers/__init__ imports every renderer, so these are the modules
        # the run imported, not necessarily the ones that drew this figure.
        renderers = [c for c in code if "/renderers/" in c]   # core and pack renderer modules
        other = [c for c in code if c not in renderers]
        lines += [f"<- code: {len(other)} file(s) + {len(renderers)} renderer module(s) imported"]
        lines += [f"     {c}" for c in other]
    groups: dict[str, list[dict]] = {}
    for i in record.get("inputs", []):
        b = (i.get("bundle") or {}).get("bundle") or ("(no bundle) " + i["path"].split("/", 1)[0])
        groups.setdefault(b, []).append(i)
    lines += [f"<- inputs: {len(record.get('inputs', []))} file(s)"]
    for b, items in sorted(groups.items()):
        meta = items[0].get("bundle") or {}
        up = ", ".join(x for x in (meta.get("app_version"), meta.get("plot_type")) if x)
        lines += [f"     {b}" + (f"  [{up}]" if up else "")]
        lines += [f"         {i['path'].rsplit('/', 1)[-1] if meta else i['path']}  sha256 {(i.get('sha256') or '')[:12]}"
                  for i in items]
    return lines


def _flatten(d, prefix: str = "") -> dict:
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    else:
        out[prefix] = d
    return out


def _changes(a: dict, b: dict) -> tuple[list[str], list[str], list[str]]:
    return (sorted(set(b) - set(a)), sorted(set(a) - set(b)),
            sorted(k for k in set(a) & set(b) if a[k] != b[k]))


def diff_records(a: dict, b: dict) -> dict:
    """What differs between two provenance records of a figure: inputs and
    code (added, removed, changed), effective config keys (old -> new),
    package versions and output hashes."""
    h = lambda items: {i["path"]: i.get("sha256") for i in items or []}   # noqa: E731
    ca, cb = a.get("config") or {}, b.get("config") or {}
    ea, eb = _flatten(ca.get("effective") or {}), _flatten(cb.get("effective") or {})
    keys = _changes(ea, eb)
    pa = (a.get("environment") or {}).get("packages", {})
    pb = (b.get("environment") or {}).get("packages", {})
    oa = {o["path"].rsplit("/", 1)[-1].rsplit(".", 1)[-1]: o.get("sha256") for o in a.get("outputs", [])}
    ob = {o["path"].rsplit("/", 1)[-1].rsplit(".", 1)[-1]: o.get("sha256") for o in b.get("outputs", [])}
    return {
        "inputs": _changes(h(a.get("inputs")), h(b.get("inputs"))),
        "code": _changes(h(c for c in a.get("code") or [] if c["path"] not in TOOLING),
                         h(c for c in b.get("code") or [] if c["path"] not in TOOLING)),
        "config_file_changed": (ca.get("path"), ca.get("sha256")) != (cb.get("path"), cb.get("sha256")),
        "config_keys": [(k, ea.get(k), eb.get(k)) for k in sorted(keys[0] + keys[1] + keys[2])],
        "packages": [(k, pa.get(k), pb.get(k)) for k in sorted(set(pa) | set(pb)) if pa.get(k) != pb.get(k)],
        "outputs_changed": sorted(k for k in set(oa) | set(ob) if oa.get(k) != ob.get(k)),
        "commits": (((a.get("git") or {}).get("commit") or "")[:7], ((b.get("git") or {}).get("commit") or "")[:7]),
        "built": ((a.get("run") or {}).get("finished"), (b.get("run") or {}).get("finished")),
    }
