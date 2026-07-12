import osmnx as ox

G = ox.load_graphml("/home/zumerhub/codebase/urban-mobility/data/graph/ikeja_drive_network.graphml")

print("Graph attributes:")
for key, value in G.graph.items():
    print(f"{key}: {value}")