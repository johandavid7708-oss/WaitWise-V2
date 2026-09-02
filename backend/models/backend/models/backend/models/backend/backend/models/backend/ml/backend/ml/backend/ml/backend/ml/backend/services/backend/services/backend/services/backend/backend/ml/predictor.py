from datetime import datetime
from typing import Optional

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.orm import Session

from models.crowd_report import CrowdReport


class CrowdPredictor:
    """
    Machine-learning crowd prediction engine.

    The model learns from verified historical crowd reports using:

    - Hour of day
    - Day of week
    - Historical crowd level
    - Historical waiting time
    """

    MIN_TRAINING_SAMPLES = 10

    def __init__(self, db: Session):
        self.db = db

        self.crowd_model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            min_samples_leaf=1
        )

        self.wait_model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            min_samples_leaf=1
        )

        self.is_trained = False
        self.training_samples = 0

    # =========================================================================
    # DATA COLLECTION
    # =========================================================================

    def get_training_reports(
        self,
        location_id: str
    ) -> list:

        return (
            self.db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location_id,
                CrowdReport.is_verified.is_(True)
            )
            .order_by(CrowdReport.created_at.asc())
            .all()
        )

    # =========================================================================
    # FEATURE EXTRACTION
    # =========================================================================

    @staticmethod
    def extract_features(
        report_time: datetime
    ) -> list:

        hour = report_time.hour
        day_of_week = report_time.weekday()

        # Cyclical encoding helps the model understand that
        # hour 23 and hour 0 are close together.

        hour_sin = np.sin(
            2 * np.pi * hour / 24
        )

        hour_cos = np.cos(
            2 * np.pi * hour / 24
        )

        day_sin = np.sin(
            2 * np.pi * day_of_week / 7
        )

        day_cos = np.cos(
            2 * np.pi * day_of_week / 7
        )

        return [
            hour,
            day_of_week,
            hour_sin,
            hour_cos,
            day_sin,
            day_cos
        ]

    # =========================================================================
    # PREPARE TRAINING DATA
    # =========================================================================

    def prepare_training_data(
        self,
        location_id: str
    ):

        reports = self.get_training_reports(
            location_id
        )

        features = []
        crowd_targets = []
        wait_targets = []

        for report in reports:

            if (
                report.created_at is None
                or report.crowd_level is None
            ):
                continue

            features.append(
                self.extract_features(
                    report.created_at
                )
            )

            crowd_targets.append(
                report.crowd_level
            )

            wait_targets.append(
                report.estimated_wait_minutes
                if report.estimated_wait_minutes is not None
                else 0
            )

        return (
            np.array(features),
            np.array(crowd_targets),
            np.array(wait_targets)
        )

    # =========================================================================
    # TRAIN MODEL
    # =========================================================================

    def train(
        self,
        location_id: str
    ) -> dict:

        (
            features,
            crowd_targets,
            wait_targets
        ) = self.prepare_training_data(
            location_id
        )

        sample_count = len(features)

        self.training_samples = sample_count

        if sample_count < self.MIN_TRAINING_SAMPLES:

            self.is_trained = False

            return {
                "trained": False,
                "reason": (
                    "Not enough verified training data"
                ),
                "samples": sample_count,
                "minimum_required": (
                    self.MIN_TRAINING_SAMPLES
                )
            }

        self.crowd_model.fit(
            features,
            crowd_targets
        )

        self.wait_model.fit(
            features,
            wait_targets
        )

        self.is_trained = True

        return {
            "trained": True,
            "samples": sample_count,
            "minimum_required": (
                self.MIN_TRAINING_SAMPLES
            )
        }

    # =========================================================================
    # PREDICT
    # =========================================================================

    def predict(
        self,
        location_id: str,
        forecast_time: Optional[datetime] = None
    ) -> dict:

        if forecast_time is None:
            forecast_time = datetime.utcnow()

        # Train using the latest verified data.
        training_result = self.train(
            location_id
        )

        if not self.is_trained:

            return {
                "available": False,
                "reason": training_result["reason"],
                "crowd_level": None,
                "wait_time_minutes": None,
                "confidence": 0,
                "samples": training_result["samples"],
                "forecast_time": (
                    forecast_time.isoformat()
                )
            }

        features = np.array([
            self.extract_features(
                forecast_time
            )
        ])

        predicted_crowd = float(
            self.crowd_model.predict(
                features
            )[0]
        )

        predicted_wait = float(
            self.wait_model.predict(
                features
            )[0]
        )

        # Keep predictions within realistic ranges.

        predicted_crowd = max(
            0,
            min(100, predicted_crowd)
        )

        predicted_wait = max(
            0,
            predicted_wait
        )

        # Confidence improves as more historical
        # verified reports
