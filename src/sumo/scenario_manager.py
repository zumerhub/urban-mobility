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

from config import SUMO_NETWORK_FILE, TRAVEL_DEMAND_CSV

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
        self.report_dir = report_dir or TRAVEL_DEMAND_CSV.parent
        self.scenario_name = scenario_name

        self.report_csv = self.report_dir / "simulation_report.csv"
        self.report_json = self.report_dir / "simulation_report.json"
        self.travel_time_plot = (
            self.report_dir / "travel_time_distribution.png"
        )
        self.delay_plot = self.report_dir / "delay_distribution.png"

        self.tripinfo: DataFrame | None = None
        self.summary: DataFrame | None = None
        self.metrics: dict[str, Any] = {}
        self.comparison: DataFrame | None = None

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
    # COMPUTE METRICS
    # ==================================================================

    def compute_metrics(self) -> dict[str, Any]:
        """Compute headline performance metrics for this scenario."""

        if self.tripinfo is None:
            raise RuntimeError("Tripinfo has not been loaded.")

        logger.info("=" * 70)
        logger.info("COMPUTING METRICS")
        logger.info("=" * 70)

        trips = self.tripinfo

        metrics: dict[str, Any] = {
            "scenario": self.scenario_name,
            "completed_trips": int(len(trips)),
            "avg_duration_s": float(trips["duration"].mean()),
            "median_duration_s": float(trips["duration"].median()),
            "avg_time_loss_s": float(trips["timeLoss"].mean()),
            "avg_waiting_time_s": float(trips["waitingTime"].mean()),
            "avg_route_length_m": float(trips["routeLength"].mean()),
            "avg_depart_delay_s": float(trips["departDelay"].mean()),
            "max_duration_s": float(trips["duration"].max()),
            "max_time_loss_s": float(trips["timeLoss"].max()),
        }

        if self.summary is not None and not self.summary.empty:
            if "running" in self.summary.columns:
                metrics["peak_concurrent_vehicles"] = int(
                    self.summary["running"].max()
                )
            if "arrived" in self.summary.columns:
                metrics["total_arrived"] = int(
                    self.summary["arrived"].iloc[-1]
                )
            if "collisions" in self.summary.columns:
                metrics["total_collisions"] = int(
                    self.summary["collisions"].iloc[-1]
                )
            if "teleports" in self.summary.columns:
                metrics["total_teleports"] = int(
                    self.summary["teleports"].iloc[-1]
                )

        self.metrics = metrics

        logger.info("Metrics computed:")
        for key, value in metrics.items():
            logger.info("  %s: %s", key, value)

        return metrics

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
        """Save travel-time and delay distribution histograms."""

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

        return created

    # ==================================================================
    # EXPORT REPORT
    # ==================================================================

    def export_report(self) -> tuple[Path, Path]:
        """Write the metrics table to CSV and JSON."""

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

        report_table.to_csv(self.report_csv)
        logger.info("CSV report written: %s", self.report_csv)

        report_data = (
            self.comparison.to_dict(orient="index")
            if self.comparison is not None
            else self.metrics
        )

        with open(self.report_json, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info("JSON report written: %s", self.report_json)

        return self.report_csv, self.report_json

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
            self.travel_time_plot,
            self.delay_plot,
        ]

        all_present = True

        for path in expected:
            if path.exists():
                logger.info("✓ %s", path)
            else:
                logger.error("✗ missing: %s", path)
                all_present = False

        logger.info("=" * 70)

        if all_present:
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

        self.load_tripinfo()
        self.load_summary()
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