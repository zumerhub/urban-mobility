# # =========================================================================
# """
# ===========================================================================
# Module: network_builder.py

# Purpose:
#     Build a SUMO road network from an OpenStreetMap (.osm.pbf) file.

# Author:
#     Samuel Adekunle

# Project:
#     Real-Time Computer Vision and Machine Learning
#     for Sustainable Urban Logistics in Lagos

# ===========================================================================

# Pipeline

# Raw OSM (.osm.pbf)
#         │
#         ▼
# netconvert
#         │
#         ▼
# SUMO Network (.net.xml)

# ===========================================================================

# This module ONLY builds the SUMO network.

# It does NOT:

#     - generate routes
#     - simulate traffic
#     - export traffic statistics
#     - train ETA models

# ===========================================================================

import subprocess
from pathlib import Path
from typing import List, Tuple

from config import (
    RAW_OSM_FILE,
    SUMO_NETWORK_FILE,
    SUMO_OSM_FILE,
    SUMO_CONFIG_FILE,
    BOUNDING_BOX
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NetworkBuilder:
    """
    Purpose: Build the SUMO road network from OpenStreetMap.

    Pipeline:
    1. Verify input file
    2. Clip OSM PBF to bounding box
    3. Convert clipped OSM to SUMO network
    4. Generate SUMO config file
    5. Verify outputs
    """

    def __init__(self, pbf_path: Path = RAW_OSM_FILE, bbox: Tuple[float, float, float, float] = BOUNDING_BOX):
        self.pbf_path = pbf_path
        self.bbox = bbox
        self.clipped_osm = SUMO_OSM_FILE
        self.net_file = SUMO_NETWORK_FILE
        self.config_file = SUMO_CONFIG_FILE

        logger.info(f"Initialized NetworkBuilder with source: {self.pbf_path}")

    def verify_input_file(self) -> bool:
        """Ensure the raw OSM PBF file exists."""
        if not self.pbf_path.exists():
            logger.error(f"Source file not found: {self.pbf_path}")
            return False
        return True

    def clip_osm(self) -> None:
        """Clip OSM data to bounding box using osmconvert."""
        if self.clipped_osm.exists():
            logger.info("Clipped OSM file already exists. Skipping clip step.")
            return

        minLon, minLat, maxLon, maxLat = self.bbox
        logger.info(f"Clipping OSM data to bounding box: {self.bbox}...")
        cmd = [
            "osmconvert",
            str(self.pbf_path),
            f"-b={minLon},{minLat},{maxLon},{maxLat}",
            "-o=" + str(self.clipped_osm)
        ]
        self._run_command(cmd, "OSM clipping")

    def build_network(self, force: bool = False) -> None:
        """Convert clipped OSM file into SUMO network using netconvert."""
        if self.net_file.exists() and not force:
            logger.info("SUMO network already exists. Skipping build.")
            return

        self.clip_osm()
        logger.info("Starting SUMO netconvert process...")
        cmd = [
            "netconvert",
            "--osm-files", str(self.clipped_osm),
            "-o", str(self.net_file),
            "--geometry.remove", "true",
            "--roundabouts.guess", "true",
            "--tls.guess", "true",
            "--junctions.join", "true"
        ]
        self._run_command(cmd, "SUMO network build")

    def create_sumo_config(self) -> None:
        """Create a basic SUMO configuration file."""
        if self.config_file.exists():
            logger.info("SUMO config already exists. Skipping creation.")
            return

        config_content = f"""<configuration>
    <input>
        <net-file value="{self.net_file.name}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
"""
        with open(self.config_file, "w") as f:
            f.write(config_content)
        logger.info(f"SUMO config created at {self.config_file}")

    def verify_outputs(self) -> None:
        """Check that all expected outputs exist."""
        for file in [self.clipped_osm, self.net_file, self.config_file]:
            if file.exists():
                logger.info(f"Verified output: {file}")
            else:
                logger.error(f"Missing expected output: {file}")

    def run(self) -> None:
        """Run the full pipeline."""
        if not self.verify_input_file():
            return
        self.build_network()
        self.create_sumo_config()
        self.verify_outputs()
        logger.info("Pipeline complete.")

    @staticmethod
    def _run_command(cmd: List[str], step: str) -> None:
        """Helper to run subprocess commands with logging."""
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"{step} successful.")
        except subprocess.CalledProcessError as e:
            logger.error(f"{step} failed: {e.stderr}")
            raise

if __name__ == "__main__":
    builder = NetworkBuilder()
    builder.run()



# cd /home/zumerhub/codebase/urban-mobility

# python3 -m src.sumo.network_builder

# # ======================================================================
# rough
# ========================================================================


# import subprocess
# from pathlib import Path

# from config import (
#     RAW_OSM_FILE,
#     SUMO_NETWORK_FILE
# )

# from src.utils.logger import get_logger

# logger = get_logger(__name__)

# class NetworkBuilder:
#     """
#     Builds a SUMO road network by first clipping a large OSM PBF 
#     to a bounding box, then converting to a SUMO network.
#     """
    
#     # Bounding box for Ikeja: minLon, minLat, maxLon, maxLat
#     BOUNDING_BOX = "3.30, 6.55, 3.40, 6.65" 
    
#     def __init__(
#             self, 
#             # pbf_path: str = "data/raw/nigeria-260713.osm.pbf"
#             pbf_path: Path = RAW_OSM_FILE,
#             sumo_dir: Path = SUMO_NETWORK_FILE
#     ) -> None:
#     # ):     
#         self.pbf_path = pbf_path
#         self.sumo_dir = sumo_dir

        
#         # self.pbf_path = Path(pbf_path)
#         # self.sumo_dir = Path("data/sumo")
#         # self.sumo_dir.mkdir(parents=True, exist_ok=True)
        
#         self.clipped_osm = self.sumo_dir / "ikeja.osm"
#         self.net_file = self.sumo_dir / "ikeja.net.xml"
#         self.config_file = self.sumo_dir / "simulation.sumocfg"
        
#         logger.info(f"Initialized NetworkBuilder for: {self.pbf_path}")

#     def clip_osm(self) -> None:
#         """
#         Uses osmconvert to extract the Ikeja region.
#         """
#         logger.info(f"Clipping OSM data to {self.BOUNDING_BOX}...")
#         # osmconvert syntax: -b=minLon,minLat,maxLon,maxLat
#         cmd = [
#             "osmconvert", 
#             str(self.pbf_path), 
#             f"-b={self.BOUNDING_BOX}", 
#             "-o=" + str(self.clipped_osm)
#         ]
#         try:
#             subprocess.run(cmd, check=True, capture_output=True, text=True)
#             logger.info(f"Successfully clipped to {self.clipped_osm}")
#         except subprocess.CalledProcessError as e:
#             logger.error(f"osmconvert failed: {e.stderr}")
#             raise

#     def build_network(self) -> None:
#         """
#         Executes SUMO netconvert on the clipped OSM file.
#         """
#         self.clip_osm()
#         logger.info("Starting SUMO netconvert process...")
        
#         cmd = [
#             "netconvert",
#             "--osm-files", str(self.clipped_osm),
#             "-o", str(self.net_file),
#             "--geometry.remove", "true",
#             "--roundabouts.guess", "true",
#             "--tls.guess", "true",
#             "--junctions.join", "true"
#         ]
        
#         try:
#             subprocess.run(cmd, check=True, capture_output=True, text=True)
#             logger.info(f"Network successfully built at {self.net_file}")
#         except subprocess.CalledProcessError as e:
#             logger.error(f"netconvert failed: {e.stderr}")
#             raise

#     def create_sumo_config(self) -> None:
#         """
#         Creates a basic SUMO configuration file.
#         """
#         config_content = f"""<configuration>
#     <input>
#         <net-file value="ikeja.net.xml"/>
#     </input>
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
#         if not self.pbf_path.exists():
#             logger.error(f"Source file not found: {self.pbf_path}")
#             return
            
#         self.build_network()
#         self.create_sumo_config()
#         logger.info("Pipeline complete.")

# if __name__ == "__main__":
#     builder = NetworkBuilder()
#     builder.run()








