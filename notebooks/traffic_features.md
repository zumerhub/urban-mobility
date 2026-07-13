Good. At this point your road network foundation and graph analysis pipeline are complete:

✅ OpenStreetMap download
✅ GraphML storage
✅ Graph processing
✅ Nodes/edges extraction
✅ Network summary
✅ Degree analysis
✅ Centrality analysis
✅ Connectivity analysis
✅ Export reports

The next stage should not be YOLO yet. We need to prepare the transportation simulation layer first.

Your research architecture is:

YOLOv11
   |
   | vehicle detection
   ↓
Traffic Density Estimation
   |
   | vehicle count per road segment
   ↓
Road Network Graph (G = V,E)
   |
   | update edge weights
   ↓
ETA Prediction Model (XGBoost)
   |
   | predicted travel time
   ↓
Dynamic Routing

You have completed the Graph Layer.

Next Module: Traffic Simulation Environment

Create:

src/
│
├── traffic_simulator.py   <-- NEXT

Purpose:

Generate realistic traffic conditions on your Ikeja road network.

Because currently your graph only knows:

Edge:
-------------
Road A → Road B
Length = 250m
Speed = unknown
Travel time = unknown
Traffic = unknown

For ETA prediction we need:

Edge:
-------------
Road A → Road B

length = 250m
speed_limit = 40 km/h
vehicle_count = 35
density = 0.14 vehicles/m
traffic_state = congested
travel_time = 180 seconds
Step 1: Prepare edge features

Create:

src/
└── traffic_features.py

This module will add:

Road length

From OSM:

edge["length"]
Speed estimation

Example:

free_flow_speed = 40 km/h
Free-flow travel time

Formula:

T=
speed
distance
	​


Example:

Road length = 1000m

Speed = 40km/h

Time:

1000 / (40*1000/3600)

= 90 seconds
Traffic density

From your YOLO model later:

k=
L
N
	​


where:

N = detected vehicles
L = road segment length

Example:

vehicles = 50

road length = 500m


density = 0.1 vehicles/m
Step 2: Create simulated traffic dataset

Before YOLO data exists, we generate synthetic traffic.

Example:

data/
|
├── processed/
|
└── traffic/
      |
      └── simulated_traffic.csv

Example:

edge_id	vehicles	density	hour	travel_time
101	20	0.04	8	120
102	80	0.20	9	350
103	15	0.03	14	100

This becomes training data for XGBoost.

Step 3: Build ETA prediction model

After simulation:

src/
|
├── eta_model.py

Input:

density
hour
day
road_length
speed

Output:

predicted_travel_time

Model:

XGBoost Regression
Step 4: Dynamic Routing

Finally:

src/
|
└── routing_engine.py

Logic:

Before:

A ---- B ---- C

distance weight only

After:

A ---- B ---- C

weight = predicted ETA

NetworkX:

nx.shortest_path(
    G,
    source,
    target,
    weight="travel_time"
)
Your next immediate task

Create:

src/traffic_features.py

The first function will be:

class TrafficFeatureGenerator:

    load_graph()

    add_speed()

    calculate_free_flow_time()

    create_edge_features()

    export_features()

    run()

This will connect your static OSM road graph to the future YOLO + XGBoost ETA system.

We should build this one module at a time like we did with the graph pipeline.