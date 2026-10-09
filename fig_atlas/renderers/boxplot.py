"""Boxplot renderer (seaborn-based)."""

from __future__ import annotations

import seaborn as sns


from ..schema import CODE_DEFAULT, Param, Schema, uses_schema

SCHEMA = Schema("boxplot", params=[
    Param("x_col", str, "Sample", role="Column of df with the groups (x axis)"),
    Param("y_col", str, "Expression", role="Column of df with the values (y axis)"),
    Param("palette", str, "Set2", role="Seaborn palette for the boxes"),
    Param("y_min", float, None, unit="data units", role="Lower y limit (both y_min and y_max needed)"),
    Param("y_max", float, None, unit="data units", role="Upper y limit"),
    Param("labels_title", str, None, role="Panel title (none = no title)"),
    Param("labels_xlabel", str, CODE_DEFAULT, role="x-axis title (default: x_col)"),
    Param("labels_ylabel", str, CODE_DEFAULT, role="y-axis title (default: y_col)"),
    Param("title_size", float, 10, unit="pt", role="Panel title font size"),
    Param("axes_label_size", float, 8, unit="pt", role="Axis title font size"),
    Param("show_xticklabels", bool, True, role="Show x tick labels"),
    Param("show_yticklabels", bool, True, role="Show y tick labels"),
    Param("show_legend", bool, False, role="Show a legend of the groups"),
])


@uses_schema(SCHEMA)
def render_boxplot(ax, df, params):
    """Render a seaborn boxplot onto the given Axes.

    Args:
        ax:     Matplotlib Axes to draw on.
        df:     DataFrame with at least x_col and y_col columns.
        params: Dict of visual parameters sourced from config / metadata YAML.
    """
    x_col = params.get("x_col", "Sample")
    y_col = params.get("y_col", "Expression")
    palette = params.get("palette", "Set2")

    if x_col not in df.columns or y_col not in df.columns:
        ax.text(0.5, 0.5, f"Required columns not found:\n{x_col}, {y_col}",
                ha="center", va="center", fontsize=12, transform=ax.transAxes)
        return

    sns.boxplot(x=x_col, y=y_col, hue=x_col, data=df, ax=ax,
                palette=palette, legend=False)

    y_min = params.get("y_min")
    y_max = params.get("y_max")
    if y_min is not None and y_max is not None:
        ax.set_ylim(float(y_min), float(y_max))

    title = params.get("labels_title")
    if title:
        ax.set_title(title,
                     fontsize=params.get("title_size", 10),
                     fontweight="bold")

    ax.set_xlabel(params.get("labels_xlabel", x_col),
                  fontsize=params.get("axes_label_size", 8))
    ax.set_ylabel(params.get("labels_ylabel", y_col),
                  fontsize=params.get("axes_label_size", 8))

    if not params.get("show_xticklabels", True):
        ax.tick_params(axis="x", labelbottom=False)
    if not params.get("show_yticklabels", True):
        ax.tick_params(axis="y", labelleft=False)
    if not params.get("show_legend", False):
        legend = ax.get_legend()
        if legend:
            legend.remove()
