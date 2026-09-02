from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from services.crowd_service import CrowdService
from models.location import Location


class ForecastService:
    """
    Combines current crowd intelligence with the prediction engine
    to generate future crowd forecasts.
    """

    def __init__(self, db: Session):
        self.db = db
        self.crowd_service = CrowdService(db)

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
    # PREDICT CROWD
    # =========================================================================

    def predict_crowd_level(
        self,
        location_id: str,
        forecast_time: datetime
    ) -> dict:
        """
        Generate a prediction for a future time.

        Uses historical verified reports when available.
        Falls back gracefully when there is not enough data.
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

        reports = self.crowd_service.get_verified_reports(
            location_id=location_id,
            limit=500
        )

        current_data = self.crowd_service.get_current_crowd(
            location_id=location_id,
            hours=6
        )

        # ---------------------------------------------------------------------
        # NO VERIFIED DATA
        # ---------------------------------------------------------------------

        if not reports:

            return {
                "available": False,
                "reason": "Not enough verified data",
                "crowd_level": None,
                "wait_time_minutes": None,
                "confidence": 0,
                "forecast_time": forecast_time.isoformat()
            }

        # ---------------------------------------------------------------------
        # HISTORICAL PATTERN MATCHING
        #
        # Find reports created at approximately the same hour of day.
        # This gives us a basic real-data forecasting foundation.
        # The ML Predictor will later improve this further.
        # ---------------------------------------------------------------------

        target_hour = forecast_time.hour

        matching_reports = [
            report
            for report in reports
            if report.created_at
            and abs(report.created_at.hour - target_hour) <= 1
        ]

        # If too few matching reports exist, use all verified history.
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
                "reason": "Historical reports contain no crowd data",
                "crowd_level": None,
                "wait_time_minutes": None,
                "confidence": 0,
                "forecast_time": forecast_time.isoformat()
            }

        historical_crowd = (
            sum(crowd_values)
            / len(crowd_values)
        )

        historical_wait = (
            sum(wait_values)
            / len(wait_values)
            if wait_values
            else 0
        )

        # ---------------------------------------------------------------------
        # CURRENT DATA INFLUENCE
        # ---------------------------------------------------------------------

        if (
            current_data.get("available")
            and current_data.get("crowd_level") is not None
        ):

            current_crowd = current_data["crowd_level"]

            # Near-future predictions should be influenced more strongly
            # by current real-world observations.
            hours_ahead = max(
                0,
                (
                    forecast_time
                    - datetime.utcnow()
                ).total_seconds() / 3600
            )

            current_weight = max(
                0.2,
                0.7 - (hours_ahead * 0.08)
            )

            historical_weight = (
                1 - current_weight
            )

            predicted_crowd = (
                current_crowd * current_weight
                + historical_crowd * historical_weight
            )

            current_wait = (
                current_data.get("wait_time_minutes")
                or historical_wait
            )

            predicted_wait = (
                current_wait * current_weight
                + historical_wait * historical_weight
            )

        else:

            predicted_crowd = historical_crowd
            predicted_wait = historical_wait

        # ---------------------------------------------------------------------
        # CONFIDENCE
        # ---------------------------------------------------------------------

        sample_score = min(
            len(matching_reports) / 20,
            1
        ) * 50

        current_confidence = (
            current_data.get("confidence", 0)
            if current_data.get("available")
            else 0
        )

        confidence = min(
            100,
            round(
                sample_score
                + (current_confidence * 0.5)
            )
        )

        return {
            "available": True,
            "location_id": str(location.id),
            "location_name": location.name,
            "crowd_level": round(
                max(0, min(100, predicted_crowd)),
                2
            ),
            "wait_time_minutes": round(
                max(0, predicted_wait),
                2
            ),
            "confidence": confidence,
            "forecast_time": forecast_time.isoformat(),
            "historical_sample_size": len(
                matching_reports
            )
        }

    # =========================================================================
    # LOCATION FORECAST
    # =========================================================================

    def get_location_forecast(
        self,
        location_id: str,
        hours: int = 6
    ) -> dict:
        """
        Generate a complete forecast timeline for a location.
        """

        location = self.get_location(location_id)

        if not location:

            return {
                "available": False,
                "reason": "Location not found",
                "current": {},
                "trend": {},
                "forecasts": [],
                "best_time": None
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
        # BEST TIME
        # ---------------------------------------------------------------------

        best_time = None

        if forecasts:

            best_forecast = min(
                forecasts,
                key=lambda item: item["crowd_level"]
            )

            best_time = {
                "time": best_forecast["forecast_time"],
                "crowd_level": best_forecast["crowd_level"],
                "wait_time_minutes": (
                    best_forecast["wait_time_minutes"]
                ),
                "confidence": best_forecast["confidence"]
            }

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
            "forecasts": forecasts,
            "best_time": best_time
        }
