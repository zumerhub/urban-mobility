"""
Purpose: Convert demand into SUMO routes.

TripGenerator
│
├── __init__()
├── load_network()
├── load_travel_demand()
├── create_routes()
├── write_routes_xml()
├── write_vehicle_types()
├── verify_outputs()
└── run()

Input

travel_demand.csv

ikeja.net.xml

Output

routes.rou.xml
"""


from src.utils.logger import get_logger
logger = get_logger(__name__)