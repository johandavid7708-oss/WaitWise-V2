from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models.location import Location
from services.crowd_service import CrowdService
from ml.predictor import CrowdPredictor


class ForecastService:
    """
    Hybrid forecasting service.

    Priority:

    1. Machine-learning prediction when enough verified data exists
    2. Historical pattern prediction as fallback
    3. Current crowd conditions influence near-future forecasts
    """

    def __init__(self, db: Session):
        self.db = db

        self.crowd_service = CrowdService(db)
        self.predictor = CrowdPredictor(db)

    # =========================================================================
    # LOCATION
    # =========================================================================

    def get_location(
        self,
        location_id: str
    ) -> Optional[Location]:

        return (
            self.db.query(Location)
            .filter(Location.id == location_id)
            .first()
        )

    # =========================================================================
    # HISTORICAL FALLBACK
    # =========================================================================

    def historical_prediction(
        self,
        location_id: str,
        forecast_time: datetime
    ) -> dict:
        """
        Predict using verified historical reports.

        Used when the ML model does not yet have enough
        training samples.
        """

        reports = self.crowd_service.get_verified_reports(
            location_id=location_id,
            limit=500
        )

        if not reports:

            return {
                "available": False,
                "reason": "No verified historical data",
                "crowd_level": None,
                "wait_time_minutes": None,
                "confidence": 0,
                "prediction_method": "none"
            }

        target_hour = forecast_time.hour

        # Find reports from approximately the same hour.
        matching_reports = [
            report
            for report in reports
            if (
                report.created_at is not None
                and abs(
                    report.created_at.hour - target_hour
                ) <= 1
            )
        ]

        # If the hour-based sample is too small,
        # use all verified history.

        if len(matching_reports) < 3:
            matching_reports = reports

        crowd_values = [
            report.crowd_level
            for report in matching_reports
            if report.crowd_level is not None
        ]

        wait_values = [
            report.estimated_wait_minutes
            for report in matching_reports
            if report.estimated_wait_minutes is not None
        ]

        if not crowd_values:

            return {
                "available": False,
                "reason": "No valid crowd values",
                "crowd_level": None,
                "wait_time_minutes": None,
                "confidence": 0,
                "prediction_method": "none"
            }

        predicted_crowd = (
            sum(crowd_values)
            / len(crowd_values)
        )

        predicted_wait = (
            sum(wait_values)
            / len(wait_values)
            if wait_values
            else 0
        )

        confidence = min(
            75,
            round(
                25
                + min(
                    len(matching_reports) * 2,
                    50
                )
            )
        )

        return {
            "available": True,

            "crowd_level": round(
                max(0, min(100, predicted_crowd)),
                2
            ),

            "wait_time_minutes": round(
                max(0, predicted_wait),
                2
            ),

            "confidence": confidence,

            "samples": len(matching_reports),

            "prediction_method": "historical"
        }

    # =========================================================================
    # CURRENT CONDITIONS ADJUSTMENT
    # =========================================================================

    def apply_current_conditions(
        self,
        prediction: dict,
        location_id: str,
        forecast_time: datetime
    ) -> dict:
        """
        Blend near-future predictions with current
        real-world crowd conditions.

        Current observations matter more for forecasts
        that are closer in time.
        """

        if not prediction.get("available"):
            return prediction

        current = self.crowd_service.get_current_crowd(
            location_id=location_id,
            hours=6
        )

        if (
            not current.get("available")
            or current.get("crowd_level") is None
        ):
            return prediction

        hours_ahead = max(
            0,
            (
                forecast_time
                - datetime.utcnow()
            ).total_seconds() / 3600
        )

        # Current conditions influence the near future
        # strongly and gradually lose influence.

        current_weight = max(
            0.10,
            min(
                0.70,
                0.70 - (hours_ahead * 0.08)
            )
        )

        prediction_weight = (
            1 - current_weight
        )

        predicted_crowd = (
            current["crowd_level"]
            * current_weight
            +
            prediction["crowd_level"]
            * prediction_weight
        )

        current_wait = (
            current.get("wait_time_minutes")
        )

        predicted_wait = (
            prediction.get("wait_time_minutes", 0)
        )

        if current_wait is not None:

            predicted_wait = (
                current_wait
                * current_weight
                +
                predicted_wait
                * prediction_weight
            )

        prediction["crowd_level"] = round(
            max(0, min(100, predicted_crowd)),
            2
        )

        prediction["wait_time_minutes"] = round(
            max(0, predicted_wait),
            2
        )

        prediction["current_conditions_used"] = True

        prediction["current_conditions_weight"] = round(
            current_weight,
            2
        )

        return prediction

    # =========================================================================
    # MAIN PREDICTION
    # =========================================================================

    def predict_crowd_level(
        self,
        location_id: str,
        forecast_time: datetime
    ) -> dict:
        """
        Generate a hybrid prediction.

        First tries ML.

        If ML does not have enough verified data,
        automatically falls back to historical analysis.
        """

        location = self.get_location(location_id)

        if not location:

            return {
                "available": False,
                "reason": "Location not found",
                "crowd_level": None,
                "wait_time_minutes": None,
                "confidence": 0
            }

        # ---------------------------------------------------------------------
        # STEP 1 — TRY MACHINE LEARNING
        # ---------------------------------------------------------------------

        ml_prediction = self.predictor.predict(
            location_id=location_id,
            forecast_time=forecast_time
        )

        if ml_prediction.get("available"):

            prediction = ml_prediction

            prediction["prediction_method"] = "machine_learning"

        else:

            # -----------------------------------------------------------------
            # STEP 2 — HISTORICAL FALLBACK
            # -----------------------------------------------------------------

            prediction = self.historical_prediction(
                location_id=location_id,
                forecast_time=forecast_time
            )

        # ---------------------------------------------------------------------
        # STEP 3 — APPLY CURRENT REAL-WORLD CONDITIONS
        # ---------------------------------------------------------------------

        prediction = self.apply_current_conditions(
            prediction=prediction,
            location_id=location_id,
            forecast_time=forecast_time
        )

        prediction["location_id"] = str(location.id)

        prediction["location_name"] = location.name

        prediction["forecast_time"] = (
            forecast_time.isoformat()
        )

        return prediction

    # =========================================================================
    # LOCATION FORECAST
    # =========================================================================

    def get_location_forecast(
        self,
        location_id: str,
        hours: int = 6
    ) -> dict:
        """
        Generate a complete hourly forecast.
        """

        location = self.get_location(location_id)

        if not location:

            return {
                "available": False,
                "reason": "Location not found",
                "forecasts": []
            }

        current = self.crowd_service.get_current_crowd(
            location_id=location_id,
            hours=6
        )

        trend = self.crowd_service.get_crowd_trend(
            location_id=location_id,
            hours=6
        )

        forecasts = []

        now = datetime.utcnow()

        for hour_offset in range(1, hours + 1):

            forecast_time = (
                now
                + timedelta(hours=hour_offset)
            )

            prediction = self.predict_crowd_level(
                location_id=location_id,
                forecast_time=forecast_time
            )

            if prediction.get("available"):

                forecasts.append(prediction)

        # ---------------------------------------------------------------------
        # FIND BEST TIME
        # ---------------------------------------------------------------------

        best_time = None

        if forecasts:

            best_forecast = min(
                forecasts,
                key=lambda item: item[
                    "crowd_level"
                ]
            )

            best_time = {
                "time": best_forecast[
                    "forecast_time"
                ],

                "crowd_level": best_forecast[
                    "crowd_level"
                ],

                "wait_time_minutes": best_forecast[
                    "wait_time_minutes"
                ],

                "confidence": best_forecast[
                    "confidence"
                ],

                "prediction_method": best_forecast.get(
                    "prediction_method"
                )
            }

        # ---------------------------------------------------------------------
        # DETERMINE PRIMARY PREDICTION METHOD
        # ---------------------------------------------------------------------

        methods = [
            forecast.get("prediction_method")
            for forecast in forecasts
        ]

        if "machine_learning" in methods:

            primary_method = "hybrid_ml"

        elif "historical" in methods:

            primary_method = "historical"

        else:

            primary_method = "insufficient_data"

        return {
            "available": True,

            "location": {
                "id": str(location.id),
                "name": location.name,
                "category": location.category,
                "city": location.city
            },

            "current": current,

            "trend": trend,

            "forecast_hours": hours,

            "prediction_method": primary_method,

            "forecasts": forecasts,

            "best_time": best_time
        }
