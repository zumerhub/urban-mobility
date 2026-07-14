"""
===========================================================================
Module: traffic_features.py

Purpose:
    Generate traffic-related features from the Ikeja road network.

Pipeline Position:

    OpenStreetMap Graph
            |
            ↓
    Traffic Feature Generation
            |
            ↓
    ETA Prediction Model (XGBoost)
            |
            ↓
    Dynamic Routing

Current features:
    - road length
    - estimated speed
    - free-flow travel time
    - road attributes

Future features:
    - YOLO vehicle count
    - traffic density
    - congestion level

Author:
    Samuel Adekunle

Project:
    Real-Time Computer Vision and Machine Learning for Sustainable
    Urban Logistics in Lagos

===========================================================================
"""


from pathlib import Path

# import pandas as pd
import osmnx as ox
from typing import Any
# import geopandas as gpd

from src.types import (
    RoadGraph,
    DataFrame,
)

from config import (
    GRAPH_FILE,
    EDGE_STATISTICS_CSV,
)


class TrafficFeatureGenerator:
    """
    Generate road segment features for ETA prediction.
    """


    def __init__(
        self,
        graph_file: Path = GRAPH_FILE,
    ):

        self.graph_file = Path(graph_file)

        self.graph: RoadGraph | None  = None

        self.edge_features: DataFrame | None  = None


    # ------------------------------------------------------------------
    # Load Graph
    # ------------------------------------------------------------------

    def load_graph(self) -> RoadGraph:

        print("=" * 70)
        print("LOADING ROAD NETWORK")
        print("=" * 70)

        if not self.graph_file.exists():
            raise FileNotFoundError(
                 f"Graph not found:\n{self.graph_file}"
            )
        self.graph = ox.load_graphml(
            self.graph_file
        )


        print("Graph loaded successfully.\n")


        return self.graph



    # ------------------------------------------------------------------
    # Convert edges to dataframe
    # ------------------------------------------------------------------

    def extract_edges(self) -> DataFrame:

        print("=" * 70)
        print("EXTRACTING ROAD SEGMENTS")
        print("=" * 70)

        if self.graph is None:
            raise RuntimeError(
                "Load the graph first"
            )
            
        graph = self.graph

        _, edges = ox.graph_to_gdfs(
            # self.graph
            graph
        )


        edges = edges.reset_index()


        self.edge_features = edges


        print(
            f"Road segments extracted: {len(edges):,}"
        )

        print()


        return edges



    # ------------------------------------------------------------------
    # Estimate speed
    # ------------------------------------------------------------------

    def add_speed_feature(self) -> None:

        print("=" * 70)
        print("ADDING SPEED ESTIMATION")
        print("=" * 70)


        """
        Approximate speed values.

        Later this can be replaced with:
        - OSM maxspeed attribute
        - GPS data
        - traffic sensors
        """


        def estimate_speed(
                row: Any,
            ) -> int:

            highway = row.get(
                "highway",
                None
            )


            if isinstance(highway, list):

                highway = highway[0]


            speed_map = {

                "motorway": 80,

                "trunk": 70,

                "primary": 50,

                "secondary": 40,

                "tertiary": 35,

                "residential": 30,

                "service": 20,

            }


            return speed_map.get(
                highway,
                30
            )

        if self.edge_features is None:
            raise RuntimeError(
                "Run extract_edges() first."
            )
        
        self.edge_features["speed_kmh"] = (
            self.edge_features.apply(
                estimate_speed,
                axis=1
            )
        )


        print("Speed feature added.\n")



    # ------------------------------------------------------------------
    # Calculate free flow travel time
    # ------------------------------------------------------------------

    def calculate_free_flow_time(self) -> None:

        print("=" * 70)
        print("CALCULATING FREE FLOW TRAVEL TIME")
        print("=" * 70)

        if self.edge_features is None:
            raise RuntimeError(
                "Run extract_edges() first."
            )


        self.edge_features[
            "free_flow_time_seconds"
        ] = (

            self.edge_features["length"]

            /

            (
                self.edge_features["speed_kmh"]
                * 1000
                / 3600
            )

        )


        print(
            "Free-flow travel time calculated.\n"
        )



    # ------------------------------------------------------------------
    # Create final feature dataset
    # ------------------------------------------------------------------

    def create_features(self) -> DataFrame:

        print("=" * 70)
        print("CREATING TRAFFIC FEATURES")
        print("=" * 70)



        columns = [

            "u",
            "v",
            "key",
            "length",
            "speed_kmh",
            "free_flow_time_seconds",
            "geometry"

        ]

        if self.edge_features is None:
                raise RuntimeError(
                    "Run extract_edges() first."
                )
        self.edge_features = (
            self.edge_features[columns]
        )


        print(
            "Feature dataset created.\n"
        )


        return self.edge_features



    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_features(self) -> None:

        print("=" * 70)
        print("EXPORTING FEATURES")
        print("=" * 70)


        output_file = (
            EDGE_STATISTICS_CSV
            .parent
            /
            "traffic_features.csv"
        )

        if self.edge_features is None:
            raise RuntimeError(
                "Run create_features() first."
            )

        self.edge_features.to_csv(
            output_file,
            index=False
        )


        print(
            f"Saved : {output_file}\n"
        )



    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def run(self) -> DataFrame:


        self.load_graph()


        self.extract_edges()


        self.add_speed_feature()


        self.calculate_free_flow_time()


        self.create_features()


        self.export_features()


        print(
            "Traffic feature generation completed."
        )

        assert self.edge_features is not None
        return self.edge_features




def main() -> None:


    generator = TrafficFeatureGenerator()

    generator.run()



if __name__ == "__main__":

    main()