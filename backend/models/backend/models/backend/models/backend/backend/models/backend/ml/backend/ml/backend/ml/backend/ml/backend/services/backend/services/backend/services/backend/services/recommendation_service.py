from typing import Optional

from sqlalchemy.orm import Session

from models.location import Location
from services.forecast_service import ForecastService


class RecommendationService:
    """
    Converts crowd forecasts into practical recommendations.
    """

    def __init__(self, db: Session):
        self.db = db
        self.forecast_service = ForecastService(db)

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
    # CROWD STATUS
    # =========================================================================

    @staticmethod
    def get_crowd_status(crowd_level: float) -> str:

        if crowd_level < 30:
            return "low"

        if crowd_level < 60:
            return "moderate"

        if crowd_level < 80:
            return "high"

        return "very_high"

    # =========================================================================
    # MAIN RECOMMENDATION
    # =========================================================================

    def get_recommendation(
        self,
        location_id: str,
        hours: int = 6
    ) -> dict:

        location = self.get_location(location_id)

        if not location:

            return {
                "available": False,
                "reason": "Location not found"
            }

        forecast = self.forecast_service.get_location_forecast(
            location_id=location_id,
            hours=hours
        )

        current = forecast.get("current") or {}
        trend = forecast.get("trend") or {}
        best_time = forecast.get("best_time")
        forecasts = forecast.get("forecasts") or []

        # ---------------------------------------------------------------------
        # NO DATA
        # ---------------------------------------------------------------------

        if not current.get("available"):

            return {
                "available": False,
                "location": {
                    "id": str(location.id),
                    "name": location.name,
                    "category": location.category,
                    "city": location.city
                },
                "recommendation": "insufficient_data",
                "title": "Not enough reliable data",
                "message": (
                    "WaitWise does not yet have enough verified "
                    "crowd information to make a reliable recommendation."
                ),
                "confidence": 0,
                "best_time": None
            }

        crowd_level = current.get("crowd_level", 0)
        wait_time = current.get("wait_time_minutes", 0)
        confidence = current.get("confidence", 0)

        trend_direction = trend.get(
            "direction",
            "stable"
        )

        crowd_status = self.get_crowd_status(
            crowd_level
        )

        # ---------------------------------------------------------------------
        # DECISION ENGINE
        # ---------------------------------------------------------------------

        recommendation = "go_now"
        title = "Good time to visit"
        message = (
            f"{location.name} currently has a manageable crowd level."
        )
        priority = "low"

        # VERY HIGH CROWD
        if crowd_level >= 80:

            recommendation = "avoid_for_now"
            title = "Avoid for now"
            message = (
                f"{location.name} is currently very crowded. "
                "Waiting for a better time is recommended."
            )
            priority = "high"

        # HIGH CROWD
        elif crowd_level >= 60:

            recommendation = "consider_waiting"
            title = "Consider waiting"
            message = (
                f"{location.name} is currently fairly crowded."
            )
            priority = "medium"

        # CROWD INCREASING
        if trend_direction == "rapidly_increasing":

            recommendation = "go_soon_or_wait"
            title = "Crowd is rising quickly"
            message = (
                f"Crowd levels at {location.name} are rising rapidly. "
                "Visit soon if you need to go now, or wait for a later "
                "low-crowd period."
            )
            priority = "high"

        elif trend_direction == "increasing":

            if recommendation == "go_now":

                recommendation = "go_soon"
                title = "Go soon"
                message = (
                    f"Crowd levels at {location.name} are increasing."
                )
                priority = "medium"

        # CROWD DECREASING
        elif trend_direction == "rapidly_decreasing":

            recommendation = "wait_for_improvement"
            title = "Crowd is dropping"
            message = (
                f"Crowd levels at {location.name} are decreasing rapidly. "
                "Waiting could give you a much better experience."
            )
            priority = "medium"

        elif trend_direction == "decreasing":

            if crowd_level >= 60:

                recommendation = "wait_a_little"
                title = "Conditions are improving"
                message = (
                    f"Crowd levels at {location.name} are gradually "
                    "decreasing."
                )
                priority = "low"

        # ---------------------------------------------------------------------
        # BEST TIME INSIGHT
        # ---------------------------------------------------------------------

        best_time_message = None
        improvement = None

        if best_time and best_time.get("crowd_level") is not None:

            best_crowd = best_time["crowd_level"]

            improvement = round(
                crowd_level - best_crowd,
                2
            )

            if improvement >= 10:

                best_time_message = (
                    f"Waiting until the predicted best time could reduce "
                    f"crowd levels by approximately {round(improvement)}%."
                )

        # ---------------------------------------------------------------------
        # SCORE
        #
        # Higher score = better time to visit.
        # ---------------------------------------------------------------------

        recommendation_score = max(
            0,
            min(
                100,
                round(
                    100
                    - (crowd_level * 0.7)
                    - (wait_time * 0.5)
                )
            )
        )

        # ---------------------------------------------------------------------
        # RESPONSE
        # ---------------------------------------------------------------------

        return {
            "available": True,

            "location": {
                "id": str(location.id),
                "name": location.name,
                "category": location.category,
                "city": location.city
            },

            "recommendation": recommendation,

            "title": title,

            "message": message,

            "priority": priority,

            "recommendation_score": recommendation_score,

            "current_conditions": {
                "crowd_level": round(crowd_level, 2),
                "crowd_status": crowd_status,
                "wait_time_minutes": round(wait_time, 2),
                "confidence": confidence,
                "trend": trend_direction
            },

            "best_time": best_time,

            "best_time_insight": best_time_message,

            "forecast_count": len(forecasts)
        }

    # =========================================================================
    # MULTIPLE LOCATION RECOMMENDATIONS
    # =========================================================================

    def compare_locations(
        self,
        location_ids: list[str],
        hours: int = 6
    ) -> dict:

        recommendations = []

        for location_id in location_ids:

            recommendation = self.get_recommendation(
                location_id=location_id,
                hours=hours
            )

            if recommendation.get("available"):

                recommendations.append(
                    recommendation
                )

        recommendations.sort(
            key=lambda item: item[
                "recommendation_score"
            ],
            reverse=True
        )

        best_option = (
            recommendations[0]
            if recommendations
            else None
        )

        return {
            "available": bool(recommendations),
            "count": len(recommendations),
            "best_option": best_option,
            "recommendations": recommendations
        }
