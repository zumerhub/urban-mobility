"""
Train the leakage-safe ETA model.
"""

from __future__ import annotations

from src.ml.eta_model import ETAModel


class ModelTrainer:
    """Thin command wrapper around the ETA model pipeline."""

    def __init__(self) -> None:
        self.model = ETAModel()

    def train(self) -> None:
        """Run model training, evaluation, and artifact export."""

        self.model.run()


def main() -> None:
    """Application entry point."""

    ModelTrainer().train()


if __name__ == "__main__":
    main()
