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
# Raw OSM Data
# ------------------------------------------------------------------

# RAW_DATA_DIR = DATA_DIR / "raw"
RAW_OSM_FILE = RAW_DATA_DIR / "nigeria-260713.osm.pbf"



# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# SUMO
# ------------------------------------------------------------------

SUMO_DIR = DATA_DIR / "sumo"

SUMO_DIR.mkdir(parents=True, exist_ok=True,)

# ----------------- Networks -----------------------------------------


SUMO_NETWORK_FILE = SUMO_DIR / "ikeja.net.xml"

SUMO_OSM_FILE = SUMO_DIR / "ikeja.osm.xml"

SUMO_CONFIG_FILE = SUMO_DIR / "simulation.sumocfg"

# ------------------------ trip_generator ----------------------------

SUMO_ROUTE_FILE = SUMO_DIR / "routes.rou.xml"

SUMO_TRIP_FILE = SUMO_DIR / "trips.trips.xml"

SUMO_OUTPUT_FILE = SUMO_DIR / "simulation_output.xml"

# ---------------- Random Trips----------------
RANDOM_TRIPS_PERIOD = 2

SIMULATION_BEGIN = 0

SIMULATION_END = 3600

RANDOM_TRIPS_SEED = 42

# ------------------------------------------------------------------
# Study Area (Bounding Box) # Format: (minLon, minLat, maxLon, maxLat)
# ------------------------------------------------------------------
# BOUNDING_BOX = "3.30, 6.55, 3.40, 6.65"  
BOUNDING_BOX = (3.30, 6.55, 3.40, 6.65,)



# ------------------------------------------------------------------
# Travel Demand Generation
# ------------------------------------------------------------------

TRAFFIC_FEATURES_CSV = REPORT_DIR / "traffic_features.csv"

TRAVEL_DEMAND_CSV = REPORT_DIR / "travel_demand.csv"

RANDOM_SEED = 42

NUMBER_OF_VEHICLES = 1000
MORNING_PEAK_START = 7 * 3600
MORNING_PEAK_END = 9 * 3600

EVENING_PEAK_START = 16 * 3600
EVENING_PEAK_END = 19 * 3600

# PASSENGER_RATIO = 0.60 # danfo/korope 
# DELIVERY_RATIO = 0.20
# TRUCK_RATIO = 0.10
# BUS_RATIO = 0.10


# Okada, Delivery Van, Korope, Keke Napep, Truck, Car, BRT, Danfo, Molue 

# Car              40%
# Danfo            18%
# Korope           10%
# Okada            10%
# Keke              7%
# Delivery Van      6%
# Truck             4%
# BRT               3%
# Police            1%
# Ambulance         0.5%
# Fire Truck        0.5%
# ------------------------
# Total           100%

# ================================================================
# Vehicle Fleet Distribution (Ikeja, Lagos)
# ================================================================

CAR_RATIO = 0.38            # Private passenger cars

DANFO_RATIO = 0.18          # Commercial minibuses

KOROPE_RATIO = 0.10         # Mini commercial buses

BRT_RATIO = 0.03            # Bus Rapid Transit

MOLUE_RATIO = 0.02          # Long commercial buses

KEKE_RATIO = 0.07           # Tricycles

OKADA_RATIO = 0.10          # Motorcycle taxis

DELIVERY_VAN_RATIO = 0.06     # Delivery vans

TRUCK_RATIO = 0.04          # Heavy goods vehicles

POLICE_RATIO = 0.01         # Police patrol vehicles

AMBULANCE_RATIO = 0.005     # Emergency medical service

FIRE_TRUCK_RATIO = 0.005    # Fire service

