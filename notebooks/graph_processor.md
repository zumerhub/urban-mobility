Raw graph
data/graph/
    ikeja_drive_network.graphml

This is the master road network.

Nodes
data/processed/nodes.geojson
data/processed/nodes.csv

Each row represents an intersection (Node).

Examples of attributes include:

Node ID
Latitude
Longitude
Geometry

In your research these are your graph vertices (V).

Edges
data/processed/edges.geojson
data/processed/edges.csv

Each row represents a road segment between two intersections.

Typical attributes include

u (start node)
v (end node)
length
geometry
road type
speed (if available)
name

These are your graph edges (E).

What this means mathematically

You now officially have

G=(V,E)

where

V = intersections
E = road segments

Exactly what you described in your ATRC methodology.

Your research pipeline now becomes
OpenStreetMap
        │
        ▼
Road Network
        │
        ▼
Graph G=(V,E)
        │
        ├─────────────┐
        │             │
        ▼             ▼
YOLOv11         Road Attributes
Vehicle Count     Length
Density           Road Class
                 Historical Data
        │
        └──────┬──────────────┐
               ▼
      Feature Engineering
               │
               ▼
        XGBoost ETA Model
               │
               ▼
Predicted Travel Time (Edge Weight)
               │
               ▼
NetworkX Shortest Path
               │
               ▼
Dynamic Route Recommendation

This is a coherent AI workflow for your paper.

We are now entering the Machine Learning part

The remaining modules naturally build on what you've completed:

src/

downloader.py                  ✅ Finished

graph_processor.py             ✅ Finished

graph_analysis.py              ← NEXT

traffic_dataset_builder.py

yolo_detector.py

density_estimator.py

feature_engineering.py

eta_model.py

dynamic_router.py

sumo_simulator.py

evaluation.py

visualization.py

I recommend the next module be graph_analysis.py

This module will answer questions such as:

- How many intersections are in Ikeja?
- How many road segments?
- Which intersections have the highest connectivity (degree)?
- Which roads are longest?
- Average edge length.
- Dead ends.
- Major junctions.
- Distribution of road types

These statistics will appear in the Study Area and Methodology sections of your paper and thesis, and they'll help validate the road network before you add computer vision and ETA prediction.