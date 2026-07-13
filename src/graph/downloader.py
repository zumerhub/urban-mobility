"""
===========================================================================
Module: downloader.py

Purpose:
    Download the drivable road network of Ikeja from OpenStreetMap
    and save it as a GraphML file.

Author:
    Samuel Adekunle

Project:
    Real-Time Computer Vision and Machine Learning for Sustainable
    Urban Logistics in Lagos

===========================================================================

This module is responsible ONLY for downloading the road network.

It does NOT:
    - simplify the graph
    - project coordinates
    - analyze the graph
    - visualize the graph

Those tasks belong to other modules.
===========================================================================
"""
from __future__ import annotations
# from typing import Hashable
from pathlib import Path
# import networkx as nx
from src.types import RoadGraph
import osmnx as ox

from config import PLACE_NAME, GRAPH_FILE


class RoadNetworkDownloader:
    """
    Downloads a drivable road network from OpenStreetMap.
    """

    def __init__(
        self,
        place_name: str = PLACE_NAME,
        output_file: Path = GRAPH_FILE,
    ):
        self.place_name = place_name
        self.output_file = Path(output_file)

    # ------------------------------------------------------------------
    # Download graph
    # ------------------------------------------------------------------

    def download(self) -> RoadGraph:
    # def download(self) -> nx.MultiDiGraph[Hashable]:
        """
        Download the drivable road network.

        Returns
        -------
        networkx.MultiDiGraph
        """

        print("=" * 70)
        print("DOWNLOADING ROAD NETWORK")
        print("=" * 70)

        print(f"Location : {self.place_name}")
        print()

        graph = ox.graph_from_place(
            self.place_name,
            network_type="drive",
            simplify=False
        )

        print("Download completed successfully.")
        print()

        return graph

    # ------------------------------------------------------------------
    # Save graph
    # ------------------------------------------------------------------

    # def save(self, graph):
    #     """
    #     Save graph as GraphML.
    #     """

    #     print("=" * 70)
    #     print("SAVING GRAPH")
    #     print("=" * 70)

    #     self.output_file.parent.mkdir(
    #         parents=True,
    #         exist_ok=True,
    #     )

    #     ox.save_graphml(
    #         graph,
    #         filepath=self.output_file,
    #     )

    #     print(f"Saved to:\n{self.output_file}")
    #     print()

    def save(
        self,
        graph: RoadGraph,
    ) -> None:
        """
        Save graph as GraphML.
        """

        print("=" * 70)
        print("SAVING GRAPH")
        print("=" * 70)

        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        ox.save_graphml(
            graph,
            filepath=self.output_file,
        )

        print(f"Saved to:\n{self.output_file}\n")
    # ------------------------------------------------------------------
    # Execute complete download pipeline
    # ------------------------------------------------------------------

    def run(self) -> RoadGraph:
        """
        Download and save the road network.

        Returns
        -------
        networkx.MultiDiGraph
        """

        graph = self.download()

        self.save(graph)

        return graph


def main():
    """
    Run downloader independently.
    """

    downloader = RoadNetworkDownloader()

    downloader.run()


if __name__ == "__main__":

    try:

        main()

    except Exception as error:

        print("=" * 70)
        print("ERROR")
        print("=" * 70)

        print(error)

        print()

        print("Possible causes:")

        print("- Internet connection unavailable")
        print("- OpenStreetMap service unavailable")
        print("- Invalid place name")
        print("- Missing required Python packages")