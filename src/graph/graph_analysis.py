"""
===========================================================================
Module: graph_analysis.py

Purpose:
    Analyze the processed road network and compute graph statistics
    required for ETA prediction and dynamic routing.

Author:
    Samuel Adekunle

Project:
    Real-Time Computer Vision and Machine Learning for Sustainable
    Urban Logistics in Lagos

===========================================================================

Responsibilities
----------------
1. Load processed road network
2. Compute graph summary
3. Analyze nodes
4. Analyze edges
5. Compute centrality
6. Connectivity analysis
7. Export statistics
8. Generate visualizations

===========================================================================
"""

from __future__ import annotations
# from typing import Hashable
import json
from pathlib import Path
from typing import Dict, Any
from src.types import (
    RoadGraph,
    DataFrame,
)


import networkx as nx
import osmnx as ox
import pandas as pd
 
import geopandas as gpd
import matplotlib.pyplot as plt

from config import (
    GRAPH_FILE,
    GRAPH_SUMMARY_JSON,
    GRAPH_SUMMARY_CSV,
    NODE_STATISTICS_CSV,
    EDGE_STATISTICS_CSV,
    ROAD_NETWORK_FIGURE,
    DEGREE_DISTRIBUTION_FIGURE,
    # CENTRALITY_STATISTICS_CSV,
    # EDGE_LENGTH_DISTRIBUTION_FIGURE,
    # CENTRALITY_FIGURE,
    # LARGEST_COMPONENT_FIGURE,
)

# Constructor
class GraphAnalyzer:
    """
    Performs graph analytics on the processed road network.
    """

    def __init__(
        self,
        graph_file: Path = GRAPH_FILE,
        force_recompute: bool =False,
    ) -> None:

        self.graph_file = Path(graph_file)

        self.force_recompute = force_recompute

        self.graph: RoadGraph | None = None

        self.nodes = None

        self.edges = None

        self.summary: Dict[str, Any] = {}

        self.node_statistics: DataFrame | None = None

        self.edge_statistics: DataFrame | None  = None

        self.centrality_statistics: DataFrame | None = None

     # ==========================================================
    # Load Graph
    # ==========================================================

    def load_graph(self) -> RoadGraph:
        """
        Load the processed road network.

        Returns
        -------
        networkx.MultiDiGraph
        """

        print("=" * 70)
        print("LOADING ROAD NETWORK")
        print("=" * 70)

        if not self.graph_file.exists():    

            raise FileNotFoundError(
                f"Graph file not found:\n{self.graph_file}"
            )

        self.graph = ox.load_graphml(
            self.graph_file
        )

        print("Road network loaded successfully.\n")

        return self.graph
    

# ==========================================================
# Graph Summary
# ==========================================================

    def graph_summary(self) -> Dict[str, Any]:
        """
        Compute descriptive statistics of the road network.

        Returns
        -------
        dict
        """

        print("=" * 70)
        print("GRAPH SUMMARY")
        print("=" * 70)

        G = self.graph

        if G is None:
            raise RuntimeError(
                "Road network has not been loaded"
            )
        # undirected = G.to_undirected()
        undirected = nx.Graph(G.to_undirected())

        summary = {

            "number_of_nodes":
                G.number_of_nodes(),

            "number_of_edges":
                G.number_of_edges(),

            "is_directed":
                nx.is_directed(G),

            "density":
                nx.density(G),

            "number_of_self_loops":
                nx.number_of_selfloops(G),

            "number_of_weak_components":
                nx.number_weakly_connected_components(G),

            "number_of_strong_components":
                nx.number_strongly_connected_components(G),

            "is_weakly_connected":
                nx.is_weakly_connected(G),

            "average_degree":
                sum(dict(G.degree()).values())
                / G.number_of_nodes(),

            "average_edge_length":
                sum(
                    data.get("length", 0)
                    for _, _, data in G.edges(data=True)
                )
                / G.number_of_edges(),

            "average_clustering":
                nx.average_clustering(
                    undirected
                ),
        }

        self.summary = summary

        for key, value in summary.items():

            print(f"{key:35}: {value}")

        print()

        return summary
    

# ==========================================================
# Preview Summary
# ==========================================================

    def print_summary(self) -> None:

        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)

        for key, value in self.summary.items():

            print(f"{key:35}: {value}")

        print()


# ==========================================================
# Analyze Nodes
# ==========================================================

    def analyze_nodes(self) -> gpd.GeoDataFrame:
        """
        Convert graph nodes into a GeoDataFrame and
        compute basic node statistics.

        Returns
        -------
        GeoDataFrame
        """

        print("=" * 70)
        print("ANALYZING NODES")
        print("=" * 70)

        G = self.graph

        if G is None:
            raise RuntimeError(
                "Road network has not been loaded."
            )
        
        nodes, _ = ox.graph_to_gdfs(
            # self.graph,
            G,
            nodes=True,
            edges=True,
        )

        nodes = nodes.copy()

        nodes["degree"] = [
            # self.graph.degree(node)
            G.degree(node)
            for node in nodes.index
        ]

        nodes["in_degree"] = [
            # self.graph.in_degree(node)
            G.in_degree(node)
            for node in nodes.index
        ]

        nodes["out_degree"] = [
            # self.graph.out_degree(node)
            G.out_degree(node)
            for node in nodes.index
        ]

        self.nodes = nodes
        self.node_statistics = nodes

        print(f"Nodes analyzed : {len(nodes):,}\n")

        return nodes

    # ==========================================================
    # Analyze Edges
    # ==========================================================

    def analyze_edges(self) -> gpd.GeoDataFrame:
        """
        Convert graph edges into a GeoDataFrame.

        Returns
        -------
        GeoDataFrame
        """

        print("=" * 70)
        print("ANALYZING EDGES")
        print("=" * 70)

        G = self.graph

        if G is None:
            raise RuntimeError(
                "Road network has not been loaded."
            )
        
        __, edges = ox.graph_to_gdfs(
            # self.graph,
            G,
            nodes=True,
            edges=True,
        )

        edges = edges.copy()

        if "length" not in edges.columns:
            edges["length"] = 0.0

        self.edges = edges
        self.edge_statistics = edges

        print(f"Edges analyzed : {len(edges):,}\n")

        return edges

    # ==========================================================
    # Compute Degree Statistics
    # ==========================================================

    def compute_degree(self) -> pd.DataFrame:
        """
        Compute normalized degree values.

        Returns
        -------
        DataFrame
        """

        print("=" * 70)
        print("COMPUTING NODE DEGREES")
        print("=" * 70)

        if self.node_statistics is None:
            raise RuntimeError(
                "Run analyze_nodes() first."
            )

        max_degree = self.node_statistics["degree"].max()

        self.node_statistics["normalized_degree"] = (
            self.node_statistics["degree"] / max_degree
        )

        print("Degree computation completed.\n")

        return self.node_statistics
    
    # ==========================================================
    # Compute Centrality Measures
    # ==========================================================

    def compute_centrality(self) -> pd.DataFrame:
        """
        Compute graph centrality measures.

        Returns
        -------
        DataFrame
        """

        print("=" * 70)
        print("COMPUTING CENTRALITY")
        print("=" * 70)

        if self.node_statistics is None:
            raise RuntimeError(
                "Run analyze_nodes() first."
            )
        
        # if self.graph is None:
        #     raise RuntimeError(
        #         "Road network has not been loaded."
        #     )
        
        # G = self.graph.to_undirected()
        G = self.graph

        if G is None:
            raise RuntimeError(
                "Road network has not been loaded."
            )

        UG = G.to_undirected()

        print("Computing Degree Centrality...")
        degree = nx.degree_centrality(UG)

        print("Computing Closeness Centrality...")
        closeness = nx.closeness_centrality(UG)

        print("Computing Betweenness Centrality...")
        betweenness = nx.betweenness_centrality(
            UG,
            normalized=True,    
            k=500,
            seed=42,
        )

        self.node_statistics["degree_centrality"] = (
            self.node_statistics.index.map(degree)
        )

        self.node_statistics["closeness_centrality"] = (
            self.node_statistics.index.map(closeness)
        )

        self.node_statistics["betweenness_centrality"] = (
            self.node_statistics.index.map(betweenness)
        )

        print("Centrality computation completed.\n")

        return self.node_statistics
    
    # ==========================================================
    # Connectivity Analysis
    # ==========================================================

    def connectivity_analysis(self):

        """
        Analyze network connectivity.
        """

        print("=" * 70)
        print("CONNECTIVITY ANALYSIS")
        print("=" * 70)

        G = self.graph
        if G is None:
            raise RuntimeError(
                "Road network has not been loaded."
            )

        weak_components = list(
            nx.weakly_connected_components(G)
        )

        strong_components = list(
            nx.strongly_connected_components(G)
        )

        largest = max(
            weak_components,
            key=len,
        )

        self.summary["largest_component_nodes"] = len(
            largest
        )

        self.summary["number_of_weak_components"] = len(
            weak_components
        )

        self.summary["number_of_strong_components"] = len(
            strong_components
        )

        print(
            f"Weak Components : {len(weak_components)}"
        )

        print(
            f"Strong Components : {len(strong_components)}"
        )

        print(
            f"Largest Component : {len(largest)} nodes\n"
        )


        # ==========================================================
    # Shortest Path Statistics
    # ==========================================================

    def shortest_path_statistics(self):

        """
        Compute shortest path statistics.

        Returns
        -------
        dict
        """

        print("=" * 70)
        print("SHORTEST PATH ANALYSIS")
        print("=" * 70)

        G = self.graph

        if G is None:
            raise RuntimeError(
                "Road network has not been loaded."
            )
        # UG = G.to_undirected()

        # if not nx.is_connected(UG):

        #     largest = max(
        #         nx.connected_components(UG),
        #         key=len,
        #     )

        #     UG = UG.subgraph(largest).copy()

        # average_path = nx.average_shortest_path_length(
        #     UG,
        #     weight="length",
        # )

        # diameter = nx.diameter(UG)
        undirected_graph = G.to_undirected()

        if not nx.is_connected(undirected_graph):

            largest = max(
                nx.connected_components(undirected_graph),
                key=len,
            )

            undirected_graph = (
                undirected_graph
                .subgraph(largest)
                .copy()
            )

        average_path = nx.average_shortest_path_length(
            undirected_graph,
            weight="length",
        )

        diameter = nx.diameter(
            undirected_graph
        )

        self.summary["average_shortest_path"] = (
            average_path
        )

        self.summary["diameter"] = diameter

        print(
            f"Average Shortest Path : {average_path:.2f}"
        )

        print(
            f"Network Diameter      : {diameter}"
        )

        print()

        return self.summary


# ===========================================
#  export summary
# ===========================================
    def export_summary(self):

        print("=" * 70)
        print("EXPORTING SUMMARY")
        print("=" * 70)

        # Save JSON
        with open(GRAPH_SUMMARY_JSON, "w") as file:
            json.dump(self.summary, file, indent=4)

        # save CSV
        summary = pd.DataFrame(
            self.summary.items(),
            columns=["Metric", "Value"],
        )

        summary.to_csv(
            # SUMMARY_FILE,
            GRAPH_SUMMARY_CSV,
            index=False,
        )

        print(f"Saved : {GRAPH_SUMMARY_CSV}\n")
        print(f"CSV  saved : {GRAPH_SUMMARY_CSV}")
        print()

# =============================================================
#  Export node_statistics
# =============================================================
    def export_node_statistics(self):

        print("=" * 70)
        print("EXPORTING NODE STATISTICS")
        print("=" * 70)

        self.node_statistics.to_csv( # type: ignore
            # NODE_STATS_FILE,
            NODE_STATISTICS_CSV,
            index=True,
        )

        print(f"Saved : {NODE_STATISTICS_CSV}\n")



    # =============================================================
    #  Export edge
    # =============================================================
    def export_edge_statistics(self):

        print("=" * 70)
        print("EXPORTING EDGE STATISTICS")
        print("=" * 70)

        if self.edge_statistics is None:
            raise RuntimeError(
                "Run analyze_edges() first."
            )
        self.edge_statistics.to_csv(
            # EDGE_STATS_FILE,
            EDGE_STATISTICS_CSV,
            index=False,
        )

        print(f"Saved : {EDGE_STATISTICS_CSV}\n")

# ==================================================================
# Export visualization 
# ==================================================================
    def create_visualizations(self):

        print("=" * 70)
        print("CREATING VISUALIZATIONS")
        print("=" * 70)



        # ----------------------------
        # Degree histogram
        # ----------------------------

        plt.figure(figsize=(8,5))
        if self.node_statistics is None:
            raise RuntimeError(
                "Run analyze_nodes() first."
            )
        self.node_statistics["degree"].hist(
            bins=30,
        )

        plt.xlabel("Node Degree")

        plt.ylabel("Frequency")

        plt.title("Degree Distribution")

        plt.tight_layout()

        plt.savefig(DEGREE_DISTRIBUTION_FIGURE)

        plt.close()

        print(f"Saved : {DEGREE_DISTRIBUTION_FIGURE}")

        # ----------------------------
        # Road network
        # ----------------------------
        
        if self.graph is None:
            raise RuntimeError(
                "Road network has not been loaded."
            )
        graph = self.graph
        
        fig, _ = ox.plot_graph(
            graph,
            node_size=0,
            edge_color="black",
            edge_linewidth=0.4,
            show=False,
            close=False,
        )

        fig.savefig(
            ROAD_NETWORK_FIGURE,
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(fig)

        print(f"Saved : {ROAD_NETWORK_FIGURE}\n")

        # ==========================================================
        # Run
        # ==========================================================

    def run(self):
        print("=" * 70)
        print("GRAPH ANALYSIS PIPELINE")
        print("=" * 70)


        if (
            not self.force_recompute
            and NODE_STATISTICS_CSV.exists()
        ):

            print(
                "Existing graph analysis results found."
            )

            print(
                "Skipping graph analysis."
            )

            return

        self.load_graph()

        self.graph_summary()

        self.analyze_nodes()

        self.analyze_edges()

        self.compute_degree()

        self.compute_centrality()

        self.connectivity_analysis()

        self.shortest_path_statistics()

        self.export_summary()

        self.export_node_statistics()

        self.export_edge_statistics()

        self.create_visualizations()

        self.print_summary()

        return (
            self.graph,
            self.nodes,
            self.edges,
        )


def main():

    analyzer = GraphAnalyzer()

    analyzer.run()


if __name__ == "__main__":

    main()


"""
We'll implement it in these four complete parts:

Part 1 (≈120–150 lines): imports, class definition, constructor, load_graph(), graph_summary().  === DONE
Part 2 (≈120–150 lines): analyze_nodes(), analyze_edges(), compute_degree().
Part 3 (≈120–150 lines): compute_centrality(), connectivity_analysis(), shortest_path_statistics().
Part 4 (≈120–150 lines): export functions, visualization, run(), and integration with main.py.
"""