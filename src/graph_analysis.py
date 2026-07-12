from pathlib import Path
import json

import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import pandas as pd

from config import (
    GRAPH_FILE,
    GRAPH_SUMMARY_JSON,
    NODE_STATISTICS_CSV,
    EDGE_STATISTICS_CSV,
    ROAD_NETWORK_FIGURE,
    DEGREE_DISTRIBUTION_FIGURE,
    EDGE_LENGTH_DISTRIBUTION_FIGURE,
    CENTRALITY_FIGURE,
    LARGEST_COMPONENT_FIGURE,
)