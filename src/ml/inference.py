"""
Run ETA inference with the saved preprocessing + XGBoost pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

from config import PROJECT_ROOT, REPORT_DIR
from src.ml.eta_model import ETAModel
from src.types import DataFrame, pd


class ModelInference:
    """Load a saved ETA pipeline and score one feature record."""

    def __init__(
        self,
        model_path: Path | None = None,
        dataset_file: Path | None = None,
    ) -> None:
        self.model_path = model_path or (
            PROJECT_ROOT / "models" / "eta" / "eta_xgboost_pipeline.joblib"
        )
        self.dataset_file = dataset_file or REPORT_DIR / "eta_dataset.csv"
        self.feature_columns = ETAModel().model_features
        self.pipeline: Any | None = None

    def load_model(self) -> Any:
        """Load the fitted sklearn pipeline."""

        if not self.model_path.exists():
            raise FileNotFoundError(f"Saved ETA model not found: {self.model_path}")
        self.pipeline = joblib.load(self.model_path)
        return self.pipeline

    def predict_record(self, record: dict[str, Any] | DataFrame) -> float:
        """Predict trip duration seconds for one valid feature record."""

        if self.pipeline is None:
            self.load_model()

        if isinstance(record, pd.DataFrame):
            frame = record.copy()
        else:
            frame = pd.DataFrame([record])

        missing = [
            column for column in self.feature_columns if column not in frame
        ]
        if missing:
            raise ValueError(f"Inference record missing features: {missing}")

        assert self.pipeline is not None
        prediction = self.pipeline.predict(frame[self.feature_columns])
        return float(prediction[0])

    def demo_from_dataset(self) -> dict[str, Any]:
        """Score the first saved test observation for verification."""

        test_ids = pd.read_csv(REPORT_DIR / "eta_test_ids.csv")
        dataset = pd.read_csv(self.dataset_file)
        vehicle_id = str(test_ids["vehicle_id"].iloc[0])
        dataset["vehicle_id"] = dataset["vehicle_id"].astype(str)
        row = dataset.loc[dataset["vehicle_id"] == vehicle_id]
        if row.empty:
            raise ValueError(f"Vehicle {vehicle_id} not found in ETA dataset.")

        prediction = self.predict_record(row[self.feature_columns].iloc[[0]])
        return {
            "vehicle_id": vehicle_id,
            "predicted_duration_seconds": prediction,
            "actual_duration_seconds": float(
                row["trip_duration_seconds"].iloc[0]
            ),
        }

    def predict(self) -> None:
        """Run a minimal CLI demonstration."""

        result = self.demo_from_dataset()
        print(result)


def main() -> None:
    """Application entry point."""

    ModelInference().predict()


if __name__ == "__main__":
    main()
