4. Transportation Research

The idea of assigning demand based on node importance is inspired by transportation modeling rather than a single formula.

Typical concepts include:

Origin–Destination (OD) matrices
Gravity models
Accessibility analysis
Centrality-based demand estimation

Good references include:

Ortúzar & Willumsen, Modelling Transport.
Bell & Iida, Transportation Network Analysis.
Sheffi, Urban Transportation Networks.

These books explain why major intersections generate more trips than minor residential streets.


Machine Learning Papers

The later stages of your project are based on current ITS (Intelligent Transportation Systems) research:

YOLO
     ↓
Vehicle Count
     ↓
Traffic Density
     ↓
XGBoost
     ↓
ETA Prediction
     ↓
Dynamic Routing

This pattern is common in recent research on:

Traffic prediction
ETA prediction
Smart cities
Urban logistics


About the weights (0.20, 0.30, 0.50)

Those specific values are not taken from any documentation or paper. They were an example heuristic to illustrate how multiple centrality measures can be combined.

For a research paper, you should either:

Use equal weights, for example:
importance =
(degree_centrality
+ closeness_centrality
+ betweenness_centrality) / 3

This is simple, objective, and easy to justify.

Justify a weighted scheme based on transportation theory or prior literature (e.g., emphasizing betweenness because it identifies critical corridors).
Learn the weights from data later, once you have YOLO-derived traffic density and ETA data. That would make the importance score data-driven rather than heuristic.
What I'm optimizing for in your project

Based on everything we've built together, I'm trying to align the architecture with a typical research pipeline:

OSMnx
      ↓
Graph Processing
      ↓
Graph Analysis
      ↓
Traffic Feature Engineering
      ↓
Demand Generation
      ↓
Trip Generation
      ↓
SUMO Simulation
      ↓
YOLO Vehicle Detection
      ↓
Traffic Density Estimation
      ↓
XGBoost ETA Prediction
      ↓
Dynamic Routing
      ↓
Performance Evaluation