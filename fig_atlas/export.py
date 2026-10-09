"""Export a published figure as an RO-Crate (roadmap Phase 3P, step P.5).

``fa export <project> [--figure N]`` packages what a reader or a journal needs
to check a figure -- the figure files, its README, its Source Data and its
provenance record -- as an RO-Crate 1.1 directory (https://w3id.org/ro/crate/1.1):
a folder plus ``ro-crate-metadata.json`` describing every file and the build
that made them (a ``CreateAction``: script, commit, inputs with sha256,
outputs, time).

Raw inputs are not copied by default (``raw_data/`` is usually not public);
they are listed by repository path and hash. ``include_inputs=True`` copies
them under ``inputs/``.
"""
from __future__ import annotations

import json
import mimetypes
import shutil
from pathlib import Path

RO_CRATE = "https://w3id.org/ro/crate/1.1"
FORMATS = {".pdf": "application/pdf", ".png": "image/png", ".svg": "image/svg+xml", ".csv": "text/csv",
           ".json": "application/json", ".md": "text/markdown", ".yaml": "application/yaml", ".tsv": "text/tab-separated-values"}


def _fmt(p: Path) -> str:
    return FORMATS.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"


def _file(rel: str, path: Path, **extra) -> dict:
    import hashlib
    return {"@id": rel, "@type": "File", "name": Path(rel).name, "encodingFormat": _fmt(path),
            "contentSize": str(path.stat().st_size), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **extra}


def export_figure(root: Path, folder: Path, out: Path, include_inputs: bool = False) -> Path:
    """Write an RO-Crate for the published figure in ``folder`` to ``out``."""
    number = folder.name.split("_")[1]
    rec_path = folder / f"figure_{number}.provenance.json"
    if not rec_path.is_file():
        raise FileNotFoundError(f"{folder}: no provenance record; build the figure with `fa build`")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    parts, graph = [], []
    for f in sorted(folder.iterdir()):
        if f.is_file():
            shutil.copy2(f, out / f.name)
            desc = {"README.md": "Figure legend, claim boundary and provenance summary",
                    f"figure_{number}.provenance.json": "Provenance record: inputs, code, config, environment, outputs"}
            graph.append(_file(f.name, out / f.name, **({"description": desc[f.name]} if f.name in desc else {})))
            parts.append(f.name)
    sd = folder / f"figure_{number}_source_data"
    if sd.is_dir():
        shutil.copytree(sd, out / sd.name)
        sd_files = []
        for e in rec.get("source_data", []):
            rel = f"{sd.name}/{Path(e['path']).name}"
            graph.append(_file(rel, out / rel, description=f"Source data, panel {e['panel']}: {e['title']}".rstrip(": ")))
            sd_files.append({"@id": rel})
        graph.append({"@id": f"{sd.name}/", "@type": "Dataset", "name": "Source data",
                      "description": "Values each panel plots, one CSV per table", "hasPart": sd_files})
        parts.append(f"{sd.name}/")

    run, git = rec.get("run") or {}, rec.get("git") or {}
    inputs = []
    for i in rec.get("inputs", []):
        src = root / i["path"]
        if include_inputs and src.is_file():
            rel = f"inputs/{i['path']}"
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out / rel)
            ent = _file(rel, out / rel, description=f"Input read by the build (repository path {i['path']})")
            parts.append(rel)
        else:
            ent = {"@id": f"#input:{i['path']}", "@type": "File", "name": i["path"], "sha256": i.get("sha256"),
                   "description": "Input read by the build; not included (repository path)"}
        b = i.get("bundle") or {}
        if b.get("app_version"):
            ent["description"] += f"; data bundle exported by {b['app_version']}"
        graph.append(ent)
        inputs.append({"@id": ent["@id"]})

    script = run.get("script", "")
    code_id = f"#code:{script}"
    code_sha = next((c.get("sha256") for c in rec.get("code", []) if c["path"] == script), None)
    graph.append({"@id": code_id, "@type": ["File", "SoftwareSourceCode"], "name": script, "programmingLanguage": "Python",
                  "version": git.get("commit") or None, "sha256": code_sha,
                  "description": "Analysis script (repository path), at the recorded commit"})
    cfg = rec.get("config") or {}
    if cfg.get("path"):
        graph.append({"@id": f"#config:{cfg['path']}", "@type": "File", "name": cfg["path"], "sha256": cfg.get("sha256"),
                      "description": "Project config (repository path); effective values in the provenance record"})
    env = rec.get("environment") or {}
    pk = env.get("packages", {})
    graph.append({"@id": "#build", "@type": "CreateAction", "name": f"fa build ({run.get('entrypoint', '')})".strip(),
                  "startTime": run.get("started"), "endTime": run.get("finished"),
                  "instrument": {"@id": code_id}, "object": inputs,
                  "result": [{"@id": p} for p in parts if p.startswith("figure_") and not p.endswith(("/", ".json"))],
                  "description": f"Python {env.get('python', '?')}, " + ", ".join(f"{k} {v}" for k, v in sorted(pk.items()))})

    readme = (folder / "README.md").read_text(encoding="utf-8").splitlines() if (folder / "README.md").is_file() else []
    title = readme[0].lstrip("# ").strip() if readme else folder.name
    root_entity = {"@id": "./", "@type": "Dataset", "name": title, "datePublished": run.get("finished"),
                   "description": "A published figure with its source data and provenance (fig-atlas export)",
                   "hasPart": [{"@id": p} for p in parts], "mentions": [{"@id": "#build"}]}
    meta = {"@context": f"{RO_CRATE}/context", "@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "conformsTo": {"@id": RO_CRATE}, "about": {"@id": "./"}},
        root_entity, *graph]}
    (out / "ro-crate-metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return out
