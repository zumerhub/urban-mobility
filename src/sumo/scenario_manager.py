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

Output

simulation_report.csv

simulation_report.json

travel_time_distribution.png

delay_distribution.png
"""

from __future__ import annotations

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ScenarioManager:

    def __init__(self) -> None:
        pass

    def create_scenarios(self) -> None:
        pass

    def run(self) -> None:
        self.create_scenarios()


if __name__ == "__main__":
    ScenarioManager().run()