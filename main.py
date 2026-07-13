"""
===========================================================================
Main entry point

Urban Logistics AI
===========================================================================

Runs the project pipeline.

Current Pipeline

1. Download road network

Future Pipeline

2. Process graph 
3. Analyze graph
4. Visualize graph
5. Traffic estimation
6. ETA prediction
7. Dynamic routing
===========================================================================
"""
from config import GRAPH_FILE
from src.graph.downloader import RoadNetworkDownloader
from src.graph.graph_processor import GraphProcessor
from src.graph_analysis import GraphAnalyzer
# from src.traffic_features import TrafficFeatureGenerator
from src.graph.downloader import RoadNetworkDownloader
# from src.graph.processor import GraphProcessor
# from src.graph.analysis import GraphAnalyzer
from src.graph.traffic_features import TrafficFeatureEngineer


def main():
    if not GRAPH_FILE.exists():

        print("\nSTEP 1: DOWNLOAD ROAD NETWORK\n")
        downloader = RoadNetworkDownloader()

        downloader.run()

    else: 
        print("\nRoad network already exists.")
        print("skipping downloadd.\n")


    print("\nSTEP 2: PROCESS ROAD NETWORK\n")
    processor = GraphProcessor()
    processor.run()

    print("\nSTEP 3: GRAPH ANALYSIS\n")
    analyzer = GraphAnalyzer(
        force_recompute=False
    )
    analyzer.run()

    print("\nSTEP 4: TRAFFIC FEATURE GENERATION\n")
    traffic = TrafficFeatureGenerator()
    traffic.run()


    print("\nPipeline completed successfully.")


if __name__ == "__main__":

    main()




# from src.downloader import RoadNetworkDownloader

# def main():

#     # Download road network
#     G = download_road_network(PLACE_NAME)

#     # Simplify graph
#     G = simplify_graph(G)

#     # Convert to projected coordinate system
#     G = project_graph(G)

#     # Save graph
#     save_graph(G, GRAPH_FILE)

#     # Convert to GeoDataFrames
#     nodes, edges = convert_to_geodataframes(G)

#     # Print summary
#     graph_summary(G)

#     # Sample node
#     sample_node(G)

#     # Sample edge
#     sample_edge(G)

#     # Display first few rows
#     print("=" * 70)
#     print("First Five Nodes")
#     print("=" * 70)

#     print(nodes.head())

#     print()

#     print("=" * 70)
#     print("First Five Edges")
#     print("=" * 70)

#     print(edges.head())

#     print()

#     # Visualize graph
#     visualize_graph(G)

# if __name__ == "__main__":

#     try:

#         main()

#     except Exception as e:

#         print("=" * 70)
#         print("ERROR")
#         print("=" * 70)

#         print(e)

#         print("\nPossible causes:")

#         print("- No Internet connection")

#         print("- OpenStreetMap service unavailable")

#         print("- Incorrect package versions")

#         print("- Invalid place name")
        