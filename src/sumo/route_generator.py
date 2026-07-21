# """
# Generate vehicle routes for SUMO.
# """
"""
RouteGenerator

├── verify_inputs()  
├── load_travel_demand()     # travel_demand.csv
├── load_network()
├── map_nodes_to_edges()
├── build_trip_file()
├── generate_routes()
├── verify_routes()
├── create_sumo_config()
├── run()

"""


from __future__ import annotations

from pathlib import Path

import sumolib  # type: ignore

from src.types import DataFrame, pd

from src.utils.logger import get_logger
from src.types import DataFrame, pd, EdgeCandidateList
from config import(
    TRAVEL_DEMAND_CSV,
    SUMO_NETWORK_FILE,
    SUMO_TRIP_FILE,
    SUMO_ROUTE_FILE,
    SUMO_CONFIG_FILE,
    SUMO_OUTPUT_FILE,
    EDGE_STATISTICS_CSV,
    NODE_STATISTICS_CSV
)


logger = get_logger(__name__)

class RouteGenerator:
    """
    Builds a SUMO route network and generates synthetic traffic demand.
    """
    
    BOUNDING_BOX = "3.30, 6.55, 3.40, 6.65" 
    
    def __init__(self, 
                 travel_demand_csv: Path = TRAVEL_DEMAND_CSV, 
                 net_file: Path = SUMO_NETWORK_FILE,

                 ) -> None:
        
        self.travel_demand_csv = travel_demand_csv
        
        # Network files
        self.net_file = net_file

        self.edge_statistics_csv = EDGE_STATISTICS_CSV
        self.node_statistics_csv = NODE_STATISTICS_CSV
        
        # Demand files
        self.trip_file = SUMO_TRIP_FILE 
        self.route_file = SUMO_ROUTE_FILE 
        
        # Config and Output
        self.config_file = SUMO_CONFIG_FILE 
        self.output_file = SUMO_OUTPUT_FILE 
        self.EDGE_SEARCH_RADIUS = 100
        
        
        logger.info(f"Initialized RouteGenerator...")


    def verify_input_file(self) -> bool:
        """Verify file files exists."""

        valid = True
        if not self.travel_demand_csv.exists():
            logger.info(f"Source file not found: {self.travel_demand_csv}")
            return False
        
        if not self.net_file.exists():
            logger.info(f"SUMO network file not found: {self.net_file}")
            return False
        return valid

    def load_travel_demand(self) -> DataFrame:
        """Load travel demand CSV into a Pandas DataFrame."""

        logger.info("=" * 70)
        logger.info("LOADING TRAVEL DEMAND...")
        logger.info("=" * 70)
        
        self.travel_demand = pd.read_csv(self.travel_demand_csv)
        
        logger.info(f"Loaded {len(self.travel_demand):,} trips.")
        
        return self.travel_demand
    

    def load_node_statistics(self) -> DataFrame:
        """Load node statistics."""

        logger.info("=" * 70)
        logger.info("LOADING NODE STATISTICS")
        logger.info("=" * 70)

        self.node_statistics = pd.read_csv(
            self.node_statistics_csv
        )

        logger.info(
            f"Loaded {len(self.node_statistics):,} nodes."
        )

        return self.node_statistics
    

    
    def load_network(self) -> None:
        """Verify the SUMO network is available."""

        logger.info("=" * 70)
        logger.info("LOADING SUMO NETWORK ...")
        logger.info("=" * 70)
        
        self.network = sumolib.net.readNet(str(self.net_file))

        logger.info(f"Network loaded successfully.")
        logger.info(f"Network file: {self.net_file}")
        

    
    def map_nodes_to_edges(self) -> DataFrame:
        """
        Map each origin and destination OSM node
        to the closest valid SUMO edge.
        """

        logger.info("=" * 70)
        logger.info("MAPPING NODES TO EDGES")
        logger.info("=" * 70)

        # TODO:
        # Read origin_node and destination_node from self.travel_demand
        node_lookup = (
            self.node_statistics
            .set_index("osmid")[["x", "y"]]
            .to_dict("index")
        )
        # Find the corresponding SUMO edges (add the lists)
        origin_edges = []
        destination_edges = []


        for _, trip in self.travel_demand.iterrows():

            origin_node = trip["origin_node"]
            destination_node = trip["destination_node"]
            
            # Store them in self.origin_edges and self.destination_edges
            origin = node_lookup[origin_node]
            destination = node_lookup[destination_node]

            # contain longitude and latitude.
            origin = node_lookup[origin_node]
            destination = node_lookup[destination_node]

            logger.info(
                f"Origin node {origin_node}: "
                f"x={origin['x']}, y={origin['y']}"
            )
            # Find nearby SUMO edges
            origin_candidates: EdgeCandidateList = (
                self.network.getNeighboringEdges(
                origin["x"],
                origin["y"],
                self.EDGE_SEARCH_RADIUS #100.0,

            ))
            logger.info(len(origin_candidates))

            destination_candidates: EdgeCandidateList = (self.network.getNeighboringEdges(
                destination["x"],
                destination["y"],
                self.EDGE_SEARCH_RADIUS #100.0,
            ))
            

            logger.info(
               f"Mapped {len(origin_edges):,} / {len(self.travel_demand):,} trips."
            )
            # Skip trips if no nearby edge exists
            if not origin_candidates:
                logger.warning(
                    f"No SUMO edge found for origin node {origin_node}"
                )
                continue

            if not destination_candidates:
                logger.warning(
                    f"No SUMO edge found for destination node {destination_node}"
                )
                continue

    
            closest_origin = min(origin_candidates, key=lambda item: item[1])
            origin_edge = closest_origin[0]

            logger.info(closest_origin[1])

            closest_destination = min(destination_candidates, key=lambda item: item[1])
            destination_edge = closest_destination[0]

            # Save edge IDs
            origin_edges.append(origin_edge.getID())
            destination_edges.append(destination_edge.getID())

        # Store results
        # self.origin_edges = origin_edges
        # self.destination_edges = destination_edges

        # Add edge IDs to travel demand
        self.travel_demand["origin_edge"] = origin_edges
        self.travel_demand["destination_edge"] = destination_edges

        logger.info(
            f"Mapped {len(self.travel_demand):,} trips to SUMO edges."
        )

        logger.info("First 5 mapped trips:")

        logger.info(
            self.travel_demand[
                [
                    "origin_node",
                    "origin_edge",
                    "destination_node",
                    "destination_edge",
                ]
            ].head()
        )
    
        return self.travel_demand

    def run(self) -> None:
        if not self.verify_input_file():
            return

        self.load_travel_demand()
        self.load_node_statistics()
        self.load_network()
        self.map_nodes_to_edges()

        logger.info("=" * 70)
        logger.info("ROUTE GENERATOR INITIALIZATION COMPLETE")
        logger.info("=" * 70)

def main() -> None:
    builder = RouteGenerator()
    builder.run()  # Uncomment to execute

if __name__ == "__main__":
    main()  


    # if __name__ == "__main__":
    #     builder = RouteGenerator()
    #     builder.run()  # Uncomment to execute


#  python3 -m src.sumo.route_generator










# # 
#         self.sumo_dir = Path("data/sumo")
#         self.sumo_dir.mkdir(parents=True, exist_ok=True)
        
#         # Network files
#         self.net_file = net_file
        
#         # Demand files
#         self.trip_file = self.sumo_dir / "trips.xml"
#         self.route_file = self.sumo_dir / "routes.rou.xml"
        
#         # Config and Output
#         self.config_file = self.sumo_dir / "simulation.sumocfg"
#         self.output_file = self.sumo_dir / "simulation_output.xml"
        
#         logger.info(f"Initialized NetworkBuilder. Pipeline ready.")

#     def generate_trips(self) -> None:
#         """Generates random trips using randomTrips.py."""
#         logger.info("Generating random trips...")
#         cmd = [
#             "python", "randomTrips.py",
#             "-n", str(self.net_file),
#             "-o", str(self.trip_file),
#             "--begin", "0",
#             "--end", "3600",
#             "--period", "1"
#         ]
#         subprocess.run(cmd, check=True)

#     def generate_routes(self) -> None:
#         """Converts trips to valid routes using duarouter."""
#         logger.info("Converting trips to routes...")
#         cmd = [
#             "duarouter",
#             "-n", str(self.net_file),
#             "-t", str(self.trip_file),
#             "-o", str(self.route_file),
#             "--ignore-errors"
#         ]
#         subprocess.run(cmd, check=True)

#     def create_sumo_config(self) -> None:
#         """Creates the SUMO config with input/output definitions."""
#         config_content = f"""<configuration>
#     <input>
#         <net-file value="ikeja.net.xml"/>
#         <route-files value="routes.rou.xml"/>
#     </input>
#     <output>
#         <tripinfo-output value="simulation_output.xml"/>
#     </output>
#     <time>
#         <begin value="0"/>
#         <end value="3600"/>
#     </time>
# </configuration>
# """
#         with open(self.config_file, "w") as f:
#             f.write(config_content)
#         logger.info(f"SUMO config created at {self.config_file}")

#     def run(self) -> None:
#         # Assuming build_network() is called first
#         self.generate_trips()
#         self.generate_routes()
#         self.create_sumo_config()
#         logger.info("Traffic generation and configuration complete.")

# if __name__ == "__main__":
#     builder = NetworkBuilder()
#     builder.run()  # Uncomment to execute

# python3 randomTrips.py \
#     -n ikeja.net.xml \
#     -o trips.trips.xml \
#     -r routes.rou.xml \
#     --begin 0 \
#     --end 3600 \
#     --period 2 \
#     --seed 42