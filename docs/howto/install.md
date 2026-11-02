# Install fig-atlas

fig-atlas is a Python package with a command-line tool, `fa`. Most people install a **release** into
the environment they use for their figures, and keep their figures in a separate *project
repository* (made with `fa init`). Only people who change fig-atlas itself need a copy of its source
(the last section).

There is no PyPI package yet, so `pip install fig-atlas` does not work. pip installs a release
straight from GitHub instead, which pins the version just as well.

## What you need

| | |
|---|---|
| Python | 3.10 or newer (the tests run on 3.12), on Windows, macOS or Linux |
| An environment | conda (Miniconda, Anaconda) or Python's own `venv`; one environment per research project is easiest to keep reproducible |
| Git | for the first install form below; the second form works without it |
| Fonts | the journal presets use Arial: Windows and macOS have it; on Linux install it (e.g. `ttf-mscorefonts-installer`), or the checks report the substituted font |

## Install a release

Pick the newest release from the [releases page](https://github.com/ibs-CMG-NGS/fig-atlas/releases);
the commands below use `v0.2.1`.

With conda:

```bash
conda create -n figures python=3.12
conda activate figures
pip install "git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1"
```

With `venv`:

```bash
python -m venv .venv
.venv\Scripts\activate                 # Windows (PowerShell or cmd)
source .venv/bin/activate              # macOS, Linux
pip install "git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1"
```

Without Git, install the release archive instead (same package):

```bash
pip install "https://github.com/ibs-CMG-NGS/fig-atlas/archive/refs/tags/v0.2.1.zip"
```

Optional parts are named in brackets: `workflow` (Snakemake), `docs` (to build this documentation
site), `test` (pytest).

```bash
pip install "fig-atlas[workflow] @ git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1"
```

## Check the installation

```bash
fa --version
fa --help
```

`fa --version` prints the version and the folder the package is imported from, for example
`fa 0.2.1 (.../site-packages)`. `fa renderers` and `fa layouts` show what it can draw and arrange, even before you make a project repository. Then make a project repository and a first figure:
[Tutorial: first figure](../tutorials/first_figure.md).

## Pin the version in your project repository

Write the release into a `requirements.txt` at the top of your project repository, so anyone
(a co-author, a reviewer, you in two years) installs the same fig-atlas:

```text
fig-atlas @ git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1
```

```bash
pip install -r requirements.txt
```

`pip freeze` shows the exact commit that was installed. Each figure's provenance record also keeps
the code it was built with.

## Upgrade

Read the [changelog](https://github.com/ibs-CMG-NGS/fig-atlas/blob/main/CHANGELOG.md) for the new
release, change the version in `requirements.txt`, and install again:

```bash
pip install --upgrade -r requirements.txt
fa --version
fa build --all --preflight
```

Rebuild and look at the figures before you send them on: a new release can change defaults, and
the checks report what moved.

## Develop fig-atlas itself

To change fig-atlas, work on a copy of its source, installed *editable* so your edits take effect
at once:

```bash
git clone https://github.com/ibs-CMG-NGS/fig-atlas
cd fig-atlas
pip install -r requirements.txt
pip install -e ".[docs,test]"
```

Or `conda env create -f environment.yml`, which makes the environment `fig-atlas` with the package
installed editable. Run the tests with `python -m pytest`.

## When something goes wrong

| Problem | Cause and fix |
|---|---|
| `fa: command not found` (`'fa' is not recognized` on Windows) | The environment is not active: `conda activate figures` (or activate the `venv`). `python -m fig_atlas` works the same as `fa`. |
| `git: command not found` during the install | Use the archive form above (`.../archive/refs/tags/v0.2.1.zip`), or install Git. |
| `fa --version` shows a folder you did not expect | Python found another copy of fig-atlas, often because you ran it inside a fig-atlas source folder. Run `fa` from your project repository. |
| On Windows, a DLL error when you run the environment's `python.exe` directly | Activate the environment first; it puts the libraries (`Library\bin`) on the path. |
| The checks report a substituted font | Install Arial (Linux), or use a preset with a font you have. |
