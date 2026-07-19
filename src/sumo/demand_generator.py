"""
DemandGenerator class
clean logging
configuration-driven parameters
type hints
comprehensive docstrings
reproducible results (fixed random seed)
export to travel_demand.csv






Vehicle type

Instead of

all passenger

generate a mix.

Example:

Vehicle	Percentage
Passenger	60%
Delivery Van	20%
Truck	10%
Bus	10%

Since your work focuses on urban logistics, delivery vans and trucks are particularly important.

Output

The module should produce a table like:

vehicle_id	origin	destination	depart	type
veh_00001	154	920	12	truck
veh_00002	901	331	20	passenger
veh_00003	444	882	32	delivery

Save it as:

outputs/reports/travel_demand.csv


Purpose: Create realistic traffic demand.

DemandGenerator
│
├── __init__()
├── verify_inputs()  
├── load_node_statistics()
├── load_traffic_features()
├── compute_node_importance()
├── generate_departure_times()
├── generate_vehicle_types()
├── generate_origin_destination_pairs()
├── build_travel_demand()
├── export_travel_demand()
├── verify_outputs()
└── run()

Input

node_statistics.csv

traffic_features.csv

Output

travel_demand.csv

"""

from __future__ import annotations


import pandas as pd
import numpy as np

from src.types import DataFrame, pd

from config import (
    NODE_STATISTICS_CSV,
    TRAFFIC_FEATURES_CSV,
    TRAVEL_DEMAND_CSV,
    NUMBER_OF_VEHICLES,
    RANDOM_SEED,

    MORNING_PEAK_START,
    MORNING_PEAK_END,
    EVENING_PEAK_START,
    EVENING_PEAK_END,

    
    # DELIVERY_RATIO,
    # TRUCK_RATIO,
    # PASSENGER_RATIO,
    # BUS_RATIO,
    CAR_RATIO,         # Private passenger cars

    DANFO_RATIO,          # Commercial minibuses

    KOROPE_RATIO, #= 0.10         # Mini commercial buses

    OKADA_RATIO, #= 0.10          # Motorcycle taxis

    MOLUE_RATIO ,

    KEKE_RATIO, #= 0.07           # Tricycles

    DELIVERY_VAN_RATIO,  #= 0.06       # Delivery vans

    TRUCK_RATIO, #= 0.04          # Heavy goods vehicles

    BRT_RATIO, #= 0.03            # Bus Rapid Transit

    POLICE_RATIO, #= 0.01         # Police patrol vehicles

    AMBULANCE_RATIO, #= 0.005     # Emergency medical service

    FIRE_TRUCK_RATIO, # = 0.005    # Fire service
    
    )

from src.utils.logger import get_logger


logger = get_logger(__name__)


class DemandGenerator:
    """
    Purpose: Build a traffic demand for Node_statistics with traffic_features

    Pipeline:
    1. verify_inputs
    2. load_node_statistics
    3. load_traffic_features
    4. compute_node_importance
    5. generate_departure_times
    6. generate_vehicle_types
    7. generate_origin_destination_pairs
    8. build_travel_demand
    9. export_travel_demand
    10. verify_outputs 
    """

    def __init__(self) -> None:

        self.traffic_features_file = TRAFFIC_FEATURES_CSV
        self.node_statistics_file = NODE_STATISTICS_CSV
        self.travel_demand_file = TRAVEL_DEMAND_CSV

        self.number_of_vehicles = NUMBER_OF_VEHICLES
        self.random_seed = RANDOM_SEED

        # self.passenger_ratio = PASSENGER_RATIO
        # self.delivery_ratio = DELIVERY_RATIO
        # self.truck_ratio = TRUCK_RATIO
        # self.bus_ratio = BUS_RATIO

        self.morning_peak_start = MORNING_PEAK_START
        self.morning_peak_end = MORNING_PEAK_END

        self.evening_peak_start = EVENING_PEAK_START
        self.evening_peak_end = EVENING_PEAK_END

        self.car_ratio = CAR_RATIO
        self.danfo_ratio = DANFO_RATIO
        self.korope_ratio = KOROPE_RATIO
        self.brt_ratio = BRT_RATIO
        self.molue_ratio = MOLUE_RATIO
        self.keke_ratio = KEKE_RATIO
        self.okada_ratio = OKADA_RATIO
        self.delivery_van_ratio = DELIVERY_VAN_RATIO
        self.truck_ratio = TRUCK_RATIO
        self.police_ratio = POLICE_RATIO
        self.ambulance_ratio = AMBULANCE_RATIO
        self.fire_truck_ratio = FIRE_TRUCK_RATIO

        logger.info(
            "Initialized DemandGenerator."
        )

    def verify_input_files(self) -> bool:
        """
        Verify that all required input files exist.
        """

        valid = True

        if not self.traffic_features_file.exists():
            logger.error(
                f"Traffic features file not found: {self.traffic_features_file}"
            )
            valid = False

        if not self.node_statistics_file.exists():
            logger.error(
                f"Node statistics file not found: {self.node_statistics_file}"
            )
            valid = False

        return valid

# ========================= load nodes statistics  ===============
    def load_node_statistics(self) -> DataFrame:
        """Load node statistics file into pandas DataFrame."""
        
        logger.info("=" * 70)
        logger.info("LOADING NODE STATISTICS")
        logger.info("=" * 70)

        self.node_statistics = pd.read_csv(self.node_statistics_file)
        logger.info(
            f"Loaded {len(self.node_statistics):,} node records."
        )
        return self.node_statistics

# ========================= load traffic files  ===============
    def load_traffic_features(self) -> DataFrame:
        """Load traffic features file into panda DataFrame."""

        logger.info("=" * 70)
        logger.info("LOADING TRAFFIC FILE")
        logger.info("=" * 70)

        self.travel_feature = pd.read_csv(self.traffic_features_file)
        logger.info(
            f"Loaded {len(self.travel_feature):,} traffic records"
        )
        return self.travel_feature
    
# ========================= compute_node_importance ==========================
    def compute_node_importance(self) -> None:
        """
        Compute an importance score for each road network node.

        The importance score is calculated as a weighted combination of:
            - Degree Centrality
            - Closeness Centrality
            - Betweenness Centrality

        The resulting scores are normalized so that they sum to 1.0,
        allowing them to be used as sampling probabilities when
        generating travel demand.
        """
        logger.info("=" * 70)
        logger.info("COMPUTING NODE IMPORTANCE")
        logger.info("=" * 70)

        self.node_statistics["importance"] = (
            0.20 * self.node_statistics["degree_centrality"]
            + 0.30 * self.node_statistics["closeness_centrality"]
            + 0.50 * self.node_statistics["betweenness_centrality"]
        )

        total_importance = self.node_statistics["importance"].sum()

        if total_importance <= 0:
            raise ValueError(
                "Total node importance is zero. "
                "Unable to normalize importance scores."
            )

        self.node_statistics["importance"] /= total_importance

        logger.info("Node importance successfully computed.")
        logger.info(
            "Importance range: %.6f - %.6f",
            self.node_statistics["importance"].min(),
            self.node_statistics["importance"].max(),
        )
        logger.info(
            "Total importance: %.6f",
            self.node_statistics["importance"].sum(),
        )

# ========================= generate vehicle departure time ==========================
    def generate_departure_times(self) -> np.ndarray:
        """Generate vehicle departure_times """
        logger.info("=" * 70)
        logger.info("GENERATING DEPARTURE TIMES")
        logger.info("=" * 70)

        # logger.info(self.number_of_vehicles)
        # distribution 60% Morning Peak, 40% Evening Peak
        morning_vehicles = int(self.number_of_vehicles * 0.60)

        evening_vehicles = (self.number_of_vehicles - morning_vehicles)

        # random times 
        morning_departures = np.random.randint(
            self.morning_peak_start,
            self.morning_peak_end,
            morning_vehicles,
        )        
        evening_departures = np.random.randint(
            self.evening_peak_start,
            self.evening_peak_end,
            evening_vehicles
        )

        # merge the inputs (morning_departures & evening_departures)
        self.departure_times = np.concatenate(
            (morning_departures, evening_departures)
        )

        # sort the times 
        self.departure_times.sort()

        logger.info(f"Generated {len(self.departure_times):,} departure times.")
        logger.info(f"Earliest departure : {self.departure_times.min()} seconds")
        logger.info(f"Latest departure   : {self.departure_times.max()} seconds")
        
        return self.departure_times

# ========================= generate vehicle type ==========================
    def generate_vehicle_types(self) -> np.ndarray:
        """Generating the vehicle types """
        logger.info("=" * 70)
        logger.info("GENERATING VEHICLE TYPES")
        logger.info("=" * 70)



    #    convert to integers
       
        # passenger_count = int(self.number_of_vehicles * self.passenger_ratio)
        # delivery_count = int(self.number_of_vehicles * self.delivery_ratio)
        # truck_count = int(self.number_of_vehicles * self.truck_ratio)
        # bus_count = int(self.number_of_vehicles 
        #                 - passenger_count
        #                 - delivery_count
        #                 - truck_count
        #                 )
        # logger.info(f"Passenger : {passenger_count:,}")
        # logger.info(f"Delivery  : {delivery_count:,}")
        # logger.info(f"Truck     : {truck_count:,}")
        # logger.info(f"Bus       : {bus_count:,}")
        # logger.info(f"Total vehicles : {self.number_of_vehicles:,}")


        # self.vehicle_types = np.array(
        #       ["passenger"] * passenger_count
        #     + ["delivery"] * delivery_count
        #     + ["truck"] * truck_count
        #     + ["bus"] * bus_count
        # )

        car_count = int(self.number_of_vehicles * self.car_ratio)

        danfo_count = int(self.number_of_vehicles * self.danfo_ratio)

        korope_count = int(self.number_of_vehicles * self.korope_ratio)

        brt_count = int(self.number_of_vehicles * self.brt_ratio)

        molue_count = int(self.number_of_vehicles * self.molue_ratio)

        keke_count = int(self.number_of_vehicles * self.keke_ratio)

        okada_count = int(self.number_of_vehicles * self.okada_ratio)

        delivery_van_count = int(
            self.number_of_vehicles * self.delivery_van_ratio
        )

        truck_count = int(
            self.number_of_vehicles * self.truck_ratio
        )

        police_count = int(
            self.number_of_vehicles * self.police_ratio
        )

        ambulance_count = int(
            self.number_of_vehicles * self.ambulance_ratio
        )

        fire_truck_count = (
            self.number_of_vehicles
            - car_count
            - danfo_count
            - korope_count
            - brt_count
            - molue_count
            - keke_count
            - okada_count
            - delivery_van_count
            - truck_count
            - police_count
            - ambulance_count
        )

        logger.info(f"Car            : {car_count:,}")
        logger.info(f"Danfo          : {danfo_count:,}")
        logger.info(f"Korope         : {korope_count:,}")
        logger.info(f"BRT            : {brt_count:,}")
        logger.info(f"Molue          : {molue_count:,}")
        logger.info(f"Keke           : {keke_count:,}")
        logger.info(f"Okada          : {okada_count:,}")
        logger.info(f"Delivery Van   : {delivery_van_count:,}")
        logger.info(f"Truck          : {truck_count:,}")
        logger.info(f"Police         : {police_count:,}")
        logger.info(f"Ambulance      : {ambulance_count:,}")
        logger.info(f"Fire Truck     : {fire_truck_count:,}")

        logger.info("-" * 70)
        logger.info(f"Total Vehicles : {self.number_of_vehicles:,}")

        vehicle_types = (
            ["car"] * car_count
            + ["danfo"] * danfo_count
            + ["korope"] * korope_count
            + ["brt"] * brt_count
            + ["molue"] * molue_count
            + ["keke"] * keke_count
            + ["okada"] * okada_count
            + ["deliveryVan"] * delivery_van_count
            + ["truck"] * truck_count
            + ["police"] * police_count
            + ["ambulance"] * ambulance_count
            + ["fireTruck"] * fire_truck_count
        )

        # Randomize vehicle order
        np.random.shuffle(vehicle_types)

        # Store as a NumPy array
        self.vehicle_types = np.array(vehicle_types)

        logger.info(
            f"Generated {len(self.vehicle_types):,} vehicle types."
        )

        logger.info(
            f"Unique vehicle types: {np.unique(self.vehicle_types)}"
        )

        return self.vehicle_types

# ======================= generate_origin_destination_pairs ==========================
    def generate_origin_destination_pairs(self) -> None:
        """
        Generate origin and destination node pairs for all vehicles.

        Nodes with higher importance scores are more likely to be selected.
        The generated origin and destination arrays are stored as class
        attributes for subsequent travel demand generation.
        """

        logger.info("=" * 70)
        logger.info("GENERATING ORIGIN-DESTINATION PAIRS")
        logger.info("=" * 70)

        # ------------------------------------------------------------------
        # Extract node IDs and sampling probabilities
        # ------------------------------------------------------------------
        node_ids = self.node_statistics["osmid"].to_numpy()

        probabilities = self.node_statistics["importance"].to_numpy()

        logger.info(f"Available nodes : {len(node_ids):,}")
        logger.info(f"Probability sum : {probabilities.sum():.6f}")

        # ------------------------------------------------------------------
        # Generate origins
        # ------------------------------------------------------------------
        self.origins = np.random.choice(
            node_ids,
            size=self.number_of_vehicles,
            replace=True,
            p=probabilities,
        )

        # ------------------------------------------------------------------
        # Generate destinations
        # ------------------------------------------------------------------
        self.destinations = np.random.choice(
            node_ids,
            size=self.number_of_vehicles,
            replace=True,
            p=probabilities,
        )

        # ------------------------------------------------------------------
        # Ensure origin != destination
        # ------------------------------------------------------------------
        duplicate_count = 0

        for i in range(self.number_of_vehicles):

            while self.origins[i] == self.destinations[i]:

                self.destinations[i] = np.random.choice(
                    node_ids,
                    p=probabilities,
                )

                duplicate_count += 1

        # ------------------------------------------------------------------
        # Logging
        # ------------------------------------------------------------------
        logger.info(
            f"Generated {self.number_of_vehicles:,} origin-destination pairs."
        )

        logger.info(
            f"Origin = Destination corrections: {duplicate_count:,}"
        )

        logger.info("First 5 Origin-Destination pairs:")

        for i in range(min(5, self.number_of_vehicles)):

            logger.info(
                f"{i + 1}. "
                f"Origin: {self.origins[i]} -> Destination: {self.destinations[i]}"
            )
         
# =============== build_travel demand ======================
    def build_travel_demand(self) -> None:
        """Combine generated attributes into a travel demand DataFrame."""
        logger.info("=" * 70)
        logger.info("GENERATE TRAVEL DEMAND")
        logger.info("=" * 70)

        # Verify all arrays have the same length
        n = len(self.departure_times)
        if not(len(self.vehicle_types) == len(self.origins) == len(self.destinations) == n):
            raise ValueError(
                "Travel demand arrays have different lengths."
            )
                   
        # create vehicle IDs
        vehicle_ids = np.arange(1, n + 1)

        # Build DataFrame
        self.travel_demand = pd.DataFrame(
            {
                "vehicle_id": vehicle_ids,
                "vehicle_type": self.vehicle_types,
                "departure_time": self.departure_times,
                "origin_node": self.origins,
                "destination_node": self.destinations,
                "priority": np.ones(n, dtype=int),
                "trip_status": ["planned"] * n,
            }
        )
        
              
        logger.info("Travel demand successfully built.")
        logger.info(f"Total trips: {len(self.travel_demand):,}")
        logger.info(f"Vehicle types: {self.travel_demand['vehicle_type'].nunique()}")
        
# ====================== export_travel_demand ===================
    def export_travel_demand(self) -> None:
        """Export the travel demand"""
        
        logger.info("=" * 70)
        logger.info("EXPORT TRAVEL DEMAND FILE")
        logger.info("=" * 70)

        if not hasattr(self, "travel_demand"):
            logger.info("No travel demand DataForm found. " 
                        "Run build_travel_demand() first.")
            return
        
        self.travel_demand.to_csv(
                    self.travel_demand_file,
                    index=False,
                )

        logger.info(f"Travel demand exported to : {self.travel_demand_file}")
        logger.info(f"Records expected: {len(self.travel_demand)}")


# ====================== verify_outputs() =============================================
    def verify_outputs(self) -> None:
        """Verify the expected travel demand CSV"""
        logger.info("=" * 70)
        logger.info("VERIFY EXPECTED TRAVEL DEMAND CSV.")
        logger.info("=" * 70)

        if not self.travel_demand_file.exists():
            logger.error(f"Output file not found: {self.travel_demand_file}")
            return
        
        travel_demand = pd.read_csv(self.travel_demand_file)

    # ---------------------------------------------------------
    # Verify number of records
    # ---------------------------------------------------------
        if len(travel_demand) != self.number_of_vehicles:
            logger.error(f"Expected %s records but found %s.", 
                         self.number_of_vehicles,
                         len(travel_demand)
                        )
            return
        logger.info(f"Records count verified: {len(travel_demand):,}")
        
        missing_values = travel_demand.isna().sum().sum()
    
    # ---------------------------------------------------------
    # Verify missing values
    # ---------------------------------------------------------
        if missing_values > 0:
            logger.error(
                f"Missing values detected: {missing_values}"
            )
            return
        logger.info("No missing values detected.")

    # ---------------------------------------------------------
    # Verify vehicle IDs
    # ---------------------------------------------------------
        if not travel_demand["vehicle_id"].is_unique:
            logger.error("Duplicate vehicle IDs detected.")
            return

        logger.info("Vehicle IDs are unique.")

    # ---------------------------------------------------------
    # Success
    # ---------------------------------------------------------
        logger.info("=" * 70)
        logger.info("TRAVEL DEMAND VERIFICATION PASSED")
        logger.info("=" * 70)
        

# ===================== run ===========================================================
    def run(self) -> None:
        if not self.verify_input_files():
            return
        self.load_node_statistics()
        self.load_traffic_features()
        self.compute_node_importance()
        self.generate_departure_times()
        self.generate_vehicle_types()
        self.generate_origin_destination_pairs()
        self.build_travel_demand()
        self.export_travel_demand()
        self.verify_outputs()

        logger.info("")
        logger.info("=" * 70)
        logger.info("DEMAND GENERATION PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)

def main() -> None:
    generator = DemandGenerator()
    generator.run()


if __name__ == "__main__":
        main()


#  python3 -m src.sumo.demand_generator