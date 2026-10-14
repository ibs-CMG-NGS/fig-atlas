# How-to: switch to a journal's format

Figures are drawn at their printed size from the start. So when the journal changes, you do not redraw the figures: **you switch the journal preset and run the checks again.** A preset is a YAML file with that journal's figure widths, maximum height, font, text sizes, line widths and panel tag style, and the values preflight checks against.

## 1. The presets included

| Preset | Width | Font | Text | Panel tags | Source |
|---|---|---|---|---|---|
| `journal_generic` | 180 mm | Arial | 6–8 pt | a, b, c | The range most life-science journals accept (for drafts before a journal is chosen) |
| `journal_nature` | 183 mm (single column 89; 1.5 columns 120, 136) | Arial, else Helvetica | 5–7 pt | a, b, c · 8 pt bold | Nature's guide for final submissions |
| `journal_science` | 184 mm (single column 89; 1.5 columns 127) | Myriad, else Arial | at least 6 pt | A, B, C · 9 pt bold | Science's guide for revised manuscripts |

Each file's header gives the guide's address and the date it was checked, and values the guide does not give are marked "not stated". Journal guides change, so check the header's date and address before submitting.

## 2. Switching

In the config's `project.style`, replace the page preset with the journal preset. This one line is all.

```yaml
project:
  style: ["default", "print", "journal_nature"]   # before: page_a4_portrait_narrow
```

Then build with the checks.

```bash
fa build <project> --preflight
```

Values written in the config itself come before the preset (merge order: bundle < preset < config). So a panel whose text sizes are set in the config keeps them when the preset changes, and preflight points out where they do not meet that journal's limits.

## 3. What preflight points out

| Check | Key in the journal preset |
|---|---|
| Text too small, lines too thin | `print_check.min_font_pt`, `min_line_pt` |
| Text too large (panel tags aside) | `preflight.max_font_pt` |
| A figure not at a journal column width | `preflight.allowed_widths_mm`, `width_tol_mm` |
| A figure taller than the page | `page.content_height_mm` |
| Tag case and size | `preflight.panel_tag_case`, `panel_tag_size_pt` |
| Fonts the PDF may not use, fonts not installed | `preflight.allowed_fonts` |

To fix them, change the values pointed out in the config. Each key's comment gives its unit and which way to adjust it, and `fa param explain <project> <key>` shows where a value came from.

## 4. Good to know

- **Fonts.** A preset gives not one font but an ordered list (`rcparams: font.sans-serif`). If the first is not installed, the next is used. To use a commercial font such as Myriad, install it.
- **Maths text.** matplotlib draws exponents (10²) and subscripts (H₂O₂) in the DejaVu font by default. The journal presets set these to the same font too, with `mathtext.*` in `rcparams`. The `rcparams:` block is applied to matplotlib when the config is loaded, so you can also write it in the config itself.
- **Scripts that draw their own tags.** In figures that use `place_panel_tags`, the tags follow the preset. A script that writes the tag letters itself reads `figures.panel_tag_case` ("lower" or "upper") for their case, and gives the tags `gid=PANEL_TAG_GID` so preflight recognises them as tags.
- **Rules that are not checked.** Science, for example, asks you not to use red and green together. Preflight's colour check measures whether two colours can be told apart under simulated colour-vision deficiency, so a red-green pair that can be told apart passes. Check the guide's written rules yourself.
