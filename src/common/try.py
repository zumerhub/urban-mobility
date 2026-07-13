import osmnx as ox

G = ox.graph_from_place(
    "Ikeja, Lagos, Nigeria",
    network_type="drive",
    simplify=False,
)

print(type(G))


import networkx as nx

help(nx.MultiDiGraph)
def save(
    self,
    graph: nx.MultiDiGraph,
):
    
def download(self) -> nx.MultiDiGraph:
    