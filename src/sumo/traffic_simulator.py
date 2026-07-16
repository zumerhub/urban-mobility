"""
Run SUMO traffic simulation.
Purpose: Execute the SUMO simulation.

TrafficSimulator
│
├── __init__()
├── verify_network()
├── verify_routes()
├── build_simulation_command()
├── run_simulation()
├── collect_outputs()
├── verify_outputs()
└── run()

Input

simulation.sumocfg

routes.rou.xml

Output

tripinfo.xml

summary.xml

edgeData.xml

queue.xml
"""

from __future__ import annotations

from src.utils.logger import get_logger
logger = get_logger(__name__)


class TrafficSimulator:

    def __init__(self) -> None:
        pass

    def simulate(self) -> None:
        pass

    def run(self) -> None:
        self.simulate()


if __name__ == "__main__":
    TrafficSimulator().run()