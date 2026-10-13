"""The Python reference (docs/reference/api.md) covers what scripts use, and
every name on it says what it does."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

import fig_atlas

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("make_reference", ROOT / "scripts" / "make_reference.py")
make_reference = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_reference)

ENTRIES = [(e if isinstance(e, tuple) else (e, [])) for _, _, entries in make_reference.API for e in entries]
LISTED = {ref for ref, _ in ENTRIES}


@pytest.mark.parametrize("ref,members", ENTRIES, ids=[ref for ref, _ in ENTRIES])
def test_every_listed_name_is_documented(ref, members):
    obj = make_reference.api_object(ref)
    doc = make_reference.api_doc(obj)
    name = ref.partition(":")[2]
    assert doc, f"{ref} has no docstring"
    assert not doc.startswith(f"{name}("), f"{ref}: only the generated dataclass docstring"
    for m in members:
        assert make_reference.api_doc(obj.__dict__[m]), f"{ref}.{m} has no docstring"


def test_public_names_are_listed():
    missing = [n for n in fig_atlas.__all__ if f"fig_atlas:{n}" not in LISTED]
    assert not missing, f"in fig_atlas.__all__ but not in the Python reference: {missing}"


def test_template_imports_are_listed():
    """What a new project's script imports is on the page that explains it."""
    text = (ROOT / "fig_atlas" / "templates" / "project_analysis.py.tmpl").read_text(encoding="utf-8")
    used = set()
    for module, names in re.findall(r"^from (fig_atlas[\w.]*) import ([^#\n]+)", text, re.M):
        for n in (x.strip() for x in names.split(",")):
            obj = getattr(importlib.import_module(module), n)
            if isinstance(obj, type(fig_atlas)):                 # a module: its functions are listed
                assert any(r.startswith(f"{obj.__name__}:") for r in LISTED), f"nothing from {obj.__name__}"
            else:
                used.add(f"{module}:{n}")
    assert not used - LISTED, f"the template imports names the reference leaves out: {sorted(used - LISTED)}"
