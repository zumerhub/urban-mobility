"""
ETA prediction model.
Purpose: Predict travel time.

ETAModel
│
├── __init__()
├── load_features()
├── split_dataset()
├── train_model()
├── evaluate_model()
├── predict_eta()
├── save_model()
├── export_predictions()
├── verify_outputs()
└── run()

Input

traffic_features.csv

vehicle_counts.csv

Output

eta_predictions.csv

xgboost_model.pkl
"""

from __future__ import annotations


class ETAModel:

    def __init__(self) -> None:
        pass

    def train(self) -> None:
        pass

    def predict(self) -> None:
        pass