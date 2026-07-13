"""
===========================================================================
Module: types.py

Purpose:
    Centralized type aliases used throughout the Urban Mobility project.

Author:
    Samuel Adekunle

===========================================================================
"""

from typing import Any, TypeAlias

import networkx as nx
import geopandas as gpd
import pandas as pd


# ==========================================================================
# Graph Types
# ==========================================================================

RoadGraph: TypeAlias = nx.MultiDiGraph[Any]


# ==========================================================================
# DataFrame Types
# ==========================================================================

NodeGeoDataFrame: TypeAlias = gpd.GeoDataFrame

EdgeGeoDataFrame: TypeAlias = gpd.GeoDataFrame

DataFrame: TypeAlias = pd.DataFrame