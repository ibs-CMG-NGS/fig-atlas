"""Plot families: the classification the gallery is grouped by (docs/reference/gallery.md).

A family is what a researcher looks for -- "I need a bar chart", "I need a
heatmap" -- not a field and not a package. A GO enrichment bar is a ``column``
plot and an omics heatmap is ``multivariate`` because the *shape* is generic
(ADR 0003: renderers are shapes); only a shape that means nothing outside its
field (a genome track, a motif table) is ``field``.

Where a family is declared
    In the renderer module, as a module-level ``FAMILY`` next to its
    ``SCHEMA``. A domain pack therefore declares its own and the core never
    names a pack's renderer. A plot type (a bundle's ``plot_type``) takes the
    family of the renderer that draws it (``contracts.ingest_map``), so the
    gallery has one source of truth for both lists.

    A gallery picture that is a layout variant of a renderer
    (``paired_dumbbell_4x1`` next to ``paired_dumbbell``) inherits the base
    renderer's family. A helper picture that is not a renderer at all (panel
    tags) is named in ``tests/renderers/cases.py`` (``EXTRA_FAMILIES``), next
    to its case.
"""
from __future__ import annotations

import importlib
import inspect

# (key, heading, what the family holds), in the order the gallery lists them.
# The keys are the contract: a renderer's FAMILY must be one of these.
FAMILIES: tuple[tuple[str, str, str], ...] = (
    ("column", "Column",
     "One value per category: bars, boxes, violins, histograms, dots with error bars."),
    ("xy", "XY",
     "y against x, with a fit, band or threshold: dose-response, correlation, volcano."),
    ("grouped", "Grouped",
     "Several series or items compared within one category (grouped bars, paired dumbbells)."),
    ("survival", "Survival",
     "Time to an event: Kaplan-Meier curves."),
    ("parts_of_whole", "Parts of a whole",
     "Composition: stacked bars, set diagrams, a narrowing funnel."),
    ("multivariate", "Multiple variables",
     "A matrix or many variables at once: heatmaps, dot matrices, PCA."),
    ("diagnostic", "Diagnostic",
     "How well a score separates two classes (ROC), and method agreement."),
    ("image", "Image",
     "A microscope image, blot or gel, drawn with its scale bar."),
    ("schematic", "Schematic",
     "Diagrams and layout helpers: pipelines, treatment timelines, panel tags."),
    ("field", "Field-specific",
     "A shape that means nothing outside its field: genome tracks, motif tables."),
)
FAMILY_KEYS: tuple[str, ...] = tuple(key for key, _, _ in FAMILIES)
_TITLES = {key: title for key, title, _ in FAMILIES}
_DESCRIPTIONS = {key: text for key, _, text in FAMILIES}
OTHER = ""            # names whose family is unknown (the gallery lists them last, and a test fails)


def title(key: str) -> str:
    """How the gallery heads the family (``"column"`` -> ``"Column"``)."""
    return _TITLES.get(key, "Other")


def describe(key: str) -> str:
    """One line on what the family holds, for the gallery."""
    return _DESCRIPTIONS.get(key, "")


def family_of(module) -> str:
    """The family a renderer module declares; a typo in ``FAMILY`` is an error."""
    family = getattr(module, "FAMILY", None)
    if family is None:
        return OTHER
    if family not in FAMILY_KEYS:
        raise ValueError(f"{getattr(module, '__name__', module)}: FAMILY {family!r} is not one of "
                         f"{', '.join(FAMILY_KEYS)} (fig_atlas/family.py)")
    return family


def family_of_plot(name: str) -> str:
    """The family of renderer or plot type ``name`` (``OTHER`` when unknown).

    Looked up as a renderer (or recipe) name first, then as a ``plot_type``
    through the ingest map, then as a layout variant ``<renderer>_<variant>``.
    """
    from . import contracts

    name = (name or "").removeprefix("render_")
    family = _renderer_family(name)
    if family:
        return family
    target = contracts.ingest_map().get(name)
    if target:
        module, _, _ = target.partition(":")
        return family_of(importlib.import_module(module))
    base = name
    while "_" in base:                      # paired_dumbbell_4x1 -> paired_dumbbell
        base = base.rsplit("_", 1)[0]
        family = _renderer_family(base)
        if family:
            return family
    return OTHER


def _renderer_family(name: str) -> str:
    """The family of the module that draws ``name``; ``OTHER`` if no renderer does."""
    from . import renderer_registry
    try:
        _, function = renderer_registry.find(name)
    except KeyError:
        return OTHER
    module = inspect.getmodule(function)
    return family_of(module) if module is not None else OTHER


def group(family_of_name, names) -> list[tuple[str, list[str]]]:
    """Group ``names`` into ``[(family, names), ...]`` in gallery order, empty
    families left out, anything whose family is unknown last under ``OTHER``
    (the coverage test fails on it, so this only shows a name that slipped
    through). ``family_of_name(name)`` says which family a name belongs to."""
    buckets: dict[str, list[str]] = {key: [] for key in (*FAMILY_KEYS, OTHER)}
    for name in names:
        buckets[family_of_name(name)].append(name)
    return [(key, sorted(buckets[key])) for key in (*FAMILY_KEYS, OTHER) if buckets[key]]
