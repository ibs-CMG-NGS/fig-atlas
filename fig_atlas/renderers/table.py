"""A summary table as text: rows and columns drawn at print size, in the
publication convention (three horizontal rules, no vertical rules, no fills).

What makes a table look professional is not the layout but the per-column
treatment -- alignment and number format -- so those come first: without them
one table prints ``0.4871234`` next to ``41``. ``column_format`` takes a Python
format spec per column (``".3f"``, ``",.0f"``, ``".2e"``), ``column_align``
overrides the default (numbers right, text left), and ``column_width`` overrides
the width measured from the content.

This draws a table; it is not a route for submitting one. Most journals take
tables as editable text (Word/Excel), where a rendered image cannot be
copyedited, typeset or read by a screen reader. Use this for a compendium page,
a talk or a poster, and keep the CSV for submission.

Long tables are not this shape: a table of thousands of rows fits no page. Rows
past ``max_rows`` are dropped and a note says how many (``truncation_note``).

Data: any table. ``columns`` picks which of its columns to print, in order;
by default every column, in the order the data has them.
Returns the rows it drew, formatted as printed, ready for
``fig_atlas.source_data.add``.
"""
from __future__ import annotations

FAMILY = "table"    # gallery family (fig_atlas/family.py): the shape this module draws

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.font_manager import FontProperties

from ..schema import Param, Schema, StyleRef, uses_schema

SCHEMA = Schema("table", params=[
    # [Columns] Which columns are printed, in which order, under which heading.
    Param("columns", list, None,
          role="Columns to print, in order (default: every column of the data, in its order)"),
    Param("column_labels", dict, {}, open_keys=True,
          role="Heading text per column (default: the column name as it is in the data)"),
    Param("column_align", dict, {}, open_keys=True,
          role="Alignment per column: 'left', 'right' or 'center' (default: numeric columns right, the rest left)"),
    Param("column_format", dict, {}, open_keys=True,
          role="Python format spec per column, applied to each value ('.3f', ',.0f', '.2e'; default: str())",
          tune="set it on every numeric column, or the table prints raw float repr next to short integers"),
    Param("column_width", dict, {}, open_keys=True, unit="[0-1] fraction of the table width",
          role="Width per column (default: measured from the widest cell and the heading)"),
    Param("column_groups", list, None,
          role="Spanning headings above the columns, as [{'label': str, 'columns': [names]}] (default: none)"),
    Param("na_text", str, StyleRef("table.na_text", "--"), role="What a missing value prints as"),
    # [Rows]
    Param("max_rows", int, 40, unit="rows", range=(1, None),
          role="Rows printed at most; the rest are dropped and counted in the truncation note",
          tune="a table of more than about 40 rows stops being readable on a page -- keep the full table as CSV"),
    Param("truncation_note", str, "... and {n} more rows (full table in the source data)",
          role="Note printed under a truncated table; {n} is the number of rows dropped"),
    Param("row_stripe", bool, StyleRef("table.row_stripe", False),
          role="Shade every other row (off in the publication convention; on for a screen table)"),
    Param("row_stripe_color", "color", StyleRef("table.row_stripe_color", "#f8fafc"), unit="hex color",
          role="Shading colour of the striped rows"),
    # [Rules] The three horizontal rules of a classic table; no vertical rules.
    Param("rule_color", "color", StyleRef("table.rule_color", "#111827"), unit="hex color",
          role="Colour of the horizontal rules"),
    Param("rule_top_width", float, StyleRef("table.rule_top_width", 1.0), unit="pt", range=(0, None),
          role="Rule above the headings (0 hides it)"),
    Param("rule_header_width", float, StyleRef("table.rule_header_width", 0.6), unit="pt", range=(0, None),
          role="Rule between the headings and the first row (0 hides it)"),
    Param("rule_bottom_width", float, StyleRef("table.rule_bottom_width", 1.0), unit="pt", range=(0, None),
          role="Rule under the last row (0 hides it)"),
    Param("rule_group_width", float, StyleRef("table.rule_group_width", 0.5), unit="pt", range=(0, None),
          role="Rule under a spanning heading, over its own columns only (0 hides it)"),
    # [Typography]
    Param("font_family", str, None, role="Font of the table text (default: the figure's font)"),
    Param("header_size", float, StyleRef("table.header_size", 6.0), unit="pt", range=(0, None),
          role="Heading font size", tune="lower if a heading wraps to three lines"),
    Param("cell_size", float, StyleRef("table.cell_size", 5.5), unit="pt", range=(0, None),
          role="Cell font size", tune="the print floor is 5.0 pt (print_check.min_font_pt)"),
    Param("header_weight", str, StyleRef("table.header_weight", "bold"), unit="matplotlib font weight",
          role="Heading weight ('bold', 'normal')"),
    Param("header_color", "color", StyleRef("table.header_color", "#111827"), unit="hex color",
          role="Heading text colour"),
    Param("cell_color", "color", StyleRef("table.cell_color", "#1f2937"), unit="hex color", role="Cell text colour"),
    # [Spacing]
    Param("col_gap", float, StyleRef("table.col_gap", 6.0), unit="pt",
          role="Gap between columns -- what separates them, since there are no vertical rules",
          tune="raise if the columns read as one block"),
    Param("row_pad", float, StyleRef("table.row_pad", 1.6), unit="pt", range=(0, None),
          role="Space above and below the text of a row",
          tune="raise to open the rows up; lower to fit more on the page"),
    Param("header_pad", float, StyleRef("table.header_pad", 2.4), unit="pt", range=(0, None),
          role="Space between the heading rule and the first row"),
    Param("wrap", bool, StyleRef("table.wrap", True),
          role="Wrap cell text that is wider than its column instead of letting it run on"),
    Param("max_lines", int, StyleRef("table.max_lines", 3), unit="lines", range=(1, None),
          role="Lines a wrapped cell may take at most", tune="raise for a notes column"),
    Param("truncation_mark", str, StyleRef("table.truncation_mark", "…"),
          role="Appended to the last line of a cell cut at max_lines, so a cut never passes as the whole text"),
    # [Labels]
    Param("title", str, None, role="Table title, above the top rule"),
    Param("title_size", float, StyleRef("table.title_size", 6.5), unit="pt", range=(0, None),
          role="Title font size"),
    Param("title_pad", float, StyleRef("table.title_pad", 3.0), unit="pt", range=(0, None),
          role="Gap between the title and the top rule"),
    Param("footnotes", list, None, role="Notes printed under the bottom rule, one per line"),
    Param("footnote_size", float, StyleRef("table.footnote_size", 5.0), unit="pt", range=(0, None),
          role="Footnote font size"),
    Param("footnote_color", "color", StyleRef("table.footnote_color", "#4b5563"), unit="hex color",
          role="Footnote text colour"),
    Param("footnote_pad", float, StyleRef("table.footnote_pad", 2.4), unit="pt", range=(0, None),
          role="Gap between the bottom rule and the first note"),
])


def _format_cell(value, spec: str | None, na_text: str) -> str:
    """One cell as printed: ``spec`` is a Python format spec, or None for str()."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return na_text
    try:
        if pd.isna(value):
            return na_text
    except (TypeError, ValueError):
        pass
    if not spec:
        return str(value)
    try:
        return format(value, spec)
    except (TypeError, ValueError):
        return str(value)


def _text_width_pt(text: str, font: FontProperties, fig) -> float:
    """Width of ``text`` in points, measured with the figure's own renderer."""
    if not text:
        return 0.0
    renderer = fig.canvas.get_renderer()
    w_px = renderer.get_text_width_height_descent(text, font, ismath=False)[0]
    return w_px * 72.0 / fig.dpi


# A column is often exactly as wide as its longest word: the width allocation
# gives it that word's measured width, and nothing more when the column asks for
# nothing more. Comparing those two equal numbers is a coin flip -- text extents
# differ in the last decimal between FreeType builds, so the same table broke a
# word on one machine and not on another, which moved every row below it. A fit
# is therefore judged with this much slack, far below a printed hairline.
_FIT_TOLERANCE_PT = 0.01


def _wrap(text: str, max_w_pt: float, font: FontProperties, fig, max_lines: int, mark: str = "") -> list[str]:
    """``text`` broken to lines that fit ``max_w_pt``, at most ``max_lines``. When
    text is left over, the last line ends in ``mark`` -- a cut cell must say so."""
    fits = max_w_pt + _FIT_TOLERANCE_PT

    def pieces(word: str) -> list[str]:
        """A word wider than the column, broken between characters: ugly, but it
        never runs into the next column, which a reader would misread."""
        if _text_width_pt(word, font, fig) <= fits:
            return [word]
        out, cur = [], ""
        for ch in word:
            if cur and _text_width_pt(cur + ch, font, fig) > fits:
                out.append(cur)
                cur = ch
            else:
                cur += ch
        return [*out, cur]

    words = [p for w in str(text).split() for p in pieces(w)]
    if not words:
        return [""]
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}" if cur else word
        if cur and _text_width_pt(trial, font, fig) > fits:
            lines.append(cur)
            cur = word
            if len(lines) == max_lines:
                break
        else:
            cur = trial
    else:
        lines.append(cur)
        return lines
    last = lines[-1].split()                 # cut: drop words until the mark fits
    while len(last) > 1 and _text_width_pt(" ".join(last) + mark, font, fig) > max_w_pt:
        last.pop()
    lines[-1] = " ".join(last) + mark
    return lines


@uses_schema(SCHEMA)
def render_table(ax: plt.Axes, df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Draw ``df`` as a classic table on ``ax``; returns the printed rows.

    params: columns, column_labels, column_align, column_format, column_width,
      column_groups, na_text ('--'), max_rows (40), truncation_note, row_stripe (False),
      rule_color ('#111827'), rule_top_width (1.0), rule_header_width (0.6),
      rule_bottom_width (1.0), header_size (6.0), cell_size (5.5), header_weight ('bold'),
      col_gap (6.0 pt), row_pad (1.6 pt), wrap (True), max_lines (3),
      title, title_size (6.5), footnotes, footnote_size (5.0)
    """
    cols = list(params.get("columns") or df.columns)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"table: columns not in the data: {missing}")

    na_text = params.get("na_text", "--")
    fmt = params.get("column_format", {}) or {}
    labels = params.get("column_labels", {}) or {}
    align_cfg = params.get("column_align", {}) or {}

    max_rows = int(params.get("max_rows", 40))
    n_dropped = max(0, len(df) - max_rows)
    body = df.iloc[:max_rows]

    printed = pd.DataFrame({c: [_format_cell(v, fmt.get(c), na_text) for v in body[c]] for c in cols})
    heads = [str(labels.get(c, c)) for c in cols]
    align = {c: align_cfg.get(c, "right" if pd.api.types.is_numeric_dtype(df[c]) else "left") for c in cols}

    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig = ax.figure

    family = params.get("font_family")
    f_head = FontProperties(size=float(params.get("header_size", 6.0)),
                            weight=params.get("header_weight", "bold"),
                            **({"family": family} if family else {}))
    f_cell = FontProperties(size=float(params.get("cell_size", 5.5)), **({"family": family} if family else {}))

    # Axes geometry in points, so widths and gaps keep their stated unit.
    bbox = ax.get_window_extent()
    ax_w_pt = bbox.width * 72.0 / fig.dpi
    ax_h_pt = bbox.height * 72.0 / fig.dpi
    if ax_w_pt <= 0 or ax_h_pt <= 0:          # an axes with no extent (not drawn yet)
        return printed
    col_gap = float(params.get("col_gap", 6.0))

    # [Column widths] The usual table layout: each column gets at least its longest
    # word (a word cannot wrap, so anything narrower runs into the next column) and
    # at most its unwrapped text; the room between the two is shared in proportion
    # to what each column still wants. column_width overrides a column outright.
    given = params.get("column_width", {}) or {}
    natural, minimum = [], []
    for c, head in zip(cols, heads):
        nat = _text_width_pt(head, f_head, fig)
        low = max((_text_width_pt(w, f_head, fig) for w in head.split()), default=0.0)
        for cell in printed[c]:
            nat = max(nat, _text_width_pt(cell, f_cell, fig))
            low = max([low, *(_text_width_pt(w, f_cell, fig) for w in str(cell).split())])
        natural.append(nat)
        minimum.append(low)
    avail = ax_w_pt - col_gap * (len(cols) - 1)
    fixed = {i: float(given[c]) * avail for i, c in enumerate(cols) if c in given}
    free = [i for i in range(len(cols)) if i not in fixed]
    room = avail - sum(fixed.values())
    nat_sum = sum(natural[i] for i in free)
    min_sum = sum(minimum[i] for i in free)
    widths = [0.0] * len(cols)
    for i, w in fixed.items():
        widths[i] = w
    if nat_sum <= room:                        # everything fits unwrapped: spread the spare room
        for i in free:
            widths[i] = natural[i] / (nat_sum or 1.0) * room
    elif min_sum < room:                       # wrap: words kept whole, the rest shared by need
        want = nat_sum - min_sum
        for i in free:
            widths[i] = minimum[i] + (natural[i] - minimum[i]) / (want or 1.0) * (room - min_sum)
    else:                                      # even the longest words do not fit: shrink them alike
        for i in free:
            widths[i] = minimum[i] / (min_sum or 1.0) * room
    over = sum(widths) - avail
    if over > 0:                               # fixed widths asked for more than there is
        widths = [w - over * (w / sum(widths)) for w in widths]

    # [Cell lines] wrapping decides each row's height.
    wrap_on = bool(params.get("wrap", True))
    max_lines = int(params.get("max_lines", 3))
    mark = str(params.get("truncation_mark", "…"))
    head_lines = [_wrap(h, w, f_head, fig, max_lines, mark) if wrap_on else [h] for h, w in zip(heads, widths)]
    row_lines: list[list[list[str]]] = []
    for _, row in printed.iterrows():
        row_lines.append([_wrap(row[c], w, f_cell, fig, max_lines, mark) if wrap_on else [str(row[c])]
                          for c, w in zip(cols, widths)])

    head_size, cell_size = float(params.get("header_size", 6.0)), float(params.get("cell_size", 5.5))
    row_pad = float(params.get("row_pad", 1.6))
    line_h_head, line_h_cell = head_size * 1.25, cell_size * 1.25

    def to_y(y_pt: float) -> float:
        return 1.0 - y_pt / ax_h_pt

    def to_x(x_pt: float) -> float:
        return x_pt / ax_w_pt

    x_left = [0.0]
    for w in widths[:-1]:
        x_left.append(x_left[-1] + w + col_gap)

    rule_color = params.get("rule_color", "#111827")
    y = 0.0

    if params.get("title"):
        t_size = float(params.get("title_size", 6.5))
        f_title = FontProperties(size=t_size, weight="bold", **({"family": family} if family else {}))
        # Wrapped to the table width, like every cell: an unwrapped title runs off
        # the page. None of it is ever cut -- it is the author's text, not data --
        # so the line cap is set where it cannot bite (a line holds >= 1 character).
        for k, line in enumerate(_wrap(params["title"], ax_w_pt, f_title, fig, len(str(params["title"])) or 1)):
            y += t_size if k == 0 else t_size * 1.25
            ax.text(0, to_y(y), line, fontproperties=f_title,
                    color=params.get("header_color", "#111827"), va="baseline", ha="left")
        y += float(params.get("title_pad", 3.0))

    top_w = float(params.get("rule_top_width", 1.0))
    if top_w > 0:
        ax.plot([0, 1], [to_y(y)] * 2, color=rule_color, lw=top_w, solid_capstyle="butt")
    y += row_pad

    # [Spanning headings] under the top rule, each over its own columns only -- the
    # convention's order (toprule, spanning row, its partial rule, then the headings).
    groups = params.get("column_groups") or []
    if groups:
        for g in groups:
            members = [c for c in (g.get("columns") or []) if c in cols]
            if not members:
                continue
            i0, i1 = cols.index(members[0]), cols.index(members[-1])
            x0, x1 = x_left[i0], x_left[i1] + widths[i1]
            ax.text(to_x((x0 + x1) / 2), to_y(y + head_size), str(g.get("label", "")), fontproperties=f_head,
                    color=params.get("header_color", "#111827"), va="baseline", ha="center")
            gw = float(params.get("rule_group_width", 0.5))
            if gw > 0:
                ax.plot([to_x(x0), to_x(x1)], [to_y(y + head_size + row_pad)] * 2, color=rule_color, lw=gw,
                        solid_capstyle="butt")
        y += head_size + row_pad * 2

    def draw_cells(lines_per_col, font, color, y_top: float) -> float:
        """One row of cells; returns the y (pt from the axes top) below it."""
        n_lines = max(len(l) for l in lines_per_col)
        line_h = line_h_head if font is f_head else line_h_cell
        for i, lines in enumerate(lines_per_col):
            how = align[cols[i]]
            x = x_left[i] if how == "left" else (x_left[i] + widths[i] if how == "right"
                                                 else x_left[i] + widths[i] / 2)
            ha = {"left": "left", "right": "right", "center": "center"}[how]
            for k, line in enumerate(lines):
                ax.text(to_x(x), to_y(y_top + line_h * (k + 1)), line, fontproperties=font, color=color,
                        va="baseline", ha=ha)
        return y_top + line_h * n_lines

    y = draw_cells(head_lines, f_head, params.get("header_color", "#111827"), y)
    y += row_pad
    hdr_w = float(params.get("rule_header_width", 0.6))
    if hdr_w > 0:
        ax.plot([0, 1], [to_y(y)] * 2, color=rule_color, lw=hdr_w, solid_capstyle="butt")
    y += float(params.get("header_pad", 2.4))

    stripe = bool(params.get("row_stripe", False))
    cell_color = params.get("cell_color", "#1f2937")
    for r, lines_per_col in enumerate(row_lines):
        y_row_top = y
        y = draw_cells(lines_per_col, f_cell, cell_color, y)
        if stripe and r % 2 == 1:
            ax.axhspan(to_y(y + row_pad), to_y(y_row_top - row_pad),
                       color=params.get("row_stripe_color", "#f8fafc"), zorder=0)
        y += row_pad * 2

    bot_w = float(params.get("rule_bottom_width", 1.0))
    if bot_w > 0:
        ax.plot([0, 1], [to_y(y)] * 2, color=rule_color, lw=bot_w, solid_capstyle="butt")

    notes = list(params.get("footnotes") or [])
    if n_dropped:
        notes.insert(0, str(params.get("truncation_note",
                                       "... and {n} more rows (full table in the source data)")).format(n=n_dropped))
    if notes:
        f_note = FontProperties(size=float(params.get("footnote_size", 5.0)), **({"family": family} if family else {}))
        y += float(params.get("footnote_pad", 2.4))
        n_size = float(params.get("footnote_size", 5.0))
        for note in notes:
            # Wrapped like the title, and for the same reason; never cut.
            for line in _wrap(note, ax_w_pt, f_note, fig, len(str(note)) or 1):
                y += n_size * 1.25
                ax.text(0, to_y(y), line, fontproperties=f_note, color=params.get("footnote_color", "#4b5563"),
                        va="baseline", ha="left")
    # The height the table actually took, so a caller that lays out pages (the
    # compendium) can size its axes to the content instead of guessing.
    printed.attrs["height_pt"] = y
    return printed
