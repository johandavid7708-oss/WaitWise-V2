from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.location import Location
from services.forecast_service import ForecastService


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


# ============================================================================
# HELPER
# ============================================================================

def get_location_or_404(
    location_id: str,
    db: Session
) -> Location:

    location = (
        db.query(Location)
        .filter(Location.id == location_id)
        .first()
    )

    if not location:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    return location


# ============================================================================
# ANALYZE ALERT CONDITIONS
# ============================================================================

def generate_alerts_from_forecast(
    location: Location,
    forecast: dict
):

    alerts = []

    current = forecast.get("current") or {}
    trend = forecast.get("trend") or {}
    best_time = forecast.get("best_time")

    crowd_level = current.get("crowd_level")
    wait_time = current.get("wait_time_minutes")
    confidence = current.get("confidence", 0)

    trend_direction = trend.get("direction")

    # ------------------------------------------------------------------------
    # HIGH CROWD ALERT
    # ------------------------------------------------------------------------

    if isinstance(crowd_level, (int, float)) and crowd_level >= 80:

        alerts.append({
            "type": "high_crowd",
            "severity": "high",
            "title": "High crowd detected",
            "message": (
                f"{location.name} is currently experiencing "
                f"heavy crowd activity."
            )
        })

    # ------------------------------------------------------------------------
    # LONG WAIT ALERT
    # ------------------------------------------------------------------------

    if isinstance(wait_time, (int, float)) and wait_time >= 30:

        alerts.append({
            "type": "long_wait",
            "severity": "medium",
            "title": "Long waiting time",
            "message": (
                f"Estimated waiting time at {location.name} "
                f"is currently around {round(wait_time)} minutes."
            )
        })

    # ------------------------------------------------------------------------
    # RAPIDLY INCREASING CROWD
    # ------------------------------------------------------------------------

    if trend_direction in {
        "increasing",
        "rapidly_increasing"
    }:

        severity = (
            "high"
            if trend_direction == "rapidly_increasing"
            else "medium"
        )

        alerts.append({
            "type": "crowd_increasing",
            "severity": severity,
            "title": "Crowd is increasing",
            "message": (
                f"Crowd activity at {location.name} "
                f"is expected to increase."
            )
        })

    # ------------------------------------------------------------------------
    # LOW CONFIDENCE ALERT
    # ------------------------------------------------------------------------

    if (
        isinstance(confidence, (int, float))
        and confidence < 40
    ):

        alerts.append({
            "type": "low_confidence",
            "severity": "low",
            "title": "Limited data available",
            "message": (
                f"WaitWise currently has limited reliable data "
                f"for {location.name}."
            )
        })

    # ------------------------------------------------------------------------
    # BEST TIME AVAILABLE
    # ------------------------------------------------------------------------

    if best_time:

        alerts.append({
            "type": "best_time",
            "severity": "info",
            "title": "Better time detected",
            "message": (
                f"A potentially better visiting time has been "
                f"identified for {location.name}."
            ),
            "best_time": best_time
        })

    return alerts


# ============================================================================
# GET ALERTS FOR ONE LOCATION
# ============================================================================

@router.get("/location/{location_id}")
def get_location_alerts(
    location_id: str,
    hours: int = Query(default=6, ge=1, le=48),
    db: Session = Depends(get_db)
):

    location = get_location_or_404(
        location_id,
        db
    )

    forecast_service = ForecastService(db)

    forecast = forecast_service.get_location_forecast(
        location_id=str(location.id),
        hours=hours
    )

    alerts = generate_alerts_from_forecast(
        location,
        forecast
    )

    return {
        "location": {
            "id": str(location.id),
            "name": location.name,
            "category": location.category,
            "city": location.city
        },
        "alert_count": len(alerts),
        "alerts": alerts
    }


# ============================================================================
# GET ALERTS FOR MULTIPLE LOCATIONS
# ============================================================================

@router.get("/")
def get_all_alerts(
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):

    query = db.query(Location)

    if city:
        query = query.filter(
            Location.city == city
        )

    locations = query.limit(limit).all()

    forecast_service = ForecastService(db)

    results = []

    for location in locations:

        try:

            forecast = (
                forecast_service.get_location_forecast(
                    location_id=str(location.id),
                    hours=6
                )
            )

            alerts = generate_alerts_from_forecast(
                location,
                forecast
            )

            if alerts:

                results.append({
                    "location": {
                        "id": str(location.id),
                        "name": location.name,
                        "category": location.category,
                        "city": location.city
                    },
                    "alerts": alerts
                })

        except Exception:

            # A failure for one location should not break
            # alerts for every other location.
            continue

    return {
        "location_count": len(results),
        "locations": results
    }


# ============================================================================
# GET HIGH PRIORITY ALERTS
# ============================================================================

@router.get("/priority/high")
def get_high_priority_alerts(
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):

    query = db.query(Location)

    if city:
        query = query.filter(
            Location.city == city
        )

    locations = query.limit(limit).all()

    forecast_service = ForecastService(db)

    results = []

    for location in locations:

        try:

            forecast = (
                forecast_service.get_location_forecast(
                    location_id=str(location.id),
                    hours=6
                )
            )

            alerts = generate_alerts_from_forecast(
                location,
                forecast
            )

            high_priority = [
                alert
                for alert in alerts
                if alert["severity"] == "high"
            ]

            if high_priority:

                results.append({
                    "location": {
                        "id": str(location.id),
                        "name": location.name,
                        "city": location.city
                    },
                    "alerts": high_priority
                })

        except Exception:
            continue

    return {
        "count": len(results),
        "locations": results
    }
