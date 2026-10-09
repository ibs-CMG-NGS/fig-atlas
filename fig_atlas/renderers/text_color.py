"""Pick a readable text colour for a given background.

Choosing white vs. dark text by the *data value* (|v| / vmax > threshold)
fails for colormaps whose two halves darken at different rates -- e.g. the
blue end of ``bwr`` is much darker than the red end at the same |v| -- so
dark text lands on dark blue and white text on mid red. Choosing by WCAG
contrast against the actual cell colour avoids that.
"""
from __future__ import annotations

import numpy as np
from matplotlib.colors import to_rgb


def relative_luminance(color) -> float:
    """WCAG relative luminance of a matplotlib colour."""
    c = np.asarray(to_rgb(color), dtype=float)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(lin @ np.array([0.2126, 0.7152, 0.0722]))


def contrast_ratio(a, b) -> float:
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable_text_color(background, light="white", dark="#111827"):
    """``light`` or ``dark``, whichever contrasts more with ``background``."""
    return light if contrast_ratio(light, background) >= contrast_ratio(dark, background) else dark
