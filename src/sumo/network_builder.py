"""
Build a SUMO road network from the processed OSMnx graph.
"""

from __future__ import annotations

# from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NetworkBuilder:

    """
    Convert OpenStreetMap data into a SUMO network.
    """
    logger.info("Starting Network Pipeline...")

    def __init__(self) -> None:
        pass

    def build_network(self) -> None:
        """
        Build SUMO network.
        """
        pass

    def run(self) -> None:
        self.build_network()


if __name__ == "__main__":
    NetworkBuilder().run()