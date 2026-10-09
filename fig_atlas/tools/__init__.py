"""The build, check and storyline tools behind `fa` (formerly scripts/*.py).

They run inside a *project repository* -- the folder holding configs/,
analysis/, figure_specs/ (and raw_data/, outputs/) -- which is not where the
package is installed. ``project_root()`` finds it: ``$FA_ROOT`` if set, else
the nearest folder at or above the working directory that holds a project
(``fig_atlas.projects.find_root``), else the working directory.

Run one directly with ``python -m fig_atlas.tools.<name>``; `fa` does this.
"""
from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("FA_ROOT")
    if env:
        return Path(env).resolve()
    from ..projects import ProjectError, find_root
    try:
        return find_root()
    except ProjectError:
        return Path.cwd().resolve()
