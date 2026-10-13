---
title: Appendix B. Questions and troubleshooting
audience: researchers (no programming experience needed)
reviewed: 2026-10-14
---

# Appendix B. Questions and troubleshooting

## Figures and the config

**I changed the config but the figure is the same.**
- Check that you **saved** the config.
- Check that you rebuilt **the right project** (the project name follows `config_` in the config's file name).
- Open the PNG in the results folder again. The image viewer may be holding on to the old figure.

**I changed the config and now the build fails.**
The error message gives the line number in the config. Usually the indentation is wrong, a space is missing after `:`, or text containing `:` or `#` lacks quotes (chapter 6, "Take care when editing"). You can also show the error message to the AI and ask it to fix it.

**The two panels' text sizes differ.**
Each kind of figure has its own defaults. Set the value of the same name (`title_size` and the like) to the same number in each panel block (example in chapter 6).

**The journal asks for another width (e.g. one column of 85 mm).**
Figures are drawn to the width of the page setting (style), so make a page setting with that journal's width and minimum text size and switch to it. Journal settings for Nature and Science are included ([Switch to a journal's format](../howto/journal_presets.md)); for another journal, make one from its rules and note their source and the date you checked them ([design decision 0001](../decisions/0001-final-size-rendering.md)). Preflight then checks again against the new limits.

**Do I have to fix preflight warnings?**
No. **Errors** must be fixed; **warnings** you read and judge. If it is an intended design, leave it (chapter 8).

## Data

**I changed the raw data by mistake.**
The raw data (`raw_data/`) are not uploaded to the repository (GitHub), so undo in git cannot restore them. Get the original again from the analysis pipeline or the collaborator who sent it. If the file you get is the same as the original, its fingerprint is the same and the figure shows as "fresh". If it differs, it shows as "stale", so you know at once (chapter 10).

**The bundle check reports an error.**
A column the figure needs is not in the table; the message says which. Do not edit the table (`data.csv`): check that the note points to the table's real column name, or ask for the data to be exported again (chapter 3).

**The data changed and I do not know which figures to redraw.**
💬 "Check whether any figures are stale." You get the stale figures and the reasons (chapter 10).

## Build and environment

**(With VS Code) the new project is not in the `Ctrl+Shift+B` list.**
A project made with a command or by the AI is added to the list automatically. If you still do not see it, reload the VS Code window (`Ctrl+Shift+P` → "Reload Window"). If you do not use VS Code, you do not need this list.

**On Windows the build stops or closes without a message.**
The drawing program did not find files it needs (in the conda environment's `Library/bin`). The AI and the `fa` commands (and the VS Code build button) handle this for you. It only happens when you run an analysis script directly; if you must, first switch the environment on with `conda activate fig-atlas`.

**The build failed and I do not understand why.**
Show the last part of the build output (where it stopped) to the AI and say "explain why it failed and fix it". If it is a config problem it fixes the config; if it is a data problem it tells you what is needed.

## AI

**The AI says it does not know the fig-atlas tools.**
fig-atlas must be connected to the AI assistant (once). See [Connect AI agents](../howto/ai_agents.md). An AI that is not connected can still read the rules file (`AGENTS.md`) and run commands, but once connected, previews and viewing figures are safer and easier.

**The AI changed things without a preview.**
Tools that change files preview first by default. If it happens anyway, add "show me what will change before you change it" to your request. What was changed stays as a change to the config, so it can be undone (💬 "undo what you just changed").

---
Previous: [Appendix A. Glossary](91-glossary.md) · Next: [Appendix C. Commands on one page](93-commands.md)
