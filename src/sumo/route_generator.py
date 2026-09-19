# ====== updateded =======================================
"""
Route Generator
===============

Generate SUMO trips and routes from synthetic travel demand.

Pipeline
--------
travel_demand.csv
        |
        v
Load OSM node statistics
        |
        v
Load SUMO network
        |
        v
Convert OSM lon/lat -> SUMO X/Y
        |
        v
Find vehicle-compatible SUMO edges
        |
        v
Map OSM origin/destination nodes -> SUMO edges
        |
        v
Build SUMO trips.xml
        |
        v
duarouter
        |
        v
routes.rou.xml
        |
        v
Verify generated routes

Responsibilities
----------------
This module:

    - validates input files
    - loads travel demand
    - loads node statistics
    - loads the SUMO network
    - converts geographic coordinates
    - maps OSM nodes to SUMO edges
    - respects vehicle classes
    - creates SUMO trip XML
    - invokes duarouter
    - verifies generated routes
    - exports mapping/routing audit reports

This module does NOT:

    - generate travel demand
    - train ML models
    - run the SUMO simulation
    - calculate traffic statistics
"""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import sumolib  # type: ignore

from config import (
    EDGE_SEARCH_RADIUS,
    FAILED_ROUTE_MAPPINGS_CSV,
    NODE_STATISTICS_CSV,
    SUMO_CONFIG_FILE,
    SUMO_NETWORK_FILE,
    SUMO_OUTPUT_FILE,
    SUMO_ROUTE_FILE,
    SUMO_TRIP_FILE,
    TRAVEL_DEMAND_CSV,
)

from src.types import DataFrame, EdgeCandidateList, pd
from src.utils.logger import get_logger


logger = get_logger(__name__)


class RouteGenerator:
    """
    Generate SUMO trips and routes from synthetic travel demand.

    Pipeline
    --------
    1. verify_input_file()
    2. load_travel_demand()
    3. load_node_statistics()
    4. load_network()
    5. convert_lonlat_to_sumo_xy()
    6. get_vehicle_class()
    7. find_valid_edges()
    8. map_nodes_to_edges()
    9. build_sumo_trip_file()
    10. generate_routes()
    11. verify_routes()
    12. run()
    """

    # ------------------------------------------------------------------
    # Vehicle class mapping
    # ------------------------------------------------------------------

    VEHICLE_CLASS_MAP: dict[str, str] = {
        "car": "passenger",
        "danfo": "bus",
        "korope": "bus",
        "brt": "bus",
        "molue": "bus",
        "keke": "passenger",
        "okada": "motorcycle",
        "deliveryVan": "delivery",
        "truck": "truck",
        "police": "passenger",
        "ambulance": "emergency",
        "fireTruck": "emergency",
    }

    def __init__(
        self,
        travel_demand_csv: Path = TRAVEL_DEMAND_CSV,
        net_file: Path = SUMO_NETWORK_FILE,
    ) -> None:
        """
        Initialize the RouteGenerator.

        Parameters
        ----------
        travel_demand_csv:
            CSV containing generated travel demand.

        net_file:
            SUMO .net.xml network file.
        """

        self.travel_demand_csv = travel_demand_csv
        self.net_file = net_file

        self.node_statistics_csv = NODE_STATISTICS_CSV

        self.trip_file = SUMO_TRIP_FILE
        self.route_file = SUMO_ROUTE_FILE

        self.config_file = SUMO_CONFIG_FILE
        self.output_file = SUMO_OUTPUT_FILE

        self.failed_route_mapping_csv = FAILED_ROUTE_MAPPINGS_CSV

        self.edge_search_radius = EDGE_SEARCH_RADIUS

        self.travel_demand: DataFrame | None = None
        self.node_statistics: DataFrame | None = None

        self.network: Any = None

        self.mapped_demand: DataFrame | None = None

        logger.info("Initialized RouteGenerator...")

    # ==================================================================
    # INPUT VALIDATION
    # ==================================================================

    def verify_input_file(self) -> bool:
        """
        Verify that all required input files exist.

        Returns
        -------
        bool
            True when all required files exist.
        """

        logger.info("=" * 70)
        logger.info("VERIFYING ROUTE GENERATOR INPUTS")
        logger.info("=" * 70)

        valid = True

        required_files = {
            "Travel demand": self.travel_demand_csv,
            "SUMO network": self.net_file,
            "Node statistics": self.node_statistics_csv,
        }

        for name, path in required_files.items():
            if path.exists():
                logger.info("✓ %s: %s", name, path)
            else:
                logger.error("✗ %s not found: %s", name, path)
                valid = False

        return valid

    # ==================================================================
    # LOAD TRAVEL DEMAND
    # ==================================================================

    def load_travel_demand(self) -> DataFrame:
        """
        Load and validate travel demand.

        The source travel_demand.csv uses the project-level schema:

            vehicle_id
            vehicle_type
            departure_time
            origin_node
            destination_node
            priority
            trip_status

        Internally, RouteGenerator normalizes these to:

            type
            departure_time

        so that SUMO generation can use a consistent schema.
        """
        logger.info("=" * 70)
        logger.info("LOADING TRAVEL DEMAND")
        logger.info("=" * 70)

        self.travel_demand = pd.read_csv(self.travel_demand_csv)

        required_columns = {
            "vehicle_id",
            "vehicle_type",
            "departure_time",
            "origin_node",
            "destination_node",
        }

        missing_columns = sorted(
            required_columns - set(self.travel_demand.columns)
        )

        if missing_columns:
            raise ValueError(
                f"Travel demand is missing required columns: "
                f"{missing_columns}"
            )

        # --------------------------------------------------------------
        # Normalize project schema → internal RouteGenerator schema
        # --------------------------------------------------------------

        self.travel_demand = self.travel_demand.rename(
            columns={
                "vehicle_type": "type",
                # "departure_time": "departure_time",
                "departure_time": "depart",

            }
        )

        # --------------------------------------------------------------
        # Validate normalized columns
        # --------------------------------------------------------------

        normalized_required = {
            "vehicle_id",
            "type",
            # "departure_time",
            "depart",    
            "origin_node",
            "destination_node",
        }

        missing_normalized = sorted(
            normalized_required - set(self.travel_demand.columns)
        )

        if missing_normalized:
            raise ValueError(
                "Normalized travel demand is missing required columns: "
                f"{missing_normalized}"
            )

        # --------------------------------------------------------------
        # Type normalization
        # --------------------------------------------------------------

        self.travel_demand["vehicle_id"] = (
            self.travel_demand["vehicle_id"]
            .astype(str)
        )

        self.travel_demand["type"] = (
            self.travel_demand["type"]
            .astype(str)
            .str.strip()
        )

        self.travel_demand["depart"] = pd.to_numeric(
            self.travel_demand["depart"],
            errors="raise",
        )

        self.travel_demand["origin_node"] = pd.to_numeric(
            self.travel_demand["origin_node"],
            errors="raise",
        ).astype("int64")

        self.travel_demand["destination_node"] = pd.to_numeric(
            self.travel_demand["destination_node"],
            errors="raise",
        ).astype("int64")

        # --------------------------------------------------------------
        # Validation
        # --------------------------------------------------------------

        if self.travel_demand["vehicle_id"].duplicated().any():
            raise ValueError(
                "Duplicate vehicle_id values detected in travel demand."
            )

        if self.travel_demand["type"].isna().any():
            raise ValueError(
                "Travel demand contains missing vehicle types."
            )

        if self.travel_demand["depart"].isna().any():
            raise ValueError(
                "Travel demand contains missing departure times."
            )

        logger.info(
            "Loaded %d travel demand records.",
            len(self.travel_demand),
        )

        logger.info(
            "Vehicle types: %d",
            self.travel_demand["type"].nunique(),
        )

        logger.info(
            "Departure range: %d - %d seconds",
            int(self.travel_demand["depart"].min()),
            int(self.travel_demand["depart"].max()),
        )

        logger.info(
            "Normalized columns: vehicle_type → type, "
            "departure_time → depart"
        )

        return self.travel_demand

    # ==================================================================
    # LOAD NODE STATISTICS
    # ==================================================================

    def load_node_statistics(self) -> DataFrame:
        """
        Load OSM node statistics.

        Returns
        -------
        DataFrame
            Node statistics.
        """

        logger.info("=" * 70)
        logger.info("LOADING NODE STATISTICS")
        logger.info("=" * 70)

        nodes = pd.read_csv(self.node_statistics_csv)

        required_columns = {
            "osmid",
            "x",
            "y",
        }

        missing_columns = required_columns.difference(nodes.columns)

        if missing_columns:
            raise ValueError(
                "Node statistics are missing required columns: "
                f"{sorted(missing_columns)}"
            )

        self.node_statistics = nodes

        # logger.info("Loaded %d nodes.", len(self.node_statistics),        )
        logger.info(
                f"Loaded {len(self.node_statistics):,} nodes."
            )


        return self.node_statistics

    # ==================================================================
    # LOAD SUMO NETWORK
    # ==================================================================

    def load_network(self) -> None:
        """
        Load the SUMO network using sumolib.
        """

        logger.info("=" * 70)
        logger.info("LOADING SUMO NETWORK")
        logger.info("=" * 70)

        self.network = sumolib.net.readNet(str(self.net_file))

        logger.info("Network loaded successfully.")
        logger.info("Network file: %s", self.net_file)

        logger.info(f"SUMO edges: %d", len(self.network.getEdges()), )

        # logger.info(
        #     "SUMO junctions: %d",
        #     len(self.network.getNodes()),
        # )
        logger.info(f"SUMO junctions: %d", len(self.network.getNodes()), )


    # ==================================================================
    # COORDINATE CONVERSION
    # ==================================================================

    def convert_lonlat_to_sumo_xy(
        self,
        longitude: float,
        latitude: float,
    ) -> tuple[float, float]:
        """
        Convert geographic coordinates into SUMO coordinates.

        Parameters
        ----------
        longitude:
            Longitude in decimal degrees.

        latitude:
            Latitude in decimal degrees.

        Returns
        -------
        tuple[float, float]
            SUMO X/Y coordinates.
        """

        if self.network is None:
            raise RuntimeError(
                "SUMO network has not been loaded."
            )

        x, y = self.network.convertLonLat2XY(
            longitude,
            latitude,
        )

        return float(x), float(y)

    # ==================================================================
    # VEHICLE CLASS
    # ==================================================================

    def get_vehicle_class(self, vehicle_type: str) -> str:
        """
        Convert application vehicle type into SUMO vehicle class.
        """

        vehicle_classes = {
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

        try:
            return vehicle_classes[vehicle_type]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported vehicle type: {vehicle_type!r}"
            ) from exc

    # ==================================================================
    # FIND VALID EDGES
    # ==================================================================

    def find_valid_edges(
        self,
        x: float,
        y: float,
        vehicle_class: str,
    ) -> EdgeCandidateList:
        """
        Find nearby SUMO edges that allow a vehicle class.

        Parameters
        ----------
        x:
            SUMO X coordinate.

        y:
            SUMO Y coordinate.

        vehicle_class:
            SUMO vehicle class.

        Returns
        -------
        EdgeCandidateList
            List of (edge, distance) candidates.
        """

        if self.network is None:
            raise RuntimeError(
                "SUMO network has not been loaded."
            )

        candidates: EdgeCandidateList = (
            self.network.getNeighboringEdges(
                x,
                y,
                self.edge_search_radius,
            )
        )

        valid_candidates = [
            (edge, distance)
            for edge, distance in candidates
            if edge.allows(vehicle_class)
        ]

        return valid_candidates

    # ==================================================================
    # NODE -> EDGE MAPPING
    # ==================================================================

    def map_nodes_to_edges(self) -> DataFrame:
        """
        Map each demand endpoint to a compatible SUMO edge.

        Mapping is vehicle-aware.

        The closest edge is selected from only those edges that allow
        the corresponding SUMO vehicle class.

        Failed mappings are exported to:

            outputs/reports/failed_route_mappings.csv
        """

        if self.travel_demand is None:
            raise RuntimeError(
                "Travel demand has not been loaded."
            )

        if self.node_statistics is None:
            raise RuntimeError(
                "Node statistics have not been loaded."
            )

        if self.network is None:
            raise RuntimeError(
                "SUMO network has not been loaded."
            )

        logger.info("=" * 70)
        logger.info("MAPPING NODES TO VEHICLE-COMPATIBLE SUMO EDGES")
        logger.info("=" * 70)

        node_lookup = (
            self.node_statistics
            .set_index("osmid")[["x", "y"]]
            .to_dict("index")
        )

        mapped_mappings: list[dict[str, object]] = []
        failed_mappings: list[dict[str, object]] = []

        failed_missing_nodes = 0
        failed_no_origin_edge = 0
        failed_no_destination_edge = 0

        total_trips = len(self.travel_demand)

        for i, (trip_index, trip) in enumerate(
            self.travel_demand.iterrows()
        ):
            origin_node = trip["origin_node"]
            destination_node = trip["destination_node"]
            # vehicle_type = str(trip["vehicle_type"])
            vehicle_type = str(trip["type"])

            vehicle_class = self.get_vehicle_class(
                vehicle_type
            )

            # ----------------------------------------------------------
            # Node existence
            # ----------------------------------------------------------

            missing_origin = origin_node not in node_lookup
            missing_destination = (
                destination_node not in node_lookup
            )

            if missing_origin or missing_destination:
                failed_missing_nodes += 1

                failed_mappings.append(
                    {
                        "trip_index": trip_index,
                        "vehicle_id": trip["vehicle_id"],
                        "vehicle_type": vehicle_type,
                        "origin_node": origin_node,
                        "destination_node": destination_node,
                        "reason": "missing_node_in_statistics",

                        # "vehicle_id": str(trip["vehicle_id"]),
                        # "type": str(trip["type"]),
                        # "depart": float(trip["depart"]),
                        # "origin_node": int(trip["origin_node"]),
                        # "origin_edge": str(origin_edge),
                        # "destination_node": int(trip["destination_node"]),
                        # "destination_edge": str(destination_edge),
                        # "vehicle_class": str(vehicle_class),
                    }
                )

                continue

            origin = node_lookup[origin_node]
            destination = node_lookup[destination_node]

            # ----------------------------------------------------------
            # Coordinate conversion
            # ----------------------------------------------------------

            origin_x, origin_y = (
                self.convert_lonlat_to_sumo_xy(
                    float(origin["x"]),
                    float(origin["y"]),
                )
            )

            destination_x, destination_y = (
                self.convert_lonlat_to_sumo_xy(
                    float(destination["x"]),
                    float(destination["y"]),
                )
            )

            # ----------------------------------------------------------
            # Find vehicle-compatible edges
            # ----------------------------------------------------------

            origin_candidates = self.find_valid_edges(
                origin_x,
                origin_y,
                vehicle_class,
            )

            destination_candidates = self.find_valid_edges(
                destination_x,
                destination_y,
                vehicle_class,
            )

            # ----------------------------------------------------------
            # Origin failure
            # ----------------------------------------------------------

            if not origin_candidates:
                failed_no_origin_edge += 1

                failed_mappings.append(
                    {
                        "trip_index": trip_index,
                        "vehicle_id": trip["vehicle_id"],
                        "vehicle_type": vehicle_type,
                        "vehicle_class": vehicle_class,
                        "origin_node": origin_node,
                        "destination_node": destination_node,
                        "reason": "no_origin_edge_found",
                    }
                )

                continue

            # ----------------------------------------------------------
            # Destination failure
            # ----------------------------------------------------------

            if not destination_candidates:
                failed_no_destination_edge += 1

                failed_mappings.append(
                    {
                        "trip_index": trip_index,
                        "vehicle_id": trip["vehicle_id"],
                        "vehicle_type": vehicle_type,
                        "vehicle_class": vehicle_class,
                        "origin_node": origin_node,
                        "destination_node": destination_node,
                        "reason": "no_destination_edge_found",
                    }
                )

                continue

            # ----------------------------------------------------------
            # Closest compatible edges
            # ----------------------------------------------------------

            closest_origin = min(
                origin_candidates,
                key=lambda item: item[1],
            )

            closest_destination = min(
                destination_candidates,
                key=lambda item: item[1],
            )

            origin_edge = closest_origin[0]
            destination_edge = closest_destination[0]

            mapped_mappings.append(
                {
                    "trip_index": trip_index,
                    "origin_edge": origin_edge.getID(),
                    "destination_edge": destination_edge.getID(),
                    "origin_distance_m": float(
                        closest_origin[1]
                    ),
                    "destination_distance_m": float(
                        closest_destination[1]
                    ),
                    "vehicle_class": vehicle_class,
                }
            )

            if (i + 1) % 100 == 0 or (i + 1) == total_trips:
                logger.info(
                    "Processed %d / %d trips...",
                    i + 1,
                    total_trips,
                )

        # ==================================================================
        # FAILED MAPPING AUDIT
        # ==================================================================

        if failed_mappings:
            failed_df = pd.DataFrame(
                failed_mappings
            )

            self.failed_route_mapping_csv.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            failed_df.to_csv(
                self.failed_route_mapping_csv,
                index=False,
            )

            logger.warning(
                "Exported %d failed mappings to %s",
                len(failed_df),
                self.failed_route_mapping_csv,
            )

        # ==================================================================
        # MERGE SUCCESSFUL MAPPINGS
        # ==================================================================

        total_failed = (
            failed_missing_nodes
            + failed_no_origin_edge
            + failed_no_destination_edge
        )

        if not mapped_mappings:
            raise ValueError(
                "All trip edge mappings failed. "
                "Check network boundaries, coordinates, "
                "vehicle permissions, and EDGE_SEARCH_RADIUS."
            )

        mapping_df = (
            pd.DataFrame(mapped_mappings)
            .set_index("trip_index")
        )

        mapped_demand = self.travel_demand.copy()

        mapped_demand["origin_edge"] = (
            mapping_df["origin_edge"]
        )

        mapped_demand["destination_edge"] = (
            mapping_df["destination_edge"]
        )

        mapped_demand["origin_distance_m"] = (
            mapping_df["origin_distance_m"]
        )

        mapped_demand["destination_distance_m"] = (
            mapping_df["destination_distance_m"]
        )

        mapped_demand["vehicle_class"] = (
            mapping_df["vehicle_class"]
        )

        mapped_demand = mapped_demand.dropna(
            subset=[
                "origin_edge",
                "destination_edge",
            ]
        )

        # ==================================================================
        # ACCOUNTING VALIDATION
        # ==================================================================

        assert (
            len(mapped_demand) + total_failed
            == total_trips
        ), (
            "Accounting mismatch! "
            f"Successful ({len(mapped_demand)}) + "
            f"Failed ({total_failed}) != "
            f"Total ({total_trips})."
        )

        self.mapped_demand = mapped_demand

        logger.info("=" * 70)
        logger.info(
            "SUCCESSFULLY MAPPED: %d trips",
            len(mapped_demand),
        )
        logger.info(
            "Missing nodes: %d",
            failed_missing_nodes,
        )
        logger.info(
            "No origin edge: %d",
            failed_no_origin_edge,
        )
        logger.info(
            "No destination edge: %d",
            failed_no_destination_edge,
        )
        logger.info(
            "Total failed: %d",
            total_failed,
        )
        logger.info("=" * 70)

        logger.info("First 5 mapped trips:")
        logger.info(
            "\n%s",
            mapped_demand[
                [
                    "vehicle_id",
                    "type",
                    "origin_node",
                    "origin_edge",
                    "destination_node",
                    "destination_edge",
                ]
            ].head().to_string(index=False),
        )

        return mapped_demand

    # ==================================================================
    # BUILD SUMO TRIP FILE
    # ==================================================================

    def build_sumo_trip_file(self) -> Path:
        """
        Build the SUMO trips XML file from mapped travel demand.

        Expected internal schema after load_travel_demand():

            vehicle_id
            type
            depart
            origin_node
            destination_node
            priority
            trip_status

        map_nodes_to_edges() additionally provides:

            vehicle_class
            origin_edge
            destination_edge
        """

        if self.mapped_demand is None:
            raise RuntimeError(
                "No mapped demand available. "
                "Run map_nodes_to_edges() first."
            )

        logger.info("=" * 70)
        logger.info("BUILDING SUMO TRIP FILE")
        logger.info("=" * 70)

        # --------------------------------------------------------------
        # Validate required columns
        # --------------------------------------------------------------

        required_columns = {
            "vehicle_id",
            "type",
            "depart",
            "origin_edge",
            "destination_edge",
            "vehicle_class",
        }

        missing_columns = sorted(
            required_columns
            - set(self.mapped_demand.columns)
        )

        if missing_columns:
            raise ValueError(
                "Mapped demand is missing required columns: "
                f"{missing_columns}"
            )

        # --------------------------------------------------------------
        # Validate mapped demand values
        # --------------------------------------------------------------

        if self.mapped_demand.empty:
            raise ValueError(
                "Mapped demand is empty. "
                "No SUMO trips can be generated."
            )

        if self.mapped_demand["vehicle_id"].duplicated().any():
            raise ValueError(
                "Duplicate vehicle IDs detected in mapped demand."
            )

        if self.mapped_demand["depart"].isna().any():
            raise ValueError(
                "Mapped demand contains missing departure times."
            )

        if self.mapped_demand["origin_edge"].isna().any():
            raise ValueError(
                "Mapped demand contains missing origin edges."
            )

        if self.mapped_demand["destination_edge"].isna().any():
            raise ValueError(
                "Mapped demand contains missing destination edges."
            )

        # --------------------------------------------------------------
        # Prepare output directory
        # --------------------------------------------------------------

        self.trip_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # --------------------------------------------------------------
        # Create SUMO routes root
        # --------------------------------------------------------------

        root = ET.Element(
            "routes",
            {
                "xmlns:xsi": (
                    "http://www.w3.org/2001/XMLSchema-instance"
                ),
            },
        )

        # --------------------------------------------------------------
        # Create SUMO vehicle types
        # --------------------------------------------------------------

        vehicle_classes = sorted(
            self.mapped_demand["vehicle_class"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

        for vehicle_class in vehicle_classes:

            ET.SubElement(
                root,
                "vType",
                {
                    "id": vehicle_class,
                    "vClass": vehicle_class,
                },
            )

        logger.info(
            "Vehicle classes written: %d",
            len(vehicle_classes),
        )

        # --------------------------------------------------------------
        # Create SUMO trips
        # --------------------------------------------------------------

        for _, row in self.mapped_demand.iterrows():

            vehicle_id = str(
                row["vehicle_id"]
            )

            vehicle_class = str(
                row["vehicle_class"]
            ).strip()

            origin_edge = str(
                row["origin_edge"]
            ).strip()

            destination_edge = str(
                row["destination_edge"]
            ).strip()

            depart = float(
                row["depart"]
            )

            ET.SubElement(
                root,
                "trip",
                {
                    "id": vehicle_id,
                    "type": vehicle_class,
                    "depart": f"{depart:.2f}",
                    "from": origin_edge,
                    "to": destination_edge,
                },
            )

        # --------------------------------------------------------------
        # Write XML
        # --------------------------------------------------------------

        tree = ET.ElementTree(root)

        ET.indent(
            tree,
            space="    ",
        )

        tree.write(
            self.trip_file,
            encoding="utf-8",
            xml_declaration=True,
        )

        # --------------------------------------------------------------
        # Final logging
        # --------------------------------------------------------------

        logger.info(
            "SUMO trip file created: %s",
            self.trip_file,
        )

        logger.info(
            "Trips written: %d",
            len(self.mapped_demand),
        )

        return self.trip_file

    # ==================================================================
    # GENERATE ROUTES
    # ==================================================================

    def generate_routes(self) -> Path:
        """
        Generate SUMO routes using duarouter.

        Returns
        -------
        Path
            Generated SUMO route file.
        """

        if not self.trip_file.exists():
            raise FileNotFoundError(
                f"SUMO trip file not found: {self.trip_file}"
            )

        logger.info("=" * 70)
        logger.info("GENERATING SUMO ROUTES")
        logger.info("=" * 70)

        self.route_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = [
            "duarouter",
            "--net-file",
            str(self.net_file),
            "--route-files",
            str(self.trip_file),
            "--output-file",
            str(self.route_file),
            "--begin",
            "0",
            "--end",
            "86400",
            "--ignore-errors",
            "false",
        ]

        logger.info(
            "Running duarouter..."
        )

        logger.info(
            "Command: %s",
            " ".join(command),
        )

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )

        except FileNotFoundError as exc:
            logger.error(
                "duarouter was not found. "
                "Ensure SUMO is installed and duarouter "
                "is available on PATH."
            )
            raise RuntimeError(
                "duarouter executable not found."
            ) from exc

        except subprocess.CalledProcessError as exc:
            logger.error(
                "duarouter failed."
            )

            if exc.stdout:
                logger.error(
                    "duarouter stdout:\n%s",
                    exc.stdout,
                )

            if exc.stderr:
                logger.error(
                    "duarouter stderr:\n%s",
                    exc.stderr,
                )

            raise RuntimeError(
                "SUMO duarouter failed."
            ) from exc

        if result.stdout:
            logger.info(
                "duarouter output:\n%s",
                result.stdout.strip(),
            )

        if result.stderr:
            logger.warning(
                "duarouter messages:\n%s",
                result.stderr.strip(),
            )

        if not self.route_file.exists():
            raise RuntimeError(
                "duarouter completed but the route file "
                f"was not created: {self.route_file}"
            )

        logger.info(
            "SUMO route generation completed."
        )

        logger.info(
            "Route file: %s",
            self.route_file,
        )

        return self.route_file

    # ==================================================================
    # VERIFY ROUTES
    # ==================================================================

    # def verify_routes(self) -> bool:
    #     """
    #     Verify the generated SUMO route file.

    #     Returns
    #     -------
    #     bool
    #         True when the route file passes validation.
    #     """

    #     logger.info("=" * 70)
    #     logger.info("VERIFYING GENERATED SUMO ROUTES")
    #     logger.info("=" * 70)

    #     if not self.route_file.exists():
    #         logger.error(
    #             "Route file does not exist: %s",
    #             self.route_file,
    #         )
    #         return False

    #     try:
    #         tree = ET.parse(
    #             self.route_file
    #         )

    #     except ET.ParseError as exc:
    #         logger.error(
    #             "Invalid XML in route file: %s",
    #             exc,
    #         )
    #         return False

    #     root = tree.getroot()

    #     vehicles = root.findall(
    #         ".//vehicle"
    #     )

    #     routes = root.findall(
    #         ".//route"
    #     )

    #     if not vehicles:
    #         logger.error(
    #             "No <vehicle> elements found in route file."
    #         )
    #         return False

    #     # --------------------------------------------------------------
    #     # Vehicle IDs
    #     # --------------------------------------------------------------

    #     vehicle_ids = [
    #         vehicle.get("id")
    #         for vehicle in vehicles
    #     ]

    #     unique_vehicle_ids = set(
    #         vehicle_ids
    #     )

    #     if len(vehicle_ids) != len(
    #         unique_vehicle_ids
    #     ):
    #         logger.error(
    #             "Duplicate vehicle IDs found."
    #         )
    #         return False

    #     # --------------------------------------------------------------
    #     # Empty routes
    #     # --------------------------------------------------------------

    #     empty_routes = 0

    #     for route in routes:
    #         edges = route.get(
    #             "edges",
    #             "",
    #         ).strip()

    #         if not edges:
    #             empty_routes += 1

    #     if empty_routes:
    #         logger.error(
    #             "Found %d empty routes.",
    #             empty_routes,
    #         )
    #         return False

    #     # --------------------------------------------------------------
    #     # Compare expected vs generated
    #     # --------------------------------------------------------------

    #     expected_count = (
    #         len(self.mapped_demand)
    #         if self.mapped_demand is not None
    #         else 0
    #     )

    #     generated_count = len(
    #         vehicles
    #     )

    #     logger.info(
    #         "Expected mapped trips : %d",
    #         expected_count,
    #     )

    #     logger.info(
    #         "Generated SUMO vehicles: %d",
    #         generated_count,
    #     )

    #     logger.info(
    #         "Generated SUMO routes  : %d",
    #         len(routes),
    #     )

    #     if generated_count != expected_count:
    #         logger.warning(
    #             "Route count differs from mapped demand."
    #         )

    #     logger.info("=" * 70)

    #     if generated_count == expected_count:
    #         logger.info(
    #             "SUMO ROUTE VERIFICATION PASSED"
    #         )
    #         return True

    #     logger.warning(
    #         "SUMO ROUTE VERIFICATION COMPLETED "
    #         "WITH COUNT DIFFERENCE"
    #     )

    #     return False
# ================================================================



    # def verify_routes(self) -> None:
    #     """
    #     Verify that SUMO generated a valid route for every mapped vehicle.
    #     """

    #     logger.info("=" * 70)
    #     logger.info("VERIFYING GENERATED SUMO ROUTES")
    #     logger.info("=" * 70)

    #     if self.mapped_demand is None:
    #         raise RuntimeError(
    #             "No mapped demand available. "
    #             "Run map_nodes_to_edges() first."
    #         )

    #     if not self.route_file.exists():
    #         raise FileNotFoundError(
    #             f"SUMO route file not found: {self.route_file}"
    #         )

    #     root = ET.parse(self.route_file).getroot()

    #     vehicles = root.findall("vehicle")

    #     expected_count = len(self.mapped_demand)
    #     generated_count = len(vehicles)

    #     logger.info(
    #         "Expected mapped trips : %d",
    #         expected_count,
    #     )

    #     logger.info(
    #         "Generated SUMO vehicles: %d",
    #         generated_count,
    #     )

    #     if generated_count != expected_count:
    #         raise RuntimeError(
    #             "Vehicle count mismatch: "
    #             f"expected {expected_count}, "
    #             f"generated {generated_count}"
    #         )

    #     vehicle_ids: set[str] = set()
    #     missing_routes = 0
    #     empty_routes = 0

    #     for vehicle in vehicles:

    #         vehicle_id = vehicle.get("id")

    #         if vehicle_id is None:
    #             raise RuntimeError(
    #                 "Generated vehicle is missing an ID."
    #             )

    #         if vehicle_id in vehicle_ids:
    #             raise RuntimeError(
    #                 f"Duplicate vehicle ID detected: {vehicle_id}"
    #             )

    #         vehicle_ids.add(vehicle_id)

    #         route = vehicle.find("route")

    #         if route is None:
    #             missing_routes += 1
    #             logger.error(
    #                 "Vehicle %s has no <route> element.",
    #                 vehicle_id,
    #             )
    #             continue

    #         edges = route.get("edges", "").strip()

    #         if not edges:
    #             empty_routes += 1
    #             logger.error(
    #                 "Vehicle %s has an empty route.",
    #                 vehicle_id,
    #             )

    #     if missing_routes > 0:
    #         raise RuntimeError(
    #             f"{missing_routes} vehicles are missing routes."
    #         )

    #     if empty_routes > 0:
    #         raise RuntimeError(
    #             f"{empty_routes} vehicles have empty routes."
    #         )

    #     logger.info(
    #         "Generated SUMO routes: %d",
    #         generated_count,
    #     )

    #     logger.info(
    #         "Vehicles with valid routes: %d",
    #         generated_count - missing_routes - empty_routes,
    #     )

    #     logger.info("=" * 70)
    #     logger.info("SUMO ROUTE VERIFICATION PASSED")
    #     logger.info("=" * 70)


    def verify_routes(self) -> None: 
        """ Verify that SUMO generated a valid route for every mapped vehicle. 
        Validation checks: 
        1. Route file exists. 
        2. Number of generated vehicles matches mapped demand. 
        3. Every vehicle has an ID. 
        4. Vehicle IDs are unique. 
        5. Every vehicle contains a <route> element. 
        6. Every route contains at least one edge. 
        """ 

        logger.info("=" * 70) 
        logger.info("VERIFYING GENERATED SUMO ROUTES") 
        logger.info("=" * 70) 

        # -------------------------------------------------------------- 
        # Validate mapped demand 
        # -------------------------------------------------------------- 
        
        if self.mapped_demand is None: 
            raise RuntimeError( 
                "No mapped demand available. " 
                "Run map_nodes_to_edges() first." 
            ) 

        # -------------------------------------------------------------- 
        # Validate route file 
        # -------------------------------------------------------------- 
        
        if not self.route_file.exists(): 
            raise FileNotFoundError( 
                f"SUMO route file not found: {self.route_file}" 
            ) 
        # -------------------------------------------------------------- 
        # Parse route XML 
        # -------------------------------------------------------------- 
        
        try: 
            root = ET.parse(self.route_file).getroot() 
        except ET.ParseError as exc: 
            raise RuntimeError( 
                f"Invalid SUMO route XML: {self.route_file}" 
            ) from exc 

        vehicles = root.findall("vehicle") 

        expected_count = len(self.mapped_demand) 
        generated_count = len(vehicles) 

        logger.info( 
            "Expected mapped trips : %d", 
            expected_count,
        ) 

        logger.info( "Generated SUMO vehicles : %d", 
                generated_count, ) 

        # -------------------------------------------------------------- 
        # Vehicle count validation 
        # -------------------------------------------------------------- 
        
        if generated_count != expected_count: 
            raise RuntimeError( 
                "Vehicle count mismatch: " 
                f"expected {expected_count}, " 
                f"generated {generated_count}" 
            ) 

        # -------------------------------------------------------------- 
        # Validate vehicle IDs and routes 
        # -------------------------------------------------------------- 
        
        vehicle_ids: set[str] = set() 

        missing_routes = 0 
        empty_routes = 0 

        for vehicle in vehicles: 
            vehicle_id = vehicle.get("id") 

            if vehicle_id is None: 
                raise RuntimeError( 
                    "Generated vehicle is missing an ID." 
                )

            if vehicle_id in vehicle_ids: 
                raise RuntimeError( 
                    f"Duplicate vehicle ID detected: {vehicle_id}" 
                ) 

            vehicle_ids.add(vehicle_id) 

            # ---------------------------------------------------------- 
            # Route validation 
            # ---------------------------------------------------------- 
            
            route = vehicle.find("route") 

            if route is None: 
                missing_routes += 1 

                logger.error( 
                    "Vehicle %s has no <route> element.", 
                    vehicle_id, 
                ) 

                continue 

            edges = route.get("edges", "").strip() 

            if not edges: 
                empty_routes += 1 

                logger.error( 
                    "Vehicle %s has an empty route.", 
                    vehicle_id, 
                ) 

        if missing_routes > 0: 
            raise RuntimeError( 
                f"{missing_routes} vehicles are missing routes." 
            )

        if empty_routes > 0: 
            raise RuntimeError( 
                f"{empty_routes} vehicles have empty routes." 
            )

        valid_routes = (
            generated_count
            - missing_routes
            - empty_routes
        )

        logger.info(
            "Generated SUMO routes : %d",
            generated_count,
        )

        logger.info(
            "Vehicles with valid routes: %d",
            valid_routes,
        )

        logger.info("=" * 70)
        logger.info("SUMO ROUTE VERIFICATION PASSED")
        logger.info("=" * 70)
        return True


    # ==================================================================
    # FULL PIPELINE
    # ==================================================================

    def run(self) -> None:
        """
        Execute the complete route-generation pipeline.
        """

        logger.info("=" * 70)
        logger.info("STARTING ROUTE GENERATION PIPELINE")
        logger.info("=" * 70)

        if not self.verify_input_file():
            raise FileNotFoundError(
                "RouteGenerator input validation failed."
            )

        self.load_travel_demand()

        self.load_node_statistics()

        self.load_network()

        self.map_nodes_to_edges()

        self.build_sumo_trip_file()

        self.generate_routes()

        routes_valid = self.verify_routes()

        if not routes_valid:
            raise RuntimeError(
                "SUMO route verification failed."
            )

        logger.info("=" * 70)
        logger.info(
            "ROUTE GENERATION PIPELINE COMPLETED SUCCESSFULLY"
        )
        logger.info("=" * 70)


def main() -> None:
    """Application entry point."""

    generator = RouteGenerator()
    generator.run()


if __name__ == "__main__":
    main()



#  ======== old ============================================
# """
# RouteGenerator

# ├── verify_inputs()  
# ├── load_travel_demand()     # travel_demand.csv
# ├── load_node_statistics()
# ├── load_network()
# ├── convert_lonlat_to_sumo_xy()
# ├── map_nodes_to_edges()
# ├── run()
# """

# from __future__ import annotations

# from pathlib import Path
# import sumolib  # type: ignore

# from src.utils.logger import get_logger
# from src.types import DataFrame, pd, EdgeCandidateList
# from config import (
#     TRAVEL_DEMAND_CSV,
#     SUMO_NETWORK_FILE,
#     SUMO_TRIP_FILE,
#     SUMO_ROUTE_FILE,
#     SUMO_CONFIG_FILE,
#     SUMO_OUTPUT_FILE,
#     EDGE_STATISTICS_CSV,
#     NODE_STATISTICS_CSV,
#     FAILED_ROUTE_MAPPINGS_CSV,
#     EDGE_SEARCH_RADIUS,
# )

# logger = get_logger(__name__)

# class RouteGenerator:
#     """
#     Builds a SUMO route network and generates synthetic traffic demand.
#     """
    
    
#     def __init__(self, 
#                  travel_demand_csv: Path = TRAVEL_DEMAND_CSV, 
#                  net_file: Path = SUMO_NETWORK_FILE,
#                  ) -> None:
        
#         self.travel_demand_csv = travel_demand_csv
#         self.net_file = net_file
#         self.edge_statistics_csv = EDGE_STATISTICS_CSV
#         self.node_statistics_csv = NODE_STATISTICS_CSV
        
#         # Demand files
#         self.trip_file = SUMO_TRIP_FILE 
#         self.route_file = SUMO_ROUTE_FILE 
        
#         # Config and Output
#         self.config_file = SUMO_CONFIG_FILE 
#         self.output_file = SUMO_OUTPUT_FILE 
#         self.edge_search_radius = EDGE_SEARCH_RADIUS
#         self.failed_route_mapping_csv = FAILED_ROUTE_MAPPINGS_CSV
        
#         logger.info("Initialized RouteGenerator...")

#     def verify_input_file(self) -> bool:
#         """Verify input files exist."""
#         if not self.travel_demand_csv.exists():
#             logger.error(f"Travel demand file not found: {self.travel_demand_csv}")
#             return False
        
#         if not self.net_file.exists():
#             logger.error(f"SUMO network file not found: {self.net_file}")
#             return False
            
#         if not self.node_statistics_csv.exists():
#             logger.error(f"Node statistics file not found: {self.node_statistics_csv}")
#             return False
            
#         return True

#     def load_travel_demand(self) -> DataFrame:
#         """Load travel demand CSV into a Pandas DataFrame."""
#         logger.info("=" * 70)
#         logger.info("LOADING TRAVEL DEMAND...")
#         logger.info("=" * 70)
        
#         self.travel_demand = pd.read_csv(self.travel_demand_csv)
#         logger.info(f"Loaded {len(self.travel_demand):,} trips.")
#         return self.travel_demand
    
#     def load_node_statistics(self) -> DataFrame:
#         """Load node statistics."""
#         logger.info("=" * 70)
#         logger.info("LOADING NODE STATISTICS...")
#         logger.info("=" * 70)

#         self.node_statistics = pd.read_csv(self.node_statistics_csv)
#         logger.info(f"Loaded {len(self.node_statistics):,} nodes.")
#         return self.node_statistics

#     def load_network(self) -> None:
#         """Load the SUMO network using sumolib."""
#         logger.info("=" * 70)
#         logger.info("LOADING SUMO NETWORK...")
#         logger.info("=" * 70)
        
#         self.network = sumolib.net.readNet(str(self.net_file))
#         logger.info("Network loaded successfully.")
#         logger.info(f"Network file: {self.net_file}")

#     def convert_lonlat_to_sumo_xy(
#             self,
#             longitude: float,
#             latitude: float,
#     ) -> tuple[float, float]:
#         """
#         Convert geographic longitude/latitude coordinates
#         into the Cartesian coordinate system used by the SUMO network.
#         """
#         x, y = self.network.convertLonLat2XY(longitude, latitude)
#         return x, y

#     def map_nodes_to_edges(self) -> DataFrame:
#             """
#             Map each origin and destination OSM node to the closest valid SUMO edge
#             using spatial transformation and nearest-neighbor search, with strict 
#             error accounting and traceability.
#             """
#             logger.info("=" * 70)
#             logger.info("MAPPING NODES TO EDGES WITH AUDIT")
#             logger.info("=" * 70)

#             # Create an efficient O(1) lookup dictionary for node coordinates
#             node_lookup = (
#                 self.node_statistics
#                 .set_index("osmid")[["x", "y"]]
#                 .to_dict("index")
#             )

#             mapped_mappings = []
#             failed_mappings = []

#             failed_missing_nodes = 0
#             failed_no_origin_edge = 0
#             failed_no_destination_edge = 0

#             total_trips = len(self.travel_demand)
#             for i, (trip_index, trip) in enumerate(self.travel_demand.iterrows()):
#                 origin_node = trip["origin_node"]
#                 destination_node = trip["destination_node"]

#                 # Check if nodes exist in statistics lookup
#                 missing_origin = origin_node not in node_lookup
#                 missing_dest = destination_node not in node_lookup

#                 if missing_origin or missing_dest:
#                     failed_missing_nodes += 1
#                     failed_mappings.append({
#                         "trip_index": trip_index,
#                         "origin_node": origin_node,
#                         "destination_node": destination_node,
#                         "reason": "missing_node_in_statistics"
#                     })
#                     continue

#                 origin = node_lookup[origin_node]
#                 destination = node_lookup[destination_node]

#                 # Convert geographic coords (lon/lat) to SUMO Cartesian XY system
#                 origin_x, origin_y = self.convert_lonlat_to_sumo_xy(
#                     float(origin["x"]), float(origin["y"])
#                 )
#                 destination_x, destination_y = self.convert_lonlat_to_sumo_xy(
#                     float(destination["x"]), float(destination["y"])
#                 )

#                 # Query neighbouring edges within radius
#                 origin_candidates: EdgeCandidateList = self.network.getNeighboringEdges(
#                     origin_x, origin_y, self.edge_search_radius
#                 )
#                 destination_candidates: EdgeCandidateList = self.network.getNeighboringEdges(
#                     destination_x, destination_y, self.edge_search_radius
#                 )

#                 if not origin_candidates:
#                     failed_no_origin_edge += 1
#                     failed_mappings.append({
#                         "trip_index": trip_index,
#                         "origin_node": origin_node,
#                         "destination_node": destination_node,
#                         "reason": "no_origin_edge_found"
#                     })
#                     continue

#                 if not destination_candidates:
#                     failed_no_destination_edge += 1
#                     failed_mappings.append({
#                         "trip_index": trip_index,
#                         "origin_node": origin_node,
#                         "destination_node": destination_node,
#                         "reason": "no_destination_edge_found"
#                     })
#                     continue

#                 # Select closest edge based on Euclidean distance score (index 1 in tuple)
#                 closest_origin = min(origin_candidates, key=lambda item: item[1])
#                 closest_destination = min(destination_candidates, key=lambda item: item[1])

#                 mapped_mappings.append({
#                     "trip_index": trip_index,
#                     "origin_edge": closest_origin[0].getID(),
#                     "destination_edge": closest_destination[0].getID()
#                 })

#                 # Clean log frequency update using safe integer counter `i`
#                 if (i + 1) % 100 == 0 or (i + 1) == total_trips:
#                     logger.info(f"Processed {i + 1} / {total_trips} trips...")

#             # Export failed mappings for audit trail
#             if failed_mappings:
#                 failed_df = pd.DataFrame(failed_mappings)
#                 #  failed_csv_path = DATA_DIR.parent / "sumo" / "failed_route_mappings.csv"
#                 self.failed_route_mapping_csv.parent.mkdir(parents=True, exist_ok=True)
#                 # Ensure output directory exists and save
#                 failed_df.to_csv(self.failed_route_mapping_csv, index=False)
#                 logger.warning(f"Exported {len(failed_df):,} failed mappings to {self.failed_route_mapping_csv}")

#             # Total failed calculation
#             total_failed = (
#                 failed_missing_nodes
#                 + failed_no_origin_edge
#                 + failed_no_destination_edge
#             )

#             # Assign directly using pandas index alignment for maximum safety
#             self.travel_demand = self.travel_demand.copy()
            
#             if mapped_mappings:
#                 mapping_df = pd.DataFrame(mapped_mappings).set_index("trip_index")
#                 self.travel_demand["origin_edge"] = mapping_df["origin_edge"]
#                 self.travel_demand["destination_edge"] = mapping_df["destination_edge"]
                
#                 # Drop unmapped rows
#                 self.travel_demand = self.travel_demand.dropna(
#                     subset=["origin_edge", "destination_edge"]
#                 )
#             else:
#                 raise ValueError("All trip edge mappings failed. Check network boundaries and coordinates.")

#             # Mathematical Validation Assertion
#             assert len(self.travel_demand) + total_failed == total_trips, (
#                 f"Accounting mismatch! Successful ({len(self.travel_demand)}) + "
#                 f"Failed ({total_failed}) does not equal Total Trips ({total_trips})."
#             )

#             logger.info("=" * 50)
#             logger.info(f"Successfully mapped: {len(self.travel_demand):,} trips.")
#             logger.info(f"Missing nodes: {failed_missing_nodes:,}")
#             logger.info(f"No origin edge: {failed_no_origin_edge:,}")
#             logger.info(f"No destination edge: {failed_no_destination_edge:,}")
#             logger.info(f"Total failed: {total_failed:,} (Audited & Saved)")
#             logger.info("=" * 50)
            
#             logger.info("First 5 mapped trips:")
#             logger.info(
#                 self.travel_demand[[
#                     "origin_node", "origin_edge", 
#                     "destination_node", "destination_edge"
#                 ]].head()
#             )
        
#             return self.travel_demand

#     def run(self) -> None:
#         if not self.verify_input_file():
#             return

#         self.load_travel_demand()
#         self.load_node_statistics()
#         self.load_network()
#         self.map_nodes_to_edges()

#         logger.info("=" * 70)
#         logger.info("ROUTE GENERATOR INITIALIZATION COMPLETE")
#         logger.info("=" * 70)

# def main() -> None:
#     builder = RouteGenerator()
#     builder.run()

# if __name__ == "__main__":
#     main()
