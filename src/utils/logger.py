"""
Centralized project logger.
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a configured logger.
    """

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)-8s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%H:%M:%S",
    )

    return logging.getLogger(name)