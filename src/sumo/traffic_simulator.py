# """
# Run SUMO traffic simulation.
# Purpose: Execute the SUMO simulation.

# TrafficSimulator
# │
# ├── __init__()
# ├── verify_network()
# ├── verify_routes()
# ├── build_simulation_command()
# ├── run_simulation()
# ├── collect_outputs()
# ├── verify_outputs()
# └── run()

# Input

# simulation.sumocfg

# routes.rou.xml

# Output

# tripinfo.xml

# summary.xml

# edgeData.xml

# queue.xml
# """

# from __future__ import annotations

# from src.utils.logger import get_logger
# logger = get_logger(__name__)


# class TrafficSimulator:

#     def __init__(self) -> None:
#         pass

#     def simulate(self) -> None:
#         pass

#     def run(self) -> None:
#         self.simulate()


# if __name__ == "__main__":
#     TrafficSimulator().run()


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
-----
simulation.sumocfg
routes.rou.xml

Output
------
tripinfo.xml
summary.xml
edgeData.xml
queue.xml

Notes
-----
data/sumo/simulation.sumocfg, as it currently exists, only declares
net-file and a begin/end window of 0-3600 seconds. It has no
route-files and no output declarations. Since this project's routed
demand departs between 25,207-68,395 seconds, running the cfg as-is
(end=3600) would mean almost no vehicle ever departs.

Rather than rewriting the .sumocfg on disk, TrafficSimulator loads it
with -c for whatever it does define, and passes route-files,
begin/end, and all four output paths as explicit command-line
options. Per SUMO's own docs, a command-line option always overrides
the same option set in the loaded .sumocfg, so this corrects the
mismatch non-destructively.
"""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from config import (
    SUMO_CONFIG_FILE,
    SUMO_NETWORK_FILE,
    SUMO_ROUTE_FILE,
)

from src.utils.logger import get_logger

logger = get_logger(__name__)


class TrafficSimulator:
    """
    Execute a SUMO simulation for a routed demand scenario.

    Pipeline
    --------
    1. verify_network()
    2. verify_routes()
    3. build_simulation_command()
    4. run_simulation()
    5. collect_outputs()
    6. verify_outputs()
    7. run()
    """

    def __init__(
        self,
        net_file: Path = SUMO_NETWORK_FILE,
        route_file: Path = SUMO_ROUTE_FILE,
        sumocfg_file: Path = SUMO_CONFIG_FILE,
        output_dir: Path | None = None,
        begin: float = 0,
        end: float = 86400,
        use_gui: bool = False,
    ) -> None:
        """
        Initialize the TrafficSimulator.

        Parameters
        ----------
        net_file:
            SUMO .net.xml network file.

        route_file:
            SUMO .rou.xml route file (e.g. produced by RouteGenerator
            or TripGenerator).

        sumocfg_file:
            Existing .sumocfg loaded with -c. Its net-file is used;
            route-files, begin/end, and outputs are supplied on the
            command line and take precedence over anything the cfg
            defines for those same options.

        output_dir:
            Directory simulation outputs are written to. Defaults to
            the network file's directory.

        begin, end:
            Simulation time window in seconds. Must cover the full
            departure range in route_file, or any vehicle departing
            after `end` simply never enters the simulation.

        use_gui:
            Run sumo-gui instead of sumo.
        """

        self.net_file = net_file
        self.route_file = route_file
        self.sumocfg_file = sumocfg_file
        self.output_dir = output_dir or self.net_file.parent
        self.begin = begin
        self.end = end
        self.use_gui = use_gui

        self.tripinfo_file = self.output_dir / "tripinfo.xml"
        self.summary_file = self.output_dir / "summary.xml"
        self.edgedata_file = self.output_dir / "edgeData.xml"
        self.queue_file = self.output_dir / "queue.xml"

        self.command: list[str] | None = None
        self.result: subprocess.CompletedProcess[str] | None = None

        logger.info("Initialized TrafficSimulator...")

    # ==================================================================
    # VERIFY NETWORK
    # ==================================================================

    def verify_network(self) -> bool:
        """Verify the SUMO network file exists."""

        logger.info("=" * 70)
        logger.info("VERIFYING NETWORK")
        logger.info("=" * 70)

        if not self.net_file.exists():
            logger.error("SUMO network not found: %s", self.net_file)
            return False

        logger.info("✓ SUMO network: %s", self.net_file)
        return True

    # ==================================================================
    # VERIFY ROUTES
    # ==================================================================

    def verify_routes(self) -> bool:
        """Verify the SUMO route file exists."""

        logger.info("=" * 70)
        logger.info("VERIFYING ROUTES")
        logger.info("=" * 70)

        if not self.route_file.exists():
            logger.error("SUMO route file not found: %s", self.route_file)
            return False

        logger.info("✓ SUMO routes: %s", self.route_file)
        return True

    # ==================================================================
    # BUILD SIMULATION COMMAND
    # ==================================================================

    def build_simulation_command(self) -> list[str]:
        """
        Assemble the sumo/sumo-gui command line.

        route-files, begin/end, and all output paths are always
        passed explicitly on the command line so they override
        whatever (if anything) the loaded .sumocfg defines for those
        same options.
        """

        binary = "sumo-gui" if self.use_gui else "sumo"

        command = [binary]

        if self.sumocfg_file.exists():
            command += ["-c", str(self.sumocfg_file)]
        else:
            logger.warning(
                "sumocfg not found (%s); running from explicit "
                "--net-file instead.",
                self.sumocfg_file,
            )
            command += ["--net-file", str(self.net_file)]

        self.output_dir.mkdir(parents=True, exist_ok=True)

        command += [
            "--route-files", str(self.route_file),
            "--begin", str(self.begin),
            "--end", str(self.end),
            "--tripinfo-output", str(self.tripinfo_file),
            "--summary-output", str(self.summary_file),
            "--edgedata-output", str(self.edgedata_file),
            "--queue-output", str(self.queue_file),
        ]

        self.command = command

        logger.info("Simulation command built.")
        logger.info("Command: %s", " ".join(command))

        return command

    # ==================================================================
    # RUN SIMULATION
    # ==================================================================

    def run_simulation(self) -> subprocess.CompletedProcess[str]:
        """Execute the sumo/sumo-gui command."""

        if self.command is None:
            raise RuntimeError(
                "Simulation command has not been built. "
                "Run build_simulation_command() first."
            )

        logger.info("=" * 70)
        logger.info("RUNNING SUMO SIMULATION")
        logger.info("=" * 70)

        try:
            result = subprocess.run(
                self.command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            binary = self.command[0]
            logger.error(
                "%s was not found. Ensure SUMO is installed and "
                "%s is available on PATH.",
                binary,
                binary,
            )
            raise RuntimeError(f"{binary} executable not found.") from exc
        except subprocess.CalledProcessError as exc:
            logger.error("SUMO simulation failed.")
            if exc.stdout:
                logger.error("sumo stdout:\n%s", exc.stdout)
            if exc.stderr:
                logger.error("sumo stderr:\n%s", exc.stderr)
            raise RuntimeError("SUMO simulation failed.") from exc

        if result.stdout:
            logger.info("sumo output:\n%s", result.stdout.strip())
        if result.stderr:
            logger.warning("sumo messages:\n%s", result.stderr.strip())

        self.result = result

        logger.info("SUMO simulation completed.")

        return result

    # ==================================================================
    # COLLECT OUTPUTS
    # ==================================================================

    def collect_outputs(self) -> dict[str, Path]:
        """Confirm which declared output files were actually written."""

        logger.info("=" * 70)
        logger.info("COLLECTING OUTPUTS")
        logger.info("=" * 70)

        expected = {
            "tripinfo": self.tripinfo_file,
            "summary": self.summary_file,
            "edgedata": self.edgedata_file,
            "queue": self.queue_file,
        }

        collected: dict[str, Path] = {}

        for name, path in expected.items():
            if path.exists():
                logger.info("✓ %s: %s", name, path)
                collected[name] = path
            else:
                logger.warning("✗ %s not written: %s", name, path)

        return collected

    # ==================================================================
    # VERIFY OUTPUTS
    # ==================================================================

    def verify_outputs(self) -> bool:
        """
        Verify tripinfo.xml is well-formed and contains at least one
        completed trip.

        tripinfo.xml is treated as the required minimum for downstream
        analysis (per-vehicle travel time/delay); summary/edgeData/
        queue are best-effort and only logged via collect_outputs().
        """

        logger.info("=" * 70)
        logger.info("VERIFYING SIMULATION OUTPUTS")
        logger.info("=" * 70)

        if not self.tripinfo_file.exists():
            logger.error(
                "tripinfo.xml was not created: %s", self.tripinfo_file
            )
            return False

        try:
            tree = ET.parse(self.tripinfo_file)
        except ET.ParseError as exc:
            logger.error("Invalid XML in tripinfo.xml: %s", exc)
            return False

        trip_infos = tree.getroot().findall(".//tripinfo")

        if not trip_infos:
            logger.error("No <tripinfo> elements found.")
            return False

        logger.info("Completed trips: %d", len(trip_infos))
        logger.info("=" * 70)
        logger.info("SIMULATION OUTPUT VERIFICATION PASSED")
        logger.info("=" * 70)

        return True

    # ==================================================================
    # FULL PIPELINE
    # ==================================================================

    def run(self) -> None:
        """Execute the complete traffic simulation pipeline."""

        logger.info("=" * 70)
        logger.info("STARTING TRAFFIC SIMULATION PIPELINE")
        logger.info("=" * 70)

        if not self.verify_network():
            raise FileNotFoundError("SUMO network verification failed.")

        if not self.verify_routes():
            raise FileNotFoundError("SUMO route verification failed.")

        self.build_simulation_command()
        self.run_simulation()
        self.collect_outputs()

        if not self.verify_outputs():
            raise RuntimeError("Simulation output verification failed.")

        logger.info("=" * 70)
        logger.info("TRAFFIC SIMULATION PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)


def main() -> None:
    """Application entry point."""

    simulator = TrafficSimulator()
    simulator.run()


if __name__ == "__main__":
    main()