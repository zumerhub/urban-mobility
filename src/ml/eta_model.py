"""
Train and evaluate the first leakage-safe ETA regression model.

The model predicts total trip duration at vehicle departure time using
only pre-departure features from ``outputs/reports/eta_dataset.csv``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

import sklearn
import xgboost
from config import PROJECT_ROOT, REPORT_DIR
from src.types import DataFrame, pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ETAModel:
    """Leakage-safe ETA model training and evaluation pipeline."""

    target_column = "trip_duration_seconds"

    numeric_features = [
        "depart_seconds",
        "depart_hour",
        "depart_minute_of_day",
        "depart_time_sin",
        "depart_time_cos",
        "is_morning_peak",
        "is_evening_peak",
        "priority",
        "route_edge_count",
        "planned_route_length_m",
        "planned_free_flow_time_s",
        "planned_avg_edge_speed_mps",
    ]

    categorical_features = [
        "demand_vehicle_type",
    ]

    excluded_columns = [
        "trip_duration_seconds",
        "outcome_arrival_seconds",
        "outcome_depart_delay_seconds",
        "outcome_actual_route_length_m",
        "outcome_waiting_time_seconds",
        "outcome_waiting_count",
        "outcome_time_loss_seconds",
        "outcome_depart_lane",
        "outcome_arrival_lane",
        "outcome_depart_speed_mps",
        "outcome_arrival_speed_mps",
        "outcome_speed_factor",
        "outcome_derived_speed_mps",
        "vehicle_type",
    ]

    limitations = [
        "Dataset contains only 500 trips.",
        "Trips come from one SUMO simulation experiment.",
        "Evaluation is an internal holdout, not external validation.",
        "Traffic-state features are not yet temporally aligned.",
        "Computer-vision real-time traffic observations are not integrated.",
        "Model is not validated on real-world Lagos travel times.",
    ]

    def __init__(
        self,
        dataset_file: Path | None = None,
        report_dir: Path | None = None,
        model_dir: Path | None = None,
        random_state: int = 42,
    ) -> None:
        self.report_dir = report_dir or REPORT_DIR
        self.dataset_file = dataset_file or self.report_dir / "eta_dataset.csv"
        self.model_dir = model_dir or PROJECT_ROOT / "models" / "eta"
        self.random_state = random_state

        self.model_path = self.model_dir / "eta_xgboost_pipeline.joblib"
        self.metrics_path = self.report_dir / "eta_model_metrics.json"
        self.predictions_path = self.report_dir / "eta_test_predictions.csv"
        self.feature_importance_path = (
            self.report_dir / "eta_feature_importance.csv"
        )
        self.feature_importance_plot_path = (
            self.report_dir / "eta_feature_importance.png"
        )
        self.train_ids_path = self.report_dir / "eta_train_ids.csv"
        self.test_ids_path = self.report_dir / "eta_test_ids.csv"

        self.dataset: DataFrame | None = None
        self.pipeline: Pipeline | None = None
        self.metrics: dict[str, Any] = {}

    @property
    def model_features(self) -> list[str]:
        """Return the exact feature list used in X."""

        return self.numeric_features + self.categorical_features

    def load_features(self) -> DataFrame:
        """Load and validate the ETA modelling dataset."""

        if not self.dataset_file.exists():
            raise FileNotFoundError(f"ETA dataset not found: {self.dataset_file}")

        dataset = pd.read_csv(self.dataset_file)
        required_columns = ["vehicle_id", self.target_column] + self.model_features
        missing = [column for column in required_columns if column not in dataset]
        if missing:
            raise ValueError(f"ETA dataset is missing columns: {missing}")

        if dataset["vehicle_id"].duplicated().any():
            raise ValueError("ETA dataset contains duplicate vehicle IDs.")
        if dataset[self.target_column].isna().any():
            raise ValueError("ETA dataset contains missing target values.")

        for column in self.numeric_features:
            dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
            if dataset[column].isna().any():
                raise ValueError(f"Numeric feature has missing values: {column}")

        for column in self.categorical_features:
            if dataset[column].isna().any():
                raise ValueError(
                    f"Categorical feature has missing values: {column}"
                )

        self._validate_no_leakage(self.model_features)
        self.dataset = dataset
        return dataset

    def split_dataset(
        self,
        dataset: DataFrame,
    ) -> tuple[DataFrame, DataFrame, str]:
        """Create a reproducible 80/20 holdout split."""

        stratify = dataset["demand_vehicle_type"]
        split_strategy = "stratified_by_demand_vehicle_type"

        try:
            train, test = train_test_split(
                dataset,
                test_size=0.20,
                random_state=self.random_state,
                stratify=stratify,
            )
        except ValueError as exc:
            logger.warning(
                "Stratified split unavailable (%s); using fixed random split.",
                exc,
            )
            train, test = train_test_split(
                dataset,
                test_size=0.20,
                random_state=self.random_state,
                shuffle=True,
            )
            split_strategy = "fixed_random_split"

        train = train.sort_values("vehicle_id").reset_index(drop=True)
        test = test.sort_values("vehicle_id").reset_index(drop=True)
        return train, test, split_strategy

    def build_pipeline(self) -> Pipeline:
        """Build the sklearn preprocessing + XGBoost pipeline."""

        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", "passthrough", self.numeric_features),
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    self.categorical_features,
                ),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        )

        model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=120,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=2.0,
            min_child_weight=2.0,
            random_state=self.random_state,
            n_jobs=1,
        )

        return Pipeline(
            steps=[
                ("preprocess", preprocessor),
                ("model", model),
            ]
        )

    def train_model(self, train: DataFrame) -> Pipeline:
        """Fit the ETA model on the training set only."""

        pipeline = self.build_pipeline()
        pipeline.fit(train[self.model_features], train[self.target_column])
        self.pipeline = pipeline
        return pipeline

    def evaluate_model(
        self,
        train: DataFrame,
        test: DataFrame,
        split_strategy: str,
    ) -> dict[str, Any]:
        """Evaluate baselines and XGBoost on the untouched test set."""

        if self.pipeline is None:
            raise RuntimeError("Model has not been trained.")

        y_train = train[self.target_column]
        y_test = test[self.target_column]
        predictions = self.pipeline.predict(test[self.model_features])

        train_median = float(y_train.median())
        train_mean = float(y_train.mean())
        median_predictions = np.full(len(test), train_median)
        mean_predictions = np.full(len(test), train_mean)

        xgb_metrics = self._regression_metrics(y_test, predictions)
        absolute_errors = np.abs(y_test.to_numpy() - predictions)

        metrics: dict[str, Any] = {
            "prediction_definition": (
                "Departure-time ETA: predict total trip duration using "
                "features available at or before vehicle departure."
            ),
            "target_column": self.target_column,
            "model_features": self.model_features,
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "excluded_columns": self.excluded_columns,
            "random_state": self.random_state,
            "split_strategy": split_strategy,
            "train_count": int(len(train)),
            "test_count": int(len(test)),
            "train_vehicle_type_distribution": self._distribution(train),
            "test_vehicle_type_distribution": self._distribution(test),
            "baselines": {
                "training_median_seconds": train_median,
                "training_mean_seconds": train_mean,
                "median_baseline": self._regression_metrics(
                    y_test,
                    median_predictions,
                ),
                "mean_baseline": self._regression_metrics(
                    y_test,
                    mean_predictions,
                ),
            },
            "xgboost": {
                **xgb_metrics,
                "median_absolute_error_seconds": float(
                    np.median(absolute_errors)
                ),
                "max_absolute_error_seconds": float(np.max(absolute_errors)),
                "mean_actual_duration_seconds": float(y_test.mean()),
                "mean_predicted_duration_seconds": float(
                    np.mean(predictions)
                ),
            },
            "package_versions": {
                "scikit_learn": sklearn.__version__,
                "xgboost": xgboost.__version__,
                "joblib": joblib.__version__,
            },
            "research_limitations": self.limitations,
        }

        self.metrics = metrics
        return metrics

    def export_predictions(self, test: DataFrame) -> DataFrame:
        """Write test-set predictions and residuals."""

        if self.pipeline is None:
            raise RuntimeError("Model has not been trained.")

        predicted = self.pipeline.predict(test[self.model_features])
        actual = test[self.target_column].to_numpy()

        predictions = pd.DataFrame(
            {
                "vehicle_id": test["vehicle_id"].astype(str),
                "actual_duration_seconds": actual,
                "predicted_duration_seconds": predicted,
                "absolute_error_seconds": np.abs(actual - predicted),
                "residual_seconds": actual - predicted,
            }
        )
        predictions.to_csv(self.predictions_path, index=False)
        return predictions

    def export_feature_importance(self) -> DataFrame:
        """Write ranked XGBoost feature importance values."""

        if self.pipeline is None:
            raise RuntimeError("Model has not been trained.")

        preprocessor = self.pipeline.named_steps["preprocess"]
        model = self.pipeline.named_steps["model"]
        feature_names = preprocessor.get_feature_names_out()
        importances = model.feature_importances_

        if len(feature_names) != len(importances):
            raise RuntimeError(
                "Feature-name and importance lengths do not match."
            )

        feature_importance = (
            pd.DataFrame(
                {
                    "feature": feature_names,
                    "importance": importances,
                }
            )
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        feature_importance.to_csv(self.feature_importance_path, index=False)
        self._plot_feature_importance(feature_importance)
        return feature_importance

    def save_model(self) -> Path:
        """Save the complete fitted preprocessing + model pipeline."""

        if self.pipeline is None:
            raise RuntimeError("Model has not been trained.")

        self.model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, self.model_path)
        return self.model_path

    def export_reports(
        self,
        train: DataFrame,
        test: DataFrame,
    ) -> None:
        """Write metrics and reproducible split identifiers."""

        self.report_dir.mkdir(parents=True, exist_ok=True)
        train[["vehicle_id", "demand_vehicle_type"]].to_csv(
            self.train_ids_path,
            index=False,
        )
        test[["vehicle_id", "demand_vehicle_type"]].to_csv(
            self.test_ids_path,
            index=False,
        )

        with open(self.metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)

    def verify_reload(self, test: DataFrame) -> dict[str, Any]:
        """Verify the saved model reloads and predicts consistently."""

        if self.pipeline is None:
            raise RuntimeError("Model has not been trained.")

        loaded = joblib.load(self.model_path)
        sample = test[self.model_features].iloc[[0]]
        live_prediction = float(self.pipeline.predict(sample)[0])
        loaded_prediction = float(loaded.predict(sample)[0])
        matches = bool(np.isclose(live_prediction, loaded_prediction))
        result = {
            "vehicle_id": str(test["vehicle_id"].iloc[0]),
            "live_prediction_seconds": live_prediction,
            "loaded_prediction_seconds": loaded_prediction,
            "matches": matches,
        }
        self.metrics["reload_inference_verification"] = result
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)
        return result

    def run(self) -> dict[str, Any]:
        """Execute the full training and evaluation pipeline."""

        logger.info("=" * 70)
        logger.info("STARTING ETA MODEL TRAINING")
        logger.info("=" * 70)

        dataset = self.load_features()
        train, test, split_strategy = self.split_dataset(dataset)
        self.train_model(train)
        self.evaluate_model(train, test, split_strategy)
        self.export_predictions(test)
        self.export_feature_importance()
        self.save_model()
        self.export_reports(train, test)
        self.verify_reload(test)

        logger.info("ETA model training completed successfully.")
        return self.metrics

    def _validate_no_leakage(self, features: list[str]) -> None:
        leakage = sorted(set(features).intersection(self.excluded_columns))
        if leakage:
            raise ValueError(f"Leakage columns included in X: {leakage}")

    @staticmethod
    def _regression_metrics(
        actual: Any,
        predicted: Any,
    ) -> dict[str, float]:
        return {
            "mae_seconds": float(mean_absolute_error(actual, predicted)),
            "rmse_seconds": float(root_mean_squared_error(actual, predicted)),
            "r2": float(r2_score(actual, predicted)),
        }

    @staticmethod
    def _distribution(data: DataFrame) -> dict[str, int]:
        return {
            str(key): int(value)
            for key, value in data["demand_vehicle_type"]
            .value_counts()
            .sort_index()
            .items()
        }

    def _plot_feature_importance(self, feature_importance: DataFrame) -> None:
        top = feature_importance.head(12).iloc[::-1]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(top["feature"], top["importance"], color="#2563eb")
        ax.set_xlabel("XGBoost feature importance")
        ax.set_title("Top ETA Model Features")
        fig.tight_layout()
        fig.savefig(self.feature_importance_plot_path, dpi=150)
        plt.close(fig)


def main() -> None:
    """Application entry point."""

    ETAModel().run()


if __name__ == "__main__":
    main()
