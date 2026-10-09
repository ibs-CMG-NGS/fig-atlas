from __future__ import annotations

from pathlib import Path

import yaml


def text_param(params: dict, key: str, default=None):
    """Look up a text/label param, distinguishing "not set" from "set empty".

    ``params.get(key) or default`` is the tempting one-liner but gets this
    wrong: "" is falsy in Python, so an explicit empty-string override in
    config (meant to hide a label/title) silently falls back to ``default``
    instead of being respected. Only an absent key or an explicit YAML
    ``null`` should fall back; ``""`` should render as nothing.
    """
    value = params.get(key)
    return default if value is None else value


def load_bundle_params(bundle_path: Path) -> dict:
    """Read ``plot_params`` from a bundle's ``metadata/metadata.yaml``.

    Returns an empty dict if the metadata file does not exist so callers can
    merge it unconditionally into their parameter chain.
    """
    meta_path = Path(bundle_path) / "metadata" / "metadata.yaml"
    if meta_path.exists():
        with meta_path.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
            params = meta.get("plot_params", {})
            # Some exporters (e.g. cmg-seqviewer) write Python's repr of None as
            # the bare word `None`, which YAML parses as the literal string
            # "None" rather than a null. Normalize those back to real None.
            return {k: (None if v == "None" else v) for k, v in params.items()}
    return {}
