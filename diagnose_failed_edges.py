# ====================================================
import xml.etree.ElementTree as ET
from pathlib import Path

route_file = Path("data/sumo/routes.rou.xml")
root = ET.parse(route_file).getroot()

vehicles = root.findall(".//vehicle")
empty = []
mismatched = []

for v in vehicles:
    route = v.find("route")
    if route is None:
        mismatched.append(v.get("id"))
        continue
    edges = route.get("edges", "").strip()
    if not edges:
        empty.append(v.get("id"))

print(f"Total vehicles: {len(vehicles)}")
print(f"Vehicles with no <route> child: {len(mismatched)} {mismatched[:10]}")
print(f"Vehicles with empty edges='': {len(empty)} {empty[:10]}")


# # ====================================================
# # python3 - <<'PY'
# import pandas as pd

# nodes = pd.read_csv("outputs/reports/node_statistics.csv")

# print("NODE STATISTICS EXTENT")
# print("=" * 60)

# print(f"Longitude min: {nodes['x'].min()}")
# print(f"Longitude max: {nodes['x'].max()}")
# print(f"Latitude  min: {nodes['y'].min()}")
# print(f"Latitude  max: {nodes['y'].max()}")

# print("\nBounding box:")
# print(
#     (
#         nodes["x"].min(),
#         nodes["y"].min(),
#         nodes["x"].max(),
#         nodes["y"].max(),
#     )
# )
