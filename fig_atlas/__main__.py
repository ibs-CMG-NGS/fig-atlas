"""``python -m fig_atlas`` == ``fa`` (works without installing the package)."""
import sys

from .cli import main

sys.exit(main())
