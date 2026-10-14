---
title: 0. How to read this guide
audience: researchers (no programming experience needed)
reviewed: 2026-10-13
---

# 0. How to read this guide

This guide is for **researchers** who make and manage paper figures with fig-atlas. You can read it without knowing much about programming or AI. It is less about what happens inside the tool and more about **what you do, and what you check**.

## Two ways to work

You can do the same things in two ways. This guide is written around the first, and each chapter adds a line on the second.

| Way | How | For |
|---|---|---|
| 💬 **Ask an AI** | Tell an AI assistant (Claude Code, Gemini CLI, Antigravity, opencode, ...) "make a figure from this data". The AI runs fig-atlas commands for you and shows what will change before it changes any file. | Most researchers |
| ⌨ **Commands** | Type a command such as `fa build project-name` in a terminal (command window). | When you want to run things yourself. The commands are listed in Appendix C |

No particular editor or program is needed. You can open and edit the config files in any text editor (Notepad, VS Code, ...), and you open the figures in your file browser. A few chapters add a 💡 **Tip** for a particular editor (such as VS Code), but you can skip them.

How to connect an AI assistant the first time is in [Connect AI agents](../howto/ai_agents.md). You do it only once.

## Five words to know first

| Word | Meaning | In lab terms |
|---|---|---|
| **bundle** | The data for one panel of a figure: a folder with one table file and one note saying "what figure this is". | A labelled sample |
| **project** | The unit that makes one figure (with several panels). It has three files: a config, an analysis script and a figure spec. | One experiment |
| **config** | A text file with every colour, size, axis range and layout of a figure. **This is where you change a figure.** | The protocol |
| **build** | One run that redraws the figure from its config, checks it and keeps a record. | Running the experiment |
| **provenance record** | A record, kept automatically, of which data, settings and software made a figure. | The lab notebook |

The other terms are collected in Appendix A (glossary).

## Reading order

- **If you are new**, read chapters 1 (why) and 2 (overview) first, then follow chapter 4 to make a figure. There is also a hands-on exercise in [Tutorial: first figure](../tutorials/first_figure.md).
- **To change a figure**, see chapter 6 (reading and writing the config).
- **You can also read as needed.** Each chapter makes sense on its own.

The whole guide follows one example: **a dose-response figure on its way to becoming a paper Figure**. The example data are in the repository's `examples/` folder, so anyone can do the same.

---
Next: [1. Why a tool like this](01-why.md)
