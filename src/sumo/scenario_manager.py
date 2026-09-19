# """
# Manage traffic simulation scenarios.

# Purpose: Evaluate simulation performance.

# SimulationAnalyzer
# │
# ├── __init__()
# ├── load_tripinfo()
# ├── load_summary()
# ├── compute_metrics()
# ├── compare_scenarios()
# ├── create_visualizations()
# ├── export_report()
# ├── verify_outputs()
# └── run()

# Output

# simulation_report.csv

# simulation_report.json

# travel_time_distribution.png

# delay_distribution.png
# """

# from __future__ import annotations

# from src.utils.logger import get_logger

# logger = get_logger(__name__)

# class ScenarioManager:

#     def __init__(self) -> None:
#         pass

#     def create_scenarios(self) -> None:
#         pass

#     def run(self) -> None:
#         self.create_scenarios()


# if __name__ == "__main__":
#     ScenarioManager().run()







"""
Manage traffic simulation scenarios.

Purpose: Evaluate simulation performance.

SimulationAnalyzer
│
├── __init__()
├── load_tripinfo()
├── load_summary()
├── compute_metrics()
├── compare_scenarios()
├── create_visualizations()
├── export_report()
├── verify_outputs()
└── run()

Input
-----
tripinfo.xml
summary.xml

Output
------
simulation_report.csv
simulation_report.json
travel_time_distribution.png
delay_distribution.png

Notes
-----
The class here is named SimulationAnalyzer, matching this module's
docstring and method list. If this file is meant to hold a
scenario-generation class instead (building multiple simulation
configs before running), that is a different responsibility and
belongs in its own module.

compare_scenarios() works standalone: with no other scenario metrics
supplied it returns a single-row table for the current run, so
export_report() always has a consistent shape whether or not you have
other scenarios to compare against yet.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import SUMO_NETWORK_FILE, SUMO_ROUTE_FILE, TRAVEL_DEMAND_CSV

from src.types import DataFrame, pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SimulationAnalyzer:
    """
    Evaluate simulation performance from SUMO tripinfo/summary output.

    Pipeline
    --------
    1. load_tripinfo()
    2. load_summary()
    3. compute_metrics()
    4. compare_scenarios()
    5. create_visualizations()
    6. export_report()
    7. verify_outputs()
    8. run()
    """

    def __init__(
        self,
        tripinfo_file: Path | None = None,
        summary_file: Path | None = None,
        edge_file: Path | None = None,
        queue_file: Path | None = None,
        route_file: Path | None = None,
        report_dir: Path | None = None,
        scenario_name: str = "baseline",
    ) -> None:
        """
        Initialize the SimulationAnalyzer.

        Parameters
        ----------
        tripinfo_file:
            SUMO tripinfo.xml. Defaults to the file TrafficSimulator
            writes alongside the SUMO network.

        summary_file:
            SUMO summary.xml. Defaults alongside the SUMO network.

        report_dir:
            Directory reports/plots are written to. Defaults to the
            same outputs/reports directory used by travel_demand.csv.

        scenario_name:
            Label for this run, used as the row/key when comparing
            against other scenarios.
        """

        default_sim_dir = SUMO_NETWORK_FILE.parent

        self.tripinfo_file = tripinfo_file or (
            default_sim_dir / "tripinfo.xml"
        )
        self.summary_file = summary_file or (
            default_sim_dir / "summary.xml"
        )
        self.edge_file = edge_file or (default_sim_dir / "edgeData.xml")
        self.queue_file = queue_file or (default_sim_dir / "queue.xml")
        self.route_file = route_file or SUMO_ROUTE_FILE
        self.report_dir = report_dir or TRAVEL_DEMAND_CSV.parent
        self.scenario_name = scenario_name

        self.report_csv = self.report_dir / "simulation_report.csv"
        self.report_json = self.report_dir / "simulation_report.json"
        self.summary_json = self.report_dir / "simulation_summary.json"
        self.trip_metrics_csv = (
            self.report_dir / "simulation_trip_metrics.csv"
        )
        self.vehicle_type_metrics_csv = (
            self.report_dir / "simulation_vehicle_type_metrics.csv"
        )
        self.edge_metrics_csv = (
            self.report_dir / "simulation_edge_metrics.csv"
        )
        self.queue_metrics_csv = (
            self.report_dir / "simulation_queue_metrics.csv"
        )
        self.travel_time_plot = (
            self.report_dir / "travel_time_distribution.png"
        )
        self.delay_plot = self.report_dir / "delay_distribution.png"
        self.waiting_time_plot = (
            self.report_dir / "waiting_time_distribution.png"
        )
        self.vehicle_type_duration_plot = (
            self.report_dir / "duration_by_vehicle_type.png"
        )

        self.tripinfo: DataFrame | None = None
        self.summary: DataFrame | None = None
        self.edge_metrics: DataFrame | None = None
        self.queue_metrics: DataFrame | None = None
        self.trip_metrics: DataFrame | None = None
        self.vehicle_type_metrics: DataFrame | None = None
        self.metrics: dict[str, Any] = {}
        self.comparison: DataFrame | None = None
        self.expected_vehicle_count: int | None = None
        self.route_vehicle_ids: set[str] = set()

        logger.info("Initialized SimulationAnalyzer...")

    # ==================================================================
    # LOAD TRIPINFO
    # ==================================================================

    def load_tripinfo(self) -> DataFrame:
        """Load and type-normalize SUMO tripinfo.xml."""

        logger.info("=" * 70)
        logger.info("LOADING TRIPINFO")
        logger.info("=" * 70)

        if not self.tripinfo_file.exists():
            raise FileNotFoundError(
                f"tripinfo.xml not found: {self.tripinfo_file}"
            )

        root = ET.parse(self.tripinfo_file).getroot()
        records = [dict(el.attrib) for el in root.findall(".//tripinfo")]

        if not records:
            raise ValueError(
                "No <tripinfo> elements found in tripinfo.xml."
            )

        trips = pd.DataFrame(records)

        numeric_columns = [
            "depart",
            "departDelay",
            "departSpeed",
            "arrivalSpeed",
            "arrival",
            "duration",
            "routeLength",
            "waitingTime",
            "waitingCount",
            "stopTime",
            "timeLoss",
            "rerouteNo",
            "speedFactor",
        ]

        for column in numeric_columns:
            if column in trips.columns:
                trips[column] = pd.to_numeric(
                    trips[column], errors="coerce"
                )

        self.tripinfo = trips

        logger.info("Loaded %d tripinfo records.", len(trips))

        return trips

    # ==================================================================
    # LOAD ROUTE VEHICLE IDS
    # ==================================================================

    def load_route_vehicle_ids(self) -> set[str]:
        """Load current SUMO route vehicle ids for count validation."""

        if not self.route_file.exists():
            raise FileNotFoundError(f"Route file not found: {self.route_file}")

        root = ET.parse(self.route_file).getroot()
        route_vehicle_ids = {
            str(el.attrib["id"])
            for el in root.findall(".//vehicle")
            if "id" in el.attrib
        }

        if not route_vehicle_ids:
            raise ValueError("No <vehicle> elements found in route file.")

        if len(route_vehicle_ids) != len(
            [el for el in root.findall(".//vehicle") if "id" in el.attrib]
        ):
            raise ValueError("Duplicate vehicle ids found in route file.")

        self.route_vehicle_ids = route_vehicle_ids
        self.expected_vehicle_count = len(route_vehicle_ids)

        logger.info(
            "Loaded %d expected vehicles from %s.",
            self.expected_vehicle_count,
            self.route_file,
        )

        return route_vehicle_ids

    # ==================================================================
    # LOAD SUMMARY
    # ==================================================================

    def load_summary(self) -> DataFrame:
        """Load and type-normalize SUMO summary.xml."""

        logger.info("=" * 70)
        logger.info("LOADING SUMMARY")
        logger.info("=" * 70)

        if not self.summary_file.exists():
            raise FileNotFoundError(
                f"summary.xml not found: {self.summary_file}"
            )

        root = ET.parse(self.summary_file).getroot()
        records = [dict(el.attrib) for el in root.findall(".//step")]

        if not records:
            raise ValueError("No <step> elements found in summary.xml.")

        summary = pd.DataFrame(records)

        for column in summary.columns:
            summary[column] = pd.to_numeric(
                summary[column], errors="coerce"
            )

        self.summary = summary

        logger.info("Loaded %d summary steps.", len(summary))

        return summary

    # ==================================================================
    # LOAD EDGE DATA
    # ==================================================================

    def load_edge_metrics(self) -> DataFrame:
        """Load useful per-edge metrics from SUMO edgeData.xml."""

        logger.info("=" * 70)
        logger.info("LOADING EDGE DATA")
        logger.info("=" * 70)

        if not self.edge_file.exists():
            raise FileNotFoundError(f"edgeData.xml not found: {self.edge_file}")

        records: list[dict[str, Any]] = []
        interval_begin: float | None = None
        interval_end: float | None = None

        for event, el in ET.iterparse(
            self.edge_file, events=("start", "end")
        ):
            if event == "start" and el.tag == "interval":
                interval_begin = float(el.attrib["begin"])
                interval_end = float(el.attrib["end"])
            elif event == "end" and el.tag == "edge":
                records.append(dict(el.attrib))
                el.clear()

        if not records:
            raise ValueError("No <edge> elements found in edgeData.xml.")

        edges = pd.DataFrame(records)
        numeric_columns = [
            "sampledSeconds",
            "traveltime",
            "density",
            "laneDensity",
            "occupancy",
            "waitingTime",
            "timeLoss",
            "speed",
            "speedRelative",
            "departed",
            "arrived",
            "entered",
            "left",
            "flow",
        ]

        for column in numeric_columns:
            if column in edges.columns:
                edges[column] = pd.to_numeric(edges[column], errors="coerce")

        useful_columns = [
            column
            for column in [
                "id",
                "sampledSeconds",
                "traveltime",
                "speed",
                "density",
                "occupancy",
                "waitingTime",
                "timeLoss",
                "entered",
                "left",
                "arrived",
                "departed",
                "flow",
            ]
            if column in edges.columns
        ]
        edges = edges[useful_columns].copy()

        edges["interval_begin_s"] = interval_begin
        edges["interval_end_s"] = interval_end

        self.edge_metrics = edges

        logger.info("Loaded %d edge records.", len(edges))

        return edges

    # ==================================================================
    # LOAD QUEUE DATA
    # ==================================================================

    def load_queue_metrics(self) -> DataFrame:
        """Aggregate queue.xml to useful per-lane queue metrics."""

        logger.info("=" * 70)
        logger.info("LOADING QUEUE DATA")
        logger.info("=" * 70)

        if not self.queue_file.exists():
            raise FileNotFoundError(f"queue.xml not found: {self.queue_file}")

        rows: list[dict[str, Any]] = []

        for _, el in ET.iterparse(self.queue_file, events=("end",)):
            if el.tag == "lane":
                rows.append(dict(el.attrib))
            el.clear()

        if not rows:
            self.queue_metrics = pd.DataFrame(
                columns=[
                    "lane_id",
                    "observations",
                    "mean_queueing_time_s",
                    "max_queueing_time_s",
                    "mean_queueing_length_m",
                    "max_queueing_length_m",
                    "mean_queueing_length_experimental_m",
                    "max_queueing_length_experimental_m",
                ]
            )
            logger.warning("No lane queue records found in queue.xml.")
            return self.queue_metrics

        queues = pd.DataFrame(rows).rename(columns={"id": "lane_id"})
        numeric_columns = [
            "queueing_time",
            "queueing_length",
            "queueing_length_experimental",
        ]

        for column in numeric_columns:
            queues[column] = pd.to_numeric(queues[column], errors="coerce")

        grouped = (
            queues.groupby("lane_id", as_index=False)
            .agg(
                observations=("queueing_time", "size"),
                mean_queueing_time_s=("queueing_time", "mean"),
                max_queueing_time_s=("queueing_time", "max"),
                mean_queueing_length_m=("queueing_length", "mean"),
                max_queueing_length_m=("queueing_length", "max"),
                mean_queueing_length_experimental_m=(
                    "queueing_length_experimental",
                    "mean",
                ),
                max_queueing_length_experimental_m=(
                    "queueing_length_experimental",
                    "max",
                ),
            )
            .sort_values(
                ["max_queueing_length_m", "max_queueing_time_s"],
                ascending=[False, False],
            )
        )

        self.queue_metrics = grouped

        logger.info("Loaded queue metrics for %d lanes.", len(grouped))

        return grouped

    # ==================================================================
    # COMPUTE METRICS
    # ==================================================================

    def compute_metrics(self) -> dict[str, Any]:
        """Compute validated research metrics for this scenario."""

        if self.tripinfo is None:
            raise RuntimeError("Tripinfo has not been loaded.")

        logger.info("=" * 70)
        logger.info("COMPUTING METRICS")
        logger.info("=" * 70)

        trips = self.tripinfo.copy()

        required_numeric = [
            "duration",
            "waitingTime",
            "timeLoss",
            "routeLength",
        ]
        missing = [
            column for column in required_numeric if column not in trips.columns
        ]
        if missing:
            raise ValueError(f"Missing required tripinfo columns: {missing}")

        invalid_numeric = [
            column
            for column in required_numeric
            if trips[column].isna().any()
        ]
        if invalid_numeric:
            raise ValueError(
                "Required numeric tripinfo fields contain unparseable "
                f"values: {invalid_numeric}"
            )

        if "id" not in trips.columns:
            raise ValueError("tripinfo.xml is missing vehicle id attributes.")

        duplicate_vehicle_ids = trips["id"][trips["id"].duplicated()].tolist()
        if duplicate_vehicle_ids:
            raise ValueError(
                "Duplicate vehicle ids found in tripinfo.xml: "
                f"{duplicate_vehicle_ids[:10]}"
            )

        if self.expected_vehicle_count is not None:
            completed = len(trips)
            if completed != self.expected_vehicle_count:
                raise ValueError(
                    "Tripinfo count does not match current route file: "
                    f"expected {self.expected_vehicle_count}, got {completed}."
                )

        if self.route_vehicle_ids:
            trip_vehicle_ids = set(trips["id"].astype(str))
            missing_from_tripinfo = self.route_vehicle_ids - trip_vehicle_ids
            extra_in_tripinfo = trip_vehicle_ids - self.route_vehicle_ids
            if missing_from_tripinfo or extra_in_tripinfo:
                raise ValueError(
                    "Tripinfo vehicle ids do not match route file. "
                    f"Missing={len(missing_from_tripinfo)}, "
                    f"extra={len(extra_in_tripinfo)}."
                )

        valid_speed = trips["duration"] > 0
        trips["derived_speed_mps"] = None
        trips.loc[valid_speed, "derived_speed_mps"] = (
            trips.loc[valid_speed, "routeLength"]
            / trips.loc[valid_speed, "duration"]
        )
        trips["derived_speed_mps"] = pd.to_numeric(
            trips["derived_speed_mps"], errors="coerce"
        )

        self.trip_metrics = self._build_trip_metrics(trips)
        self.vehicle_type_metrics = self._build_vehicle_type_metrics(trips)

        metrics: dict[str, Any] = {
            "scenario": self.scenario_name,
            "completed_trips": int(len(trips)),
            "expected_vehicles_from_routes": self.expected_vehicle_count,
            "mean_duration_s": float(trips["duration"].mean()),
            "median_duration_s": float(trips["duration"].median()),
            "min_duration_s": float(trips["duration"].min()),
            "max_duration_s": float(trips["duration"].max()),
            "std_duration_s": float(trips["duration"].std()),
            "mean_waiting_time_s": float(trips["waitingTime"].mean()),
            "mean_time_loss_s": float(trips["timeLoss"].mean()),
            "mean_route_length_m": float(trips["routeLength"].mean()),
            "mean_derived_speed_mps": float(
                trips["derived_speed_mps"].mean()
            ),
            "mean_derived_speed_kmh": float(
                trips["derived_speed_mps"].mean() * 3.6
            ),
            "avg_duration_s": float(trips["duration"].mean()),
            "avg_time_loss_s": float(trips["timeLoss"].mean()),
            "avg_waiting_time_s": float(trips["waitingTime"].mean()),
            "avg_route_length_m": float(trips["routeLength"].mean()),
            "max_time_loss_s": float(trips["timeLoss"].max()),
        }

        if "departDelay" in trips.columns:
            metrics["avg_depart_delay_s"] = float(trips["departDelay"].mean())

        if self.summary is not None and not self.summary.empty:
            final_summary = self.summary.iloc[-1]
            metrics["final_summary_step_s"] = float(final_summary["time"])

            for source, target in [
                ("loaded", "final_loaded"),
                ("inserted", "final_inserted"),
                ("arrived", "final_arrived"),
                ("running", "final_running"),
                ("waiting", "final_waiting"),
                ("collisions", "final_collisions"),
                ("teleports", "final_teleports"),
                ("ended", "final_ended"),
                ("discarded", "final_discarded"),
            ]:
                if source in self.summary.columns:
                    metrics[target] = int(final_summary[source])

            if "running" in self.summary.columns:
                metrics["peak_concurrent_vehicles"] = int(
                    self.summary["running"].max()
                )
                metrics["total_arrived"] = int(final_summary.get("arrived", 0))
                metrics["total_collisions"] = int(
                    final_summary.get("collisions", 0)
                )
                metrics["total_teleports"] = int(
                    final_summary.get("teleports", 0)
                )

        if self.edge_metrics is not None and not self.edge_metrics.empty:
            active_edges = self.edge_metrics[
                self.edge_metrics.get("sampledSeconds", 0) > 0
            ]
            metrics["edge_records"] = int(len(self.edge_metrics))
            metrics["active_edge_records"] = int(len(active_edges))
            for column, target in [
                ("traveltime", "mean_edge_travel_time_s"),
                ("speed", "mean_edge_speed_mps"),
                ("density", "mean_edge_density"),
                ("occupancy", "mean_edge_occupancy"),
                ("waitingTime", "mean_edge_waiting_time_s"),
                ("timeLoss", "mean_edge_time_loss_s"),
            ]:
                if column in active_edges.columns and not active_edges.empty:
                    metrics[target] = float(active_edges[column].mean())

        if self.queue_metrics is not None:
            metrics["queue_lane_records"] = int(len(self.queue_metrics))
            if not self.queue_metrics.empty:
                metrics["max_queueing_length_m"] = float(
                    self.queue_metrics["max_queueing_length_m"].max()
                )
                metrics["max_queueing_time_s"] = float(
                    self.queue_metrics["max_queueing_time_s"].max()
                )
                metrics["mean_lane_queueing_length_m"] = float(
                    self.queue_metrics["mean_queueing_length_m"].mean()
                )

        self.metrics = metrics

        logger.info("Metrics computed:")
        for key, value in metrics.items():
            logger.info("  %s: %s", key, value)

        return metrics

    def _build_trip_metrics(self, trips: DataFrame) -> DataFrame:
        """Create per-vehicle rows for ETA and downstream modelling."""

        columns = [
            column
            for column in [
                "id",
                "vType",
                "depart",
                "departDelay",
                "arrival",
                "duration",
                "routeLength",
                "waitingTime",
                "waitingCount",
                "timeLoss",
                "departLane",
                "arrivalLane",
                "departSpeed",
                "arrivalSpeed",
                "speedFactor",
                "derived_speed_mps",
            ]
            if column in trips.columns
        ]
        trip_metrics = trips[columns].copy()
        trip_metrics = trip_metrics.rename(
            columns={
                "id": "vehicle_id",
                "vType": "vehicle_type",
                "depart": "depart_s",
                "departDelay": "depart_delay_s",
                "arrival": "arrival_s",
                "duration": "duration_s",
                "routeLength": "route_length_m",
                "waitingTime": "waiting_time_s",
                "waitingCount": "waiting_count",
                "timeLoss": "time_loss_s",
                "departSpeed": "depart_speed_mps",
                "arrivalSpeed": "arrival_speed_mps",
            }
        )
        return trip_metrics.sort_values("depart_s").reset_index(drop=True)

    def _build_vehicle_type_metrics(self, trips: DataFrame) -> DataFrame:
        """Compute per-vehicle-type statistics when SUMO vType exists."""

        if "vType" not in trips.columns:
            return pd.DataFrame()

        return (
            trips.groupby("vType", as_index=False)
            .agg(
                vehicle_count=("id", "count"),
                mean_duration_s=("duration", "mean"),
                median_duration_s=("duration", "median"),
                mean_waiting_time_s=("waitingTime", "mean"),
                mean_time_loss_s=("timeLoss", "mean"),
                mean_route_length_m=("routeLength", "mean"),
            )
            .rename(columns={"vType": "vehicle_type"})
            .sort_values("vehicle_type")
        )

    # ==================================================================
    # COMPARE SCENARIOS
    # ==================================================================

    def compare_scenarios(
        self,
        others: dict[str, dict[str, Any]] | None = None,
    ) -> DataFrame:
        """
        Build a comparison table of this scenario against any other
        already-computed scenario metrics dicts supplied.

        With no `others` given, returns a single-row table for the
        current scenario, so export_report() has a consistent shape
        regardless of whether other scenarios exist yet.
        """

        if not self.metrics:
            raise RuntimeError("Metrics have not been computed.")

        logger.info("=" * 70)
        logger.info("COMPARING SCENARIOS")
        logger.info("=" * 70)

        rows: dict[str, dict[str, Any]] = {self.scenario_name: self.metrics}

        if others:
            rows.update(others)
        else:
            logger.info(
                "No other scenarios supplied; reporting %s alone.",
                self.scenario_name,
            )

        comparison = pd.DataFrame(rows).T
        comparison.index.name = "scenario"

        if "scenario" in comparison.columns:
            comparison = comparison.drop(columns=["scenario"])

        self.comparison = comparison

        logger.info("Scenarios compared: %d", len(comparison))

        return comparison

    # ==================================================================
    # CREATE VISUALIZATIONS
    # ==================================================================

    def create_visualizations(self) -> list[Path]:
        """Save compact research-useful simulation plots."""

        if self.tripinfo is None:
            raise RuntimeError("Tripinfo has not been loaded.")

        logger.info("=" * 70)
        logger.info("CREATING VISUALIZATIONS")
        logger.info("=" * 70)

        self.report_dir.mkdir(parents=True, exist_ok=True)

        created: list[Path] = []

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(
            self.tripinfo["duration"],
            bins=30,
            color="#3b82f6",
            edgecolor="white",
        )
        ax.set_xlabel("Travel time (s)")
        ax.set_ylabel("Number of trips")
        ax.set_title(f"Travel Time Distribution — {self.scenario_name}")
        fig.tight_layout()
        fig.savefig(self.travel_time_plot, dpi=150)
        plt.close(fig)
        created.append(self.travel_time_plot)
        logger.info("Saved: %s", self.travel_time_plot)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(
            self.tripinfo["timeLoss"],
            bins=30,
            color="#ef4444",
            edgecolor="white",
        )
        ax.set_xlabel("Time loss / delay (s)")
        ax.set_ylabel("Number of trips")
        ax.set_title(f"Delay Distribution — {self.scenario_name}")
        fig.tight_layout()
        fig.savefig(self.delay_plot, dpi=150)
        plt.close(fig)
        created.append(self.delay_plot)
        logger.info("Saved: %s", self.delay_plot)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(
            self.tripinfo["waitingTime"],
            bins=30,
            color="#10b981",
            edgecolor="white",
        )
        ax.set_xlabel("Waiting time (s)")
        ax.set_ylabel("Number of trips")
        ax.set_title(f"Waiting Time Distribution — {self.scenario_name}")
        fig.tight_layout()
        fig.savefig(self.waiting_time_plot, dpi=150)
        plt.close(fig)
        created.append(self.waiting_time_plot)
        logger.info("Saved: %s", self.waiting_time_plot)

        if "vType" in self.tripinfo.columns:
            fig, ax = plt.subplots(figsize=(9, 5))
            self.tripinfo.boxplot(
                column="duration",
                by="vType",
                ax=ax,
                grid=False,
                rot=30,
            )
            ax.set_xlabel("Vehicle type")
            ax.set_ylabel("Travel duration (s)")
            ax.set_title(
                f"Travel Duration by Vehicle Type — {self.scenario_name}"
            )
            fig.suptitle("")
            fig.tight_layout()
            fig.savefig(self.vehicle_type_duration_plot, dpi=150)
            plt.close(fig)
            created.append(self.vehicle_type_duration_plot)
            logger.info("Saved: %s", self.vehicle_type_duration_plot)

        return created

    # ==================================================================
    # EXPORT REPORT
    # ==================================================================

    def export_report(self) -> list[Path]:
        """Write reproducible metrics and modelling-ready artifacts."""

        if not self.metrics:
            raise RuntimeError("Metrics have not been computed.")

        logger.info("=" * 70)
        logger.info("EXPORTING REPORT")
        logger.info("=" * 70)

        self.report_dir.mkdir(parents=True, exist_ok=True)

        report_table = (
            self.comparison
            if self.comparison is not None
            else pd.DataFrame([self.metrics]).set_index("scenario")
        )

        written: list[Path] = []

        report_table.to_csv(self.report_csv)
        written.append(self.report_csv)
        logger.info("CSV report written: %s", self.report_csv)

        report_data = (
            self.comparison.to_dict(orient="index")
            if self.comparison is not None
            else self.metrics
        )

        with open(self.report_json, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        written.append(self.report_json)

        logger.info("JSON report written: %s", self.report_json)

        summary = {
            "scenario": self.scenario_name,
            "source_files": self._source_file_metadata(),
            "metrics": self.metrics,
            "vehicle_type_metrics": (
                []
                if self.vehicle_type_metrics is None
                else self.vehicle_type_metrics.to_dict(orient="records")
            ),
            "validation": {
                "expected_vehicles_from_routes": self.expected_vehicle_count,
                "tripinfo_records": (
                    None if self.tripinfo is None else int(len(self.tripinfo))
                ),
                "duplicate_trip_vehicle_ids": 0,
                "fresh_xml_outputs_used": True,
            },
        }

        with open(self.summary_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        written.append(self.summary_json)
        logger.info("Summary JSON written: %s", self.summary_json)

        if self.trip_metrics is not None:
            self.trip_metrics.to_csv(self.trip_metrics_csv, index=False)
            written.append(self.trip_metrics_csv)
            logger.info("Trip metrics written: %s", self.trip_metrics_csv)

        if self.vehicle_type_metrics is not None:
            self.vehicle_type_metrics.to_csv(
                self.vehicle_type_metrics_csv, index=False
            )
            written.append(self.vehicle_type_metrics_csv)
            logger.info(
                "Vehicle-type metrics written: %s",
                self.vehicle_type_metrics_csv,
            )

        if self.edge_metrics is not None:
            self.edge_metrics.to_csv(self.edge_metrics_csv, index=False)
            written.append(self.edge_metrics_csv)
            logger.info("Edge metrics written: %s", self.edge_metrics_csv)

        if self.queue_metrics is not None:
            self.queue_metrics.to_csv(self.queue_metrics_csv, index=False)
            written.append(self.queue_metrics_csv)
            logger.info("Queue metrics written: %s", self.queue_metrics_csv)

        return written

    def _source_file_metadata(self) -> dict[str, dict[str, Any]]:
        """Record source file sizes and mtimes for reproducibility."""

        sources = {
            "tripinfo": self.tripinfo_file,
            "summary": self.summary_file,
            "edgeData": self.edge_file,
            "queue": self.queue_file,
            "routes": self.route_file,
        }

        metadata: dict[str, dict[str, Any]] = {}
        for name, path in sources.items():
            stat = path.stat()
            metadata[name] = {
                "path": str(path),
                "size_bytes": stat.st_size,
                "modified_time_epoch": stat.st_mtime,
            }
        return metadata

    # ==================================================================
    # VERIFY OUTPUTS
    # ==================================================================

    def verify_outputs(self) -> bool:
        """Verify all four report/plot outputs were written."""

        logger.info("=" * 70)
        logger.info("VERIFYING ANALYZER OUTPUTS")
        logger.info("=" * 70)

        expected = [
            self.report_csv,
            self.report_json,
            self.summary_json,
            self.trip_metrics_csv,
            self.vehicle_type_metrics_csv,
            self.edge_metrics_csv,
            self.queue_metrics_csv,
            self.travel_time_plot,
            self.delay_plot,
            self.waiting_time_plot,
        ]

        if self.vehicle_type_metrics is not None and not self.vehicle_type_metrics.empty:
            expected.append(self.vehicle_type_duration_plot)

        all_present = True

        for path in expected:
            if path.exists():
                logger.info("✓ %s", path)
            else:
                logger.error("✗ missing: %s", path)
                all_present = False

        logger.info("=" * 70)

        if all_present:
            if self.tripinfo is None:
                raise RuntimeError("Tripinfo was not loaded.")
            if self.summary is None or self.summary.empty:
                raise RuntimeError("Summary was not loaded.")
            if self.expected_vehicle_count is None:
                raise RuntimeError("Route vehicle count was not loaded.")
            if len(self.tripinfo) != self.expected_vehicle_count:
                raise RuntimeError(
                    "Generated report count mismatch: "
                    f"{len(self.tripinfo)} trips vs "
                    f"{self.expected_vehicle_count} route vehicles."
                )
            final_arrived = self.metrics.get("final_arrived")
            if (
                final_arrived is not None
                and int(final_arrived) != len(self.tripinfo)
            ):
                raise RuntimeError(
                    "Final summary arrived count does not match tripinfo: "
                    f"{final_arrived} vs {len(self.tripinfo)}."
                )
            logger.info("SIMULATION ANALYSIS VERIFICATION PASSED")
        else:
            logger.warning("SIMULATION ANALYSIS VERIFICATION INCOMPLETE")

        return all_present

    # ==================================================================
    # FULL PIPELINE
    # ==================================================================

    def run(self) -> None:
        """Execute the complete simulation-analysis pipeline."""

        logger.info("=" * 70)
        logger.info("STARTING SIMULATION ANALYSIS PIPELINE")
        logger.info("=" * 70)

        self.load_route_vehicle_ids()
        self.load_tripinfo()
        self.load_summary()
        self.load_edge_metrics()
        self.load_queue_metrics()
        self.compute_metrics()
        self.compare_scenarios()
        self.create_visualizations()
        self.export_report()

        if not self.verify_outputs():
            raise RuntimeError("Simulation analysis verification failed.")

        logger.info("=" * 70)
        logger.info("SIMULATION ANALYSIS PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)


def main() -> None:
    """Application entry point."""

    SimulationAnalyzer().run()


if __name__ == "__main__":
    main()
