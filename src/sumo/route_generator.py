# """
# Generate vehicle routes for SUMO.
# """
"""
RouteGenerator

├── verify_inputs()  
├── load_travel_demand()     # travel_demand.csv
├── map_nodes_to_edges()
├── build_trip_file()
├── generate_routes()
├── verify_routes()
├── create_sumo_config()

"""



from config import(
    TRAVEL_DEMAND_CSV,
    SUMO_NETWORK_FILE
)





# import subprocess
# from pathlib import Path
# from src.utils.logger import get_logger

# logger = get_logger(__name__)

# class NetworkBuilder:
#     """
#     Builds a SUMO road network and generates synthetic traffic demand.
#     """
    
#     BOUNDING_BOX = "3.30, 6.55, 3.40, 6.65" 
    
#     def __init__(self, pbf_path: str = "data/raw/nigeria-260713.osm.pbf") -> None:
#         self.pbf_path = Path(pbf_path)
#         self.sumo_dir = Path("data/sumo")
#         self.sumo_dir.mkdir(parents=True, exist_ok=True)
        
#         # Network files
#         self.net_file = self.sumo_dir / "ikeja.net.xml"
        
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