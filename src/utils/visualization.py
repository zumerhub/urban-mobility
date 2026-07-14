"""
Visualization utilities.
"""

from __future__ import annotations
from pathlib import Path

from matplotlib.figure import Figure
import matplotlib.pyplot as plt


def save_figure(
    figure: Figure,
    output_file: Path,
) -> None:
    """
    Save a matplotlib figure.
    """

    figure.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)


def apply_plot_style() -> None:
    """
    Configure matplotlib defaults.
    """

    plt.style.use("ggplot")


"""
Later we'll add:

    network visualization
    centrality plots
    traffic density plots
    ETA prediction plots
    XGBoost feature importance
    SHAP plots
    confusion matrices
    SUMO visualization helpers

"""