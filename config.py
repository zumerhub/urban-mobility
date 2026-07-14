"""
Project-wide constants.

These values are fixed across the Urban Mobility project.
"""

from __future__ import annotations


from pathlib import Path
# import sys

# ------------------------------------------------------------------
# Project Paths
# ------------------------------------------------------------------
PROJECT_NAME = "Urban Mobility"

PROJECT_VERSION = "1.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent
# sys.path.append(str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"

PROCESSED_DATA_DIR = DATA_DIR / "processed"

GRAPH_DIR = DATA_DIR / "graph"

OUTPUT_DIR = PROJECT_ROOT / "outputs"

FIGURE_DIR = OUTPUT_DIR / "figures"

MAP_DIR = OUTPUT_DIR / "maps"

# ------------------------------------------------------------------
# Create directories if they do not exist
# ------------------------------------------------------------------

for directory in [
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    GRAPH_DIR,
    FIGURE_DIR,
    MAP_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# OpenStreetMap Configuration
# ------------------------------------------------------------------

PLACE_NAME = "Ikeja, Lagos, Nigeria"

GRAPH_FILE = GRAPH_DIR / "ikeja_drive_network.graphml"

NODE_FILE = PROCESSED_DATA_DIR / "nodes.geojson"

EDGE_FILE = PROCESSED_DATA_DIR / "edges.geojson"

NODE_CSV = PROCESSED_DATA_DIR / "nodes.csv"

EDGE_CSV = PROCESSED_DATA_DIR / "edges.csv"

ROAD_NETWORK_IMAGE = FIGURE_DIR / "ikeja_road_network.png"


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------

# REPORT_DIR = OUTPUT_DIR / "reports"

# REPORT_DIR.mkdir(
#     parents=True,
#     exist_ok=True,
# )

# GRAPH_SUMMARY_JSON = REPORT_DIR / "graph_summary.json"

# NODE_STATISTICS_CSV = REPORT_DIR / "node_statistics.csv"

# EDGE_STATISTICS_CSV = REPORT_DIR / "edge_statistics.csv"

# GRAPH_SUMMARY_CSV = REPORT_DIR / "graph_summary.csv"

# CENTRALITY_STATISTICS_CSV = REPORT_DIR / "centrality_statistics.csv"

REPORT_DIR = OUTPUT_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_SUMMARY_JSON = REPORT_DIR / "graph_summary.json"

GRAPH_SUMMARY_CSV = REPORT_DIR / "graph_summary.csv"

NODE_STATISTICS_CSV = REPORT_DIR / "node_statistics.csv"

EDGE_STATISTICS_CSV = REPORT_DIR / "edge_statistics.csv"

CENTRALITY_STATISTICS_CSV = REPORT_DIR / "centrality_statistics.csv"

# ------------------------------------------------------------------
# Figures
# ------------------------------------------------------------------

ROAD_NETWORK_FIGURE = FIGURE_DIR / "road_network.png"

DEGREE_DISTRIBUTION_FIGURE = FIGURE_DIR / "degree_distribution.png"

EDGE_LENGTH_DISTRIBUTION_FIGURE = FIGURE_DIR / "edge_length_distribution.png"

CENTRALITY_FIGURE = FIGURE_DIR / "centrality_distribution.png"

LARGEST_COMPONENT_FIGURE = FIGURE_DIR / "largest_connected_component.png"


