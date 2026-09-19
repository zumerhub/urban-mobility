"""
Build a leakage-safe trip-level ETA modelling dataset.

The first ETA problem is departure-time prediction: estimate total trip
duration using fields available at or before the vehicle departs.
"""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from config import (
    MORNING_PEAK_END,
    MORNING_PEAK_START,
    REPORT_DIR,
    SUMO_NETWORK_FILE,
    SUMO_ROUTE_FILE,
    TRAVEL_DEMAND_CSV,
)
from src.types import DataFrame, pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineering:
    """Create one row per completed SUMO trip for ETA modelling."""

    target_column = "trip_duration_seconds"

    numeric_predictors = [
        "depart_seconds",
        "depart_hour",
        "depart_minute_of_day",
        "depart_time_sin",
        "depart_time_cos",
        "is_morning_peak",
        "is_evening_peak",
        "priority",
        "route_edge_count",
        "planned_route_length_m",
        "planned_free_flow_time_s",
        "planned_avg_edge_speed_mps",
    ]

    categorical_predictors = [
        "vehicle_type",
        "demand_vehicle_type",
    ]

    metadata_columns = [
        "vehicle_id",
        "origin_node",
        "destination_node",
        "trip_status",
        "route_first_edge_id",
        "route_last_edge_id",
        "route_missing_edge_count",
    ]

    outcome_columns = [
        "outcome_arrival_seconds",
        "outcome_depart_delay_seconds",
        "outcome_actual_route_length_m",
        "outcome_waiting_time_seconds",
        "outcome_waiting_count",
        "outcome_time_loss_seconds",
        "outcome_depart_lane",
        "outcome_arrival_lane",
        "outcome_depart_speed_mps",
        "outcome_arrival_speed_mps",
        "outcome_speed_factor",
        "outcome_derived_speed_mps",
    ]

    excluded_traffic_feature_sources = {
        "simulation_edge_metrics.csv": (
            "Generated from whole-run edgeData.xml aggregates spanning "
            "0-71995 seconds, so values include conditions after each "
            "vehicle's departure."
        ),
        "simulation_queue_metrics.csv": (
            "Generated from whole-run queue.xml aggregates, so values are "
            "not aligned to each vehicle's departure time."
        ),
    }

    def __init__(
        self,
        trip_metrics_file: Path | None = None,
        travel_demand_file: Path | None = None,
        route_file: Path | None = None,
        network_file: Path | None = None,
        report_dir: Path | None = None,
    ) -> None:
        self.report_dir = report_dir or REPORT_DIR
        self.trip_metrics_file = trip_metrics_file or (
            self.report_dir / "simulation_trip_metrics.csv"
        )
        self.travel_demand_file = travel_demand_file or TRAVEL_DEMAND_CSV
        self.route_file = route_file or SUMO_ROUTE_FILE
        self.network_file = network_file or SUMO_NETWORK_FILE

        self.dataset_file = self.report_dir / "eta_dataset.csv"
        self.schema_file = self.report_dir / "eta_dataset_schema.json"

        self.dataset: DataFrame | None = None
        self.validation_report: dict[str, Any] = {}

    def load_trip_metrics(self) -> DataFrame:
        """Load authoritative completed-trip metrics."""

        if not self.trip_metrics_file.exists():
            raise FileNotFoundError(
                f"Trip metrics not found: {self.trip_metrics_file}"
            )

        trips = pd.read_csv(self.trip_metrics_file)
        self._require_columns(
            trips,
            [
                "vehicle_id",
                "duration_s",
                "arrival_s",
                "route_length_m",
                "waiting_time_s",
                "waiting_count",
                "time_loss_s",
            ],
            "simulation trip metrics",
        )

        trips["vehicle_id"] = trips["vehicle_id"].astype(str)
        return trips

    def load_travel_demand(self) -> DataFrame:
        """Load planned travel-demand fields available before departure."""

        if not self.travel_demand_file.exists():
            raise FileNotFoundError(
                f"Travel demand not found: {self.travel_demand_file}"
            )

        demand = pd.read_csv(self.travel_demand_file)
        self._require_columns(
            demand,
            [
                "vehicle_id",
                "vehicle_type",
                "departure_time",
                "origin_node",
                "destination_node",
                "priority",
                "trip_status",
            ],
            "travel demand",
        )

        demand["vehicle_id"] = demand["vehicle_id"].astype(str)
        return demand.rename(
            columns={
                "vehicle_type": "demand_vehicle_type",
                "departure_time": "demand_departure_seconds",
            }
        )

    def load_edge_lookup(self) -> dict[str, dict[str, float]]:
        """Load static SUMO edge length and speed from the network file."""

        if not self.network_file.exists():
            raise FileNotFoundError(
                f"SUMO network not found: {self.network_file}"
            )

        edge_lookup: dict[str, dict[str, float]] = {}

        for _, edge in ET.iterparse(self.network_file, events=("end",)):
            if edge.tag != "edge" or "function" in edge.attrib:
                continue

            lanes = edge.findall("lane")
            lengths = [
                float(lane.attrib["length"])
                for lane in lanes
                if "length" in lane.attrib
            ]
            speeds = [
                float(lane.attrib["speed"])
                for lane in lanes
                if "speed" in lane.attrib
            ]

            if lengths and speeds and "id" in edge.attrib:
                mean_speed = sum(speeds) / len(speeds)
                edge_length = max(lengths)
                edge_lookup[edge.attrib["id"]] = {
                    "length_m": edge_length,
                    "speed_mps": mean_speed,
                    "free_flow_time_s": edge_length / mean_speed
                    if mean_speed > 0
                    else math.nan,
                }

            edge.clear()

        if not edge_lookup:
            raise ValueError("No regular edges found in SUMO network.")

        return edge_lookup

    def load_route_features(
        self,
        edge_lookup: dict[str, dict[str, float]],
    ) -> DataFrame:
        """Parse planned route features available before vehicle departure."""

        if not self.route_file.exists():
            raise FileNotFoundError(f"Route file not found: {self.route_file}")

        rows: list[dict[str, Any]] = []

        root = ET.parse(self.route_file).getroot()
        for vehicle in root.findall(".//vehicle"):
            vehicle_id = vehicle.attrib.get("id")
            route = vehicle.find("route")
            if vehicle_id is None or route is None:
                continue

            edges = route.attrib.get("edges", "").split()
            lengths = [
                edge_lookup[edge_id]["length_m"]
                for edge_id in edges
                if edge_id in edge_lookup
            ]
            free_flow_times = [
                edge_lookup[edge_id]["free_flow_time_s"]
                for edge_id in edges
                if edge_id in edge_lookup
            ]
            missing_edge_count = len(edges) - len(lengths)
            planned_length = sum(lengths)
            planned_free_flow = sum(free_flow_times)

            rows.append(
                {
                    "vehicle_id": str(vehicle_id),
                    "vehicle_type": vehicle.attrib.get("type"),
                    "depart_seconds": float(vehicle.attrib["depart"]),
                    "route_edge_count": len(edges),
                    "planned_route_length_m": planned_length,
                    "planned_free_flow_time_s": planned_free_flow,
                    "planned_avg_edge_speed_mps": (
                        planned_length / planned_free_flow
                        if planned_free_flow > 0
                        else math.nan
                    ),
                    "route_first_edge_id": edges[0] if edges else None,
                    "route_last_edge_id": edges[-1] if edges else None,
                    "route_missing_edge_count": missing_edge_count,
                }
            )

        routes = pd.DataFrame(rows)
        if routes.empty:
            raise ValueError("No vehicle routes found in routes.rou.xml.")

        return routes

    def create_features(self) -> DataFrame:
        """Build and validate the ETA dataset."""

        logger.info("=" * 70)
        logger.info("BUILDING ETA DATASET")
        logger.info("=" * 70)

        trips = self.load_trip_metrics()
        demand = self.load_travel_demand()
        edge_lookup = self.load_edge_lookup()
        routes = self.load_route_features(edge_lookup)

        self._validate_unique_vehicle_ids(trips, "trip metrics")
        self._validate_unique_vehicle_ids(demand, "travel demand")
        self._validate_unique_vehicle_ids(routes, "routes")

        trips_for_join = trips.drop(columns=["vehicle_type"], errors="ignore")

        dataset = routes.merge(demand, on="vehicle_id", how="inner")
        dataset = dataset.merge(trips_for_join, on="vehicle_id", how="inner")

        dataset = self._rename_outcome_columns(dataset)
        dataset[self.target_column] = pd.to_numeric(
            dataset[self.target_column], errors="coerce"
        )
        dataset = self._add_departure_time_features(dataset)

        ordered_columns = (
            ["vehicle_id", self.target_column]
            + self.numeric_predictors
            + self.categorical_predictors
            + [
                column
                for column in self.metadata_columns
                if column != "vehicle_id"
            ]
            + self.outcome_columns
        )
        ordered_columns = [
            column for column in ordered_columns if column in dataset.columns
        ]
        dataset = dataset[ordered_columns].sort_values(
            "depart_seconds"
        ).reset_index(drop=True)

        self.validate_dataset(dataset, trips, demand, routes)
        self.dataset = dataset

        return dataset

    def _rename_outcome_columns(self, dataset: DataFrame) -> DataFrame:
        """Rename post-trip tripinfo fields so leakage is visible."""

        return dataset.rename(
            columns={
                "duration_s": self.target_column,
                "arrival_s": "outcome_arrival_seconds",
                "depart_delay_s": "outcome_depart_delay_seconds",
                "route_length_m": "outcome_actual_route_length_m",
                "waiting_time_s": "outcome_waiting_time_seconds",
                "waiting_count": "outcome_waiting_count",
                "time_loss_s": "outcome_time_loss_seconds",
                "departLane": "outcome_depart_lane",
                "arrivalLane": "outcome_arrival_lane",
                "depart_speed_mps": "outcome_depart_speed_mps",
                "arrival_speed_mps": "outcome_arrival_speed_mps",
                "speedFactor": "outcome_speed_factor",
                "derived_speed_mps": "outcome_derived_speed_mps",
            }
        )

    def _add_departure_time_features(self, dataset: DataFrame) -> DataFrame:
        """Add cyclic and peak-period encodings from departure seconds."""

        seconds_per_day = 24 * 3600
        dataset["depart_seconds"] = pd.to_numeric(
            dataset["depart_seconds"], errors="coerce"
        )
        dataset["depart_hour"] = (dataset["depart_seconds"] // 3600).astype(
            int
        )
        dataset["depart_minute_of_day"] = (
            dataset["depart_seconds"] // 60
        ).astype(int)
        angle = 2 * math.pi * dataset["depart_seconds"] / seconds_per_day
        dataset["depart_time_sin"] = angle.apply(math.sin)
        dataset["depart_time_cos"] = angle.apply(math.cos)
        dataset["is_morning_peak"] = (
            dataset["depart_seconds"].between(
                MORNING_PEAK_START,
                MORNING_PEAK_END,
                inclusive="left",
            )
        ).astype(int)
        dataset["is_evening_peak"] = (
            dataset["depart_seconds"] >= 16 * 3600
        ).astype(int)
        return dataset

    def validate_dataset(
        self,
        dataset: DataFrame,
        trips: DataFrame,
        demand: DataFrame,
        routes: DataFrame,
    ) -> None:
        """Validate row counts, joins, missing values, and leakage exclusions."""

        expected_rows = len(trips)
        missing_report = dataset.isna().sum().to_dict()
        numeric_columns = [self.target_column] + self.numeric_predictors

        if len(dataset) != expected_rows:
            raise ValueError(
                "ETA dataset row count mismatch: "
                f"expected {expected_rows}, got {len(dataset)}."
            )
        if dataset["vehicle_id"].duplicated().any():
            raise ValueError("Duplicate vehicle IDs found in ETA dataset.")
        if dataset[self.target_column].isna().any():
            raise ValueError("Missing target values found in ETA dataset.")

        for column in numeric_columns:
            if column not in dataset.columns:
                raise ValueError(f"Missing numeric predictor: {column}")
            parsed = pd.to_numeric(dataset[column], errors="coerce")
            if parsed.isna().any():
                raise ValueError(
                    f"Numeric column has unparseable values: {column}"
                )

        for column in self.categorical_predictors:
            if column not in dataset.columns:
                raise ValueError(f"Missing categorical predictor: {column}")
            if dataset[column].isna().any():
                raise ValueError(
                    f"Categorical predictor has missing values: {column}"
                )

        if dataset["route_missing_edge_count"].sum() != 0:
            raise ValueError(
                "At least one route edge was missing from the SUMO network."
            )

        leakage_columns = set(self.outcome_columns)
        predictor_columns = set(self.numeric_predictors).union(
            self.categorical_predictors
        )
        leaked = sorted(leakage_columns.intersection(predictor_columns))
        if leaked:
            raise ValueError(
                f"Outcome columns included as predictors: {leaked}"
            )

        trip_ids = set(trips["vehicle_id"].astype(str))
        demand_ids = set(demand["vehicle_id"].astype(str))
        route_ids = set(routes["vehicle_id"].astype(str))
        dataset_ids = set(dataset["vehicle_id"].astype(str))

        self.validation_report = {
            "row_count": int(len(dataset)),
            "column_count": int(len(dataset.columns)),
            "expected_completed_trips": int(expected_rows),
            "unique_vehicle_ids": int(dataset["vehicle_id"].nunique()),
            "missing_values": {
                column: int(count)
                for column, count in missing_report.items()
                if int(count) > 0
            },
            "join_validation": {
                "trip_ids_missing_from_dataset": len(trip_ids - dataset_ids),
                "demand_ids_missing_from_dataset": len(
                    demand_ids - dataset_ids
                ),
                "route_ids_missing_from_dataset": len(route_ids - dataset_ids),
                "dataset_ids_missing_from_trips": len(dataset_ids - trip_ids),
                "dataset_ids_missing_from_demand": len(
                    dataset_ids - demand_ids
                ),
                "dataset_ids_missing_from_routes": len(
                    dataset_ids - route_ids
                ),
            },
            "leakage_checks": {
                "outcome_columns_excluded_from_model_features": True,
                "whole_run_edge_metrics_excluded": True,
                "whole_run_queue_metrics_excluded": True,
                "arrival_and_duration_derived_fields_excluded": True,
            },
            "target_summary": {
                "mean": float(dataset[self.target_column].mean()),
                "median": float(dataset[self.target_column].median()),
                "std": float(dataset[self.target_column].std()),
                "min": float(dataset[self.target_column].min()),
                "max": float(dataset[self.target_column].max()),
            },
        }

    def export_dataset(self) -> list[Path]:
        """Write ETA dataset and schema/validation metadata."""

        if self.dataset is None:
            raise RuntimeError("ETA dataset has not been created.")

        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.dataset.to_csv(self.dataset_file, index=False)

        schema = {
            "prediction_definition": (
                "Departure-time ETA: predict total completed trip duration "
                "from fields available at or before vehicle departure."
            ),
            "target": self.target_column,
            "model_features": self.numeric_predictors
            + self.categorical_predictors,
            "numeric_predictors": self.numeric_predictors,
            "categorical_predictors": self.categorical_predictors,
            "metadata_columns": self.metadata_columns,
            "post_trip_outcome_columns_excluded_from_modelling": (
                self.outcome_columns
            ),
            "traffic_features_considered_but_excluded": (
                self.excluded_traffic_feature_sources
            ),
            "validation": self.validation_report,
            "recommended_baseline_for_next_milestone": (
                "Use the training-set median trip_duration_seconds as the "
                "first naive baseline; also report training-set mean as a "
                "secondary constant baseline."
            ),
        }
        with open(self.schema_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)

        logger.info("ETA dataset written: %s", self.dataset_file)
        logger.info("ETA schema written: %s", self.schema_file)

        return [self.dataset_file, self.schema_file]

    def run(self) -> DataFrame:
        """Execute the dataset-build pipeline."""

        dataset = self.create_features()
        self.export_dataset()
        logger.info("ETA feature dataset build completed successfully.")
        return dataset

    @staticmethod
    def _require_columns(
        data: DataFrame,
        required_columns: list[str],
        label: str,
    ) -> None:
        missing = [
            column for column in required_columns if column not in data.columns
        ]
        if missing:
            raise ValueError(f"Missing {label} columns: {missing}")

    @staticmethod
    def _validate_unique_vehicle_ids(data: DataFrame, label: str) -> None:
        if "vehicle_id" not in data.columns:
            raise ValueError(f"{label} is missing vehicle_id.")
        duplicates = data["vehicle_id"][data["vehicle_id"].duplicated()]
        if not duplicates.empty:
            raise ValueError(
                f"Duplicate vehicle IDs in {label}: "
                f"{duplicates.head(10).tolist()}"
            )


def main() -> None:
    """Application entry point."""

    FeatureEngineering().run()


if __name__ == "__main__":
    main()
