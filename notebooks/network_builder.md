1. NetworkX (Graph Theory) ⭐⭐⭐⭐⭐

This is the primary reference for graph metrics.

It defines:

Degree Centrality
Closeness Centrality
Betweenness Centrality
Connectivity
Shortest paths

These are exactly the metrics you're already computing in graph_analysis.py.

Documentation:

https://networkx.org/documentation/stable/reference/algorithms/

For example, the definitions of degree_centrality(), closeness_centrality(), and betweenness_centrality() come directly from NetworkX's graph algorithms.

Network workflow

        nigeria-260713.osm.pbf
                │
                ▼
        Extract Ikeja only
                │
                ▼
        ikeja.osm.pbf
                │
                ▼
        netconvert
                │
                ▼
        ikeja.net.xml