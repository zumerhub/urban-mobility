"""
Common helper functions used throughout the Urban Mobility project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def ensure_directory(path: Path) -> None:
    """
    Create a directory if it does not exist.
    """

    path.mkdir(
        parents=True,
        exist_ok=True,
    )


def dataframe_memory_usage(
    dataframe: pd.DataFrame,
) -> float:
    """
    Return dataframe memory usage in MB.
    """

    return (
        dataframe.memory_usage(
            deep=True,
        ).sum()
        / 1024**2
    )


def print_header(title: str) -> None:
    """
    Print a formatted console header.
    """

    print("=" * 70)
    print(title)
    print("=" * 70)


def safe_get(
    dictionary: dict[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve a dictionary value.
    """

    return dictionary.get(key, default)