"""
===========================================================================
Module: graph_processor.py

Purpose:
    Process the downloaded OpenStreetMap road network.

Responsibilities:
    1. Load GraphML
    2. Simplify the graph
    3. Project to metric CRS
    4. Convert to GeoDataFrames
    5. Export nodes and edges

Author:
    Samuel Adekunle

Project:
    Urban Logistics AI
===========================================================================
"""

from pathlib import Path

import geopandas as gpd
import osmnx as ox
from src.types import (
    RoadGraph,
    NodeGeoDataFrame,
    EdgeGeoDataFrame,
)
from config import (
    GRAPH_FILE,
    NODE_FILE,
    EDGE_FILE,
    NODE_CSV,
    EDGE_CSV,
)


class GraphProcessor:
    """
    Process the downloaded road network.
    """

    def __init__(
        self,
        graph_file: Path = GRAPH_FILE,
    ):
        self.graph_file = Path(graph_file)

    # ------------------------------------------------------------------
    # Load Graph
    # ------------------------------------------------------------------

    # def load_graph(self):
    def load_graph(self) -> RoadGraph:

        print("=" * 70)
        print("LOADING GRAPH")
        print("=" * 70)

        graph = ox.load_graphml(self.graph_file)

        print("Graph loaded successfully.\n")

        return graph

    # ------------------------------------------------------------------
    # Simplify Graph
    # ------------------------------------------------------------------

    def simplify_graph(self, graph: RoadGraph) -> RoadGraph:

        print("=" * 70)
        print("SIMPLIFYING GRAPH")
        print("=" * 70)

        graph = ox.simplify_graph(graph)

        print("Graph simplified.\n")

        return graph

    # ------------------------------------------------------------------
    # Project Graph
    # ------------------------------------------------------------------

    def project_graph(self, graph: RoadGraph) -> RoadGraph:

        print("=" * 70)
        print("PROJECTING GRAPH")
        print("=" * 70)

        graph = ox.project_graph(graph)

        print("Projection complete.\n")

        return graph

    # ------------------------------------------------------------------
    # Convert Graph
    # ------------------------------------------------------------------

    def convert_to_geodataframes(self, graph: RoadGraph
                                 ) -> tuple[NodeGeoDataFrame, EdgeGeoDataFrame]:

        print("=" * 70)
        print("CONVERTING GRAPH")
        print("=" * 70)

        nodes, edges = ox.graph_to_gdfs(graph)

        print("Conversion completed.\n")

        return nodes, edges

    # ------------------------------------------------------------------
    # Save GeoDataFrames
    # ------------------------------------------------------------------

    def save_outputs(
        self,
        nodes: gpd.GeoDataFrame,
        edges: gpd.GeoDataFrame,
    ):

        print("=" * 70)
        print("SAVING OUTPUT FILES")
        print("=" * 70)

        nodes.to_file(
            NODE_FILE,
            driver="GeoJSON",
        )

        edges.to_file(
            EDGE_FILE,
            driver="GeoJSON",
        )

        nodes.to_csv(
            NODE_CSV,
            index=True,
        )

        edges.to_csv(
            EDGE_CSV,
            index=True,
        )

        print(f"Nodes GeoJSON : {NODE_FILE}")
        print(f"Edges GeoJSON : {EDGE_FILE}")
        print(f"Nodes CSV     : {NODE_CSV}")
        print(f"Edges CSV     : {EDGE_CSV}")
        print()

    # ------------------------------------------------------------------
    # Complete Pipeline
    # ------------------------------------------------------------------

    def run(self):

        graph = self.load_graph()

        graph = self.simplify_graph(graph)

        graph = self.project_graph(graph)

        nodes, edges = self.convert_to_geodataframes(graph)

        self.save_outputs(nodes, edges)

        return graph, nodes, edges


def main():

    processor = GraphProcessor()

    processor.run()


if __name__ == "__main__":

    main()