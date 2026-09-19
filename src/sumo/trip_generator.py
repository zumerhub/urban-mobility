# """
# Purpose: Convert demand into SUMO routes.

# TripGenerator
# │
# ├── __init__()
# ├── load_network()
# ├── load_travel_demand()
# ├── create_routes()
# ├── write_routes_xml()
# ├── write_vehicle_types()
# ├── verify_outputs()
# └── run()

# Input

# travel_demand.csv

# ikeja.net.xml

# Output

# routes.rou.xml
# """


# from src.utils.logger import get_logger
# logger = get_logger(__name__)

# ===============================================================================


"""
Trip Generator
==============

Purpose: Convert demand into SUMO routes.

TripGenerator
│
├── __init__()
├── load_network()
├── load_travel_demand()
├── load_node_statistics()
├── create_routes()
├── write_vehicle_types()
├── write_routes_xml()
├── verify_outputs()
└── run()

Input
-----
travel_demand.csv
ikeja.net.xml
node_statistics.csv

Output
------
routes.rou.xml

Notes
-----
origin_node/destination_node in travel_demand.csv are arbitrary OSM
node IDs, not SUMO junction IDs. netconvert only preserves OSM nodes
that become real junctions (intersections/endpoints); most OSM nodes
along a way are dropped or merged during network building. Looking
these IDs up with network.getNode() therefore fails for the large
majority of records (KeyError), so endpoints must instead be resolved
by geographic snapping: OSM lon/lat (from node_statistics.csv) ->
SUMO X/Y -> nearest vehicle-compatible SUMO edge, same approach used
by RouteGenerator.

What TripGenerator does differently from RouteGenerator is the
routing step itself: instead of writing a trips.trips.xml and
shelling out to the external duarouter binary, it computes each
route in-process with sumolib's built-in shortest-path search
(network.getShortestPath), and writes routes.rou.xml directly.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, cast

import sumolib  # type: ignore

from config import (
    EDGE_SEARCH_RADIUS,
    NODE_STATISTICS_CSV,
    SUMO_NETWORK_FILE,
    SUMO_ROUTE_FILE,
    TRAVEL_DEMAND_CSV,
)

from src.types import DataFrame, EdgeCandidateList, pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TripGenerator:
    """
    Convert travel demand into SUMO routes.

    Pipeline
    --------
    1. load_network()
    2. load_travel_demand()
    3. load_node_statistics()
    4. create_routes()
    5. write_vehicle_types()
    6. write_routes_xml()
    7. verify_outputs()
    8. run()
    """

    VEHICLE_CLASS_MAP: dict[str, str] = {
        "car": "passenger",
        "danfo": "passenger",
        "korope": "passenger",
        "brt": "bus",
        "molue": "bus",
        "keke": "passenger",
        "okada": "motorcycle",
        "deliveryVan": "delivery",
        "truck": "truck",
        "police": "authority",
        "ambulance": "emergency",
        "fireTruck": "emergency",
    }

    def __init__(
        self,
        travel_demand_csv: Path = TRAVEL_DEMAND_CSV,
        net_file: Path = SUMO_NETWORK_FILE,
        route_file: Path = SUMO_ROUTE_FILE,
        node_statistics_csv: Path = NODE_STATISTICS_CSV,
    ) -> None:
        """
        Initialize the TripGenerator.

        Parameters
        ----------
        travel_demand_csv:
            CSV containing generated travel demand.

        net_file:
            SUMO .net.xml network file.

        route_file:
            Output SUMO .rou.xml file.

        node_statistics_csv:
            OSM node statistics (osmid, x, y in lon/lat) used to
            resolve demand endpoints to real-world coordinates.
        """

        self.travel_demand_csv = travel_demand_csv
        self.net_file = net_file
        self.route_file = route_file
        self.node_statistics_csv = node_statistics_csv

        self.edge_search_radius = EDGE_SEARCH_RADIUS

        self.network: Any = None
        self.travel_demand: DataFrame | None = None
        self.node_statistics: DataFrame | None = None

        # populated by create_routes()
        self.routes: list[dict[str, object]] = []
        self.failed_trips: list[dict[str, object]] = []

        self._xml_root: ET.Element | None = None

        logger.info("Initialized TripGenerator...")

    # ==================================================================
    # LOAD NETWORK
    # ==================================================================

    def load_network(self) -> None:
        """Load the SUMO network using sumolib."""

        logger.info("=" * 70)
        logger.info("LOADING SUMO NETWORK")
        logger.info("=" * 70)

        if not self.net_file.exists():
            raise FileNotFoundError(
                f"SUMO network not found: {self.net_file}"
            )

        self.network = sumolib.net.readNet(str(self.net_file))

        logger.info("Network loaded successfully.")
        logger.info("Network file: %s", self.net_file)
        logger.info("SUMO edges: %d", len(self.network.getEdges()))
        logger.info("SUMO junctions: %d", len(self.network.getNodes()))

    # ==================================================================
    # LOAD TRAVEL DEMAND
    # ==================================================================

    def load_travel_demand(self) -> DataFrame:
        """
        Load and normalize travel demand.

        Normalizes the project schema:

            vehicle_type -> type
            departure_time -> depart
        """

        logger.info("=" * 70)
        logger.info("LOADING TRAVEL DEMAND")
        logger.info("=" * 70)

        if not self.travel_demand_csv.exists():
            raise FileNotFoundError(
                f"Travel demand not found: {self.travel_demand_csv}"
            )

        demand = pd.read_csv(self.travel_demand_csv)

        required_columns = {
            "vehicle_id",
            "vehicle_type",
            "departure_time",
            "origin_node",
            "destination_node",
        }

        missing_columns = sorted(required_columns - set(demand.columns))

        if missing_columns:
            raise ValueError(
                f"Travel demand is missing required columns: {missing_columns}"
            )

        demand = demand.rename(columns={"vehicle_type": "type"})

        demand["vehicle_id"] = demand["vehicle_id"].astype(str)
        demand["type"] = demand["type"].astype(str).str.strip()

        demand["departure_time"] = pd.to_numeric(
            demand["departure_time"], errors="raise"
        )

        demand["origin_node"] = pd.to_numeric(
            demand["origin_node"], errors="raise"
        ).astype("int64")

        demand["destination_node"] = pd.to_numeric(
            demand["destination_node"], errors="raise"
        ).astype("int64")

        if demand["vehicle_id"].duplicated().any():
            raise ValueError("Duplicate vehicle_id values in travel demand.")

        self.travel_demand = demand

        logger.info("Loaded %d travel demand records.", len(demand))
        logger.info("Vehicle types: %d", demand["type"].nunique())
        logger.info(
            "Departure range: %d - %d seconds",
            int(demand["departure_time"].min()),
            int(demand["departure_time"].max()),
        )
        logger.info(
            "Normalized columns: vehicle_type -> type, "
            "departure_time -> depart"
        )

        return demand

    # ==================================================================
    # LOAD NODE STATISTICS
    # ==================================================================

    def load_node_statistics(self) -> DataFrame:
        """Load OSM node statistics used to resolve demand endpoints."""

        logger.info("=" * 70)
        logger.info("LOADING NODE STATISTICS")
        logger.info("=" * 70)

        if not self.node_statistics_csv.exists():
            raise FileNotFoundError(
                f"Node statistics not found: {self.node_statistics_csv}"
            )

        nodes = pd.read_csv(self.node_statistics_csv)

        required_columns = {"osmid", "x", "y"}
        missing_columns = required_columns.difference(nodes.columns)

        if missing_columns:
            raise ValueError(
                "Node statistics are missing required columns: "
                f"{sorted(missing_columns)}"
            )

        self.node_statistics = nodes

        logger.info("Loaded %d nodes.", len(nodes))

        return nodes

    # ==================================================================
    # VEHICLE CLASS
    # ==================================================================

    def get_vehicle_class(self, vehicle_type: str) -> str:
        """Convert application vehicle type into a SUMO vehicle class."""

        try:
            return self.VEHICLE_CLASS_MAP[vehicle_type]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported vehicle type: {vehicle_type!r}. "
                f"Supported types: {sorted(self.VEHICLE_CLASS_MAP)}"
            ) from exc

    # ==================================================================
    # COORDINATE CONVERSION
    # ==================================================================

    def convert_lonlat_to_sumo_xy(
        self, longitude: float, latitude: float
    ) -> tuple[float, float]:
        """Convert geographic coordinates into SUMO coordinates."""

        if self.network is None:
            raise RuntimeError("SUMO network has not been loaded.")

        x, y = self.network.convertLonLat2XY(longitude, latitude)

        return float(x), float(y)

    # ==================================================================
    # EDGE SELECTION
    # ==================================================================

    def find_valid_edges(
        self, x: float, y: float, vehicle_class: str
    ) -> EdgeCandidateList:
        """Find nearby SUMO edges that allow a vehicle class."""

        if self.network is None:
            raise RuntimeError("SUMO network has not been loaded.")

        candidates: EdgeCandidateList = self.network.getNeighboringEdges(
            x, y, self.edge_search_radius
        )

        return [
            (edge, distance)
            for edge, distance in candidates
            if edge.allows(vehicle_class)
        ]

    # ==================================================================
    # CREATE ROUTES
    # ==================================================================

    def create_routes(self) -> list[dict[str, object]]:
        """
        Snap each trip's origin/destination to the nearest compatible
        SUMO edge, then compute a route between them using sumolib's
        built-in shortest-path search.

        Failures (missing node, no compatible edge, no path) are
        logged and skipped rather than raised, so a handful of bad
        trips don't abort the whole run.
        """

        if self.network is None:
            raise RuntimeError("SUMO network has not been loaded.")

        if self.travel_demand is None:
            raise RuntimeError("Travel demand has not been loaded.")

        if self.node_statistics is None:
            raise RuntimeError("Node statistics have not been loaded.")

        logger.info("=" * 70)
        logger.info("CREATING ROUTES")
        logger.info("=" * 70)

        node_lookup = (
            self.node_statistics.set_index("osmid")[["x", "y"]].to_dict(
                "index"
            )
        )

        routes: list[dict[str, object]] = []
        failed: list[dict[str, object]] = []

        total_trips = len(self.travel_demand)

        for i, (_, trip) in enumerate(self.travel_demand.iterrows()):
            vehicle_id = str(trip["vehicle_id"])
            vehicle_type = str(trip["type"])
            origin_node = trip["origin_node"]
            destination_node = trip["destination_node"]
            departure_time = float(trip["departure_time"])

            try:
                vehicle_class = self.get_vehicle_class(vehicle_type)
            except ValueError as exc:
                failed.append(
                    {
                        "vehicle_id": vehicle_id,
                        "vehicle_type": vehicle_type,
                        "reason": str(exc),
                    }
                )
                continue

            if origin_node not in node_lookup or (
                destination_node not in node_lookup
            ):
                failed.append(
                    {
                        "vehicle_id": vehicle_id,
                        "vehicle_type": vehicle_type,
                        "origin_node": origin_node,
                        "destination_node": destination_node,
                        "reason": "missing_node_in_statistics",
                    }
                )
                continue

            origin = node_lookup[origin_node]
            destination = node_lookup[destination_node]

            origin_x, origin_y = self.convert_lonlat_to_sumo_xy(
                float(origin["x"]), float(origin["y"])
            )
            destination_x, destination_y = self.convert_lonlat_to_sumo_xy(
                float(destination["x"]), float(destination["y"])
            )

            origin_candidates = self.find_valid_edges(
                origin_x, origin_y, vehicle_class
            )
            destination_candidates = self.find_valid_edges(
                destination_x, destination_y, vehicle_class
            )

            if not origin_candidates:
                failed.append(
                    {
                        "vehicle_id": vehicle_id,
                        "vehicle_type": vehicle_type,
                        "origin_node": origin_node,
                        "destination_node": destination_node,
                        "reason": "no_origin_edge_found",
                    }
                )
                continue

            if not destination_candidates:
                failed.append(
                    {
                        "vehicle_id": vehicle_id,
                        "vehicle_type": vehicle_type,
                        "origin_node": origin_node,
                        "destination_node": destination_node,
                        "reason": "no_destination_edge_found",
                    }
                )
                continue

            origin_edge = min(origin_candidates, key=lambda c: c[1])[0]
            destination_edge = min(
                destination_candidates, key=lambda c: c[1]
            )[0]

            path_edges, cost = self.network.getShortestPath(
                origin_edge,
                destination_edge,
                vClass=vehicle_class,
            )

            if not path_edges:
                failed.append(
                    {
                        "vehicle_id": vehicle_id,
                        "vehicle_type": vehicle_type,
                        "origin_node": origin_node,
                        "destination_node": destination_node,
                        "reason": "no_path_found",
                    }
                )
                continue

            routes.append(
                {
                    "vehicle_id": vehicle_id,
                    "vehicle_class": vehicle_class,
                    "depart": departure_time,
                    "edges": " ".join(e.getID() for e in path_edges),
                    "cost": float(cost),
                }
            )

            if (i + 1) % 100 == 0 or (i + 1) == total_trips:
                logger.info("Processed %d / %d trips...", i + 1, total_trips)

        if not routes:
            raise ValueError(
                "All trip routing attempts failed. "
                "Check node coordinates against the SUMO network "
                "boundaries, vehicle class permissions, and "
                "EDGE_SEARCH_RADIUS."
            )

        self.routes = routes
        self.failed_trips = failed

        logger.info("=" * 70)
        logger.info("ROUTES CREATED: %d", len(routes))
        logger.info("FAILED TRIPS: %d", len(failed))
        logger.info("TOTAL TRIPS: %d", total_trips)
        logger.info("=" * 70)

        return routes

    # ==================================================================
    # WRITE VEHICLE TYPES
    # ==================================================================

    def write_vehicle_types(self) -> ET.Element:
        """
        Build the <routes> root element and populate it with a
        <vType> per distinct vehicle class used by the routed trips.
        """

        if not self.routes:
            raise RuntimeError(
                "No routes available. Run create_routes() first."
            )

        logger.info("=" * 70)
        logger.info("WRITING VEHICLE TYPES")
        logger.info("=" * 70)

        root = ET.Element(
            "routes",
            {"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"},
        )

        vehicle_classes = sorted(
            {str(route["vehicle_class"]) for route in self.routes}
        )

        for vehicle_class in vehicle_classes:
            ET.SubElement(
                root,
                "vType",
                {"id": vehicle_class, "vClass": vehicle_class},
            )

        logger.info("Vehicle types written: %d", len(vehicle_classes))

        self._xml_root = root

        return root

    # ==================================================================
    # WRITE ROUTES XML
    # ==================================================================

    def write_routes_xml(self) -> Path:
        """
        Append a <vehicle><route .../></vehicle> pair for each routed
        trip, in departure-time order, and write the file to disk.
        """

        if self._xml_root is None:
            raise RuntimeError(
                "Vehicle types have not been written. "
                "Run write_vehicle_types() first."
            )

        logger.info("=" * 70)
        logger.info("WRITING SUMO ROUTES XML")
        logger.info("=" * 70)

        self.route_file.parent.mkdir(parents=True, exist_ok=True)

        # duarouter/sumo expect vehicles in ascending depart order
        ordered_routes = sorted(
            self.routes, key=lambda r: cast(float, r["depart"])
        )

        for route in ordered_routes:
            vehicle = ET.SubElement(
                self._xml_root,
                "vehicle",
                {
                    "id": str(route["vehicle_id"]),
                    "type": str(route["vehicle_class"]),
                    "depart": f"{cast(float, route['depart']):.2f}",
                },
            )

            ET.SubElement(
                vehicle,
                "route",
                {"edges": str(route["edges"])},
            )

        tree = ET.ElementTree(self._xml_root)
        ET.indent(tree, space="    ")

        tree.write(
            self.route_file,
            encoding="utf-8",
            xml_declaration=True,
        )

        logger.info("SUMO route file created: %s", self.route_file)
        logger.info("Vehicles written: %d", len(ordered_routes))

        return self.route_file

    # ==================================================================
    # VERIFY OUTPUTS
    # ==================================================================

    def verify_outputs(self) -> bool:
        """Verify the generated SUMO route file."""

        logger.info("=" * 70)
        logger.info("VERIFYING GENERATED SUMO ROUTES")
        logger.info("=" * 70)

        if not self.route_file.exists():
            logger.error("Route file does not exist: %s", self.route_file)
            return False

        try:
            tree = ET.parse(self.route_file)
        except ET.ParseError as exc:
            logger.error("Invalid XML in route file: %s", exc)
            return False

        root = tree.getroot()

        vehicles = root.findall(".//vehicle")
        routes = root.findall(".//route")

        if not vehicles:
            logger.error("No <vehicle> elements found in route file.")
            return False

        vehicle_ids = [v.get("id") for v in vehicles]

        if len(vehicle_ids) != len(set(vehicle_ids)):
            logger.error("Duplicate vehicle IDs found.")
            return False

        empty_routes = sum(
            1 for r in routes if not r.get("edges", "").strip()
        )

        if empty_routes:
            logger.error("Found %d empty routes.", empty_routes)
            return False

        expected_count = len(self.routes)
        generated_count = len(vehicles)

        logger.info("Expected routed trips : %d", expected_count)
        logger.info("Generated SUMO vehicles: %d", generated_count)
        logger.info("Generated SUMO routes  : %d", len(routes))

        if self.failed_trips:
            logger.warning(
                "%d trips failed to route and were excluded.",
                len(self.failed_trips),
            )

        logger.info("=" * 70)

        if generated_count == expected_count:
            logger.info("SUMO ROUTE VERIFICATION PASSED")
            return True

        logger.warning(
            "SUMO ROUTE VERIFICATION COMPLETED WITH COUNT DIFFERENCE"
        )
        return False

    # ==================================================================
    # FULL PIPELINE
    # ==================================================================

    def run(self) -> None:
        """Execute the complete trip-generation pipeline."""

        logger.info("=" * 70)
        logger.info("STARTING TRIP GENERATION PIPELINE")
        logger.info("=" * 70)

        self.load_network()
        self.load_travel_demand()
        self.load_node_statistics()
        self.create_routes()
        self.write_vehicle_types()
        self.write_routes_xml()

        if not self.verify_outputs():
            raise RuntimeError("SUMO route verification failed.")

        logger.info("=" * 70)
        logger.info("TRIP GENERATION PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)


def main() -> None:
    """Application entry point."""

    generator = TripGenerator()
    generator.run()


if __name__ == "__main__":
    main()