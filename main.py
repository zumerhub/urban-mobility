"""
===========================================================================
Main entry point

Urban Logistics AI
===========================================================================

Runs the project pipeline.

Current Pipeline

1. Download road network

Future Pipeline

2. Process graph 
3. Analyze graph
4. Visualize graph
5. Traffic estimation
6. ETA prediction
7. Dynamic routing
===========================================================================
"""
from config import GRAPH_FILE
from src.graph.downloader import RoadNetworkDownloader
from src.graph.graph_processor import GraphProcessor
from src.graph.graph_analysis import GraphAnalyzer
from src.graph.traffic_features import TrafficFeatureGenerator

from src.utils.logger import get_logger


logger = get_logger(__name__)

# logger.info("Loading graph...")

# logger.warning("Missing road segment")

# logger.error("Model failed.")


def main():
    logger.info("Starting Urban Mobility Pipeline...")
    try:
        if not GRAPH_FILE.exists():
            logger.info("STEP 1:  Download Road Network...")
            downloader = RoadNetworkDownloader()

            downloader.run()

        else: 
            # print("\nRoad network already exists.")
            # print("skipping downloadd.\n")
            logger.info("\n-------.\n")
            logger.info(
                    "Road network already exists. Skipping download."
                )

        # print("\nSTEP 2: PROCESS ROAD NETWORK\n")
        logger.info("STEP 2: PROCESS ROAD NETWORK")
        processor = GraphProcessor()
        processor.run()

        logger.info("STEP 3: Graph Analysis")
        analyzer = GraphAnalyzer(
            force_recompute=False
        )
        analyzer.run()

        logger.info("STEP 4: Traffic Feature Generation")
        traffic = TrafficFeatureGenerator()
        traffic.run()

        logger.info("Urban Mobility Pipeline completed successfully.")
    
    except Exception:
        logger.exception(
                    "Urban Mobility Pipeline failed."
                )
        raise

if __name__ == "__main__":

    main()


