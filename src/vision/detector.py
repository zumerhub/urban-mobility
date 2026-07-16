"""
Vehicle detection using YOLO.
Purpose: Detect vehicles from video.

YOLOTrafficDetector
│
├── __init__()
├── load_model()
├── load_video()
├── process_frame()
├── detect_vehicles()
├── track_vehicles()
├── estimate_density()
├── export_results()
├── verify_outputs()
└── run()

Input

traffic video

Output

vehicle_counts.csv

traffic_density.csv

"""

from __future__ import annotations


class VehicleDetector:

    def __init__(self) -> None:
        pass

    def detect(self) -> None:
        pass