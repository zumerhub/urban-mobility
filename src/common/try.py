import osmnx as ox
# import networkx as nx

G = ox.graph_from_place(
    "Ikeja, Lagos, Nigeria",
    network_type="drive",
    simplify=False,
)

print(type(G))
# print(isinstance(G, nx.MultiDiGraph))