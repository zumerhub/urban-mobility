"""
===========================================================================
Module: types.py

Purpose:
    Shared type aliases used throughout the Urban Mobility project.

    This module centralizes commonly used type annotations to
    improve readability and maintainability.

Author:
    Samuel Adekunle

===========================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeAlias

import networkx as nx
import geopandas as gpd
import pandas as pd


# ==========================================================================
# Graph Types
# ==========================================================================

RoadGraph: TypeAlias = nx.MultiDiGraph[Any]


# ==========================================================================
# GeoDataFrame Types
# ==========================================================================

GeoDataFrame: TypeAlias = gpd.GeoDataFrame

NodeGeoDataFrame: TypeAlias = gpd.GeoDataFrame

EdgeGeoDataFrame: TypeAlias = gpd.GeoDataFrame

# ==========================================================================
# Pandas Types
# ==========================================================================

DataFrame: TypeAlias = pd.DataFrame

Series: TypeAlias = pd.Series

# ==========================================================================
# Path Types
# ==========================================================================

PathLike: TypeAlias = str | Path

# ==========================================================================
# JSON Types
# ==========================================================================

JsonDict: TypeAlias = dict[str, Any]

JsonList: TypeAlias = list[dict[str, Any]]

# ==========================================================================
# Graph Identifiers
# ==========================================================================

NodeId: TypeAlias = int

EdgeId: TypeAlias = tuple[int, int, int]