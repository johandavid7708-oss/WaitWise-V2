  from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.location import Location
from services.forecast_service import ForecastService


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"]
)


# ============================================================================
# HELPER: GET LOCATION OR RETURN 404
# ============================================================================

def get_location_or_404(
    location_id: str,
    db: Session
):

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
# GET COMPLETE LOCATION FORECAST
# ============================================================================

@router.get("/{location_id}")
def get_location_forecast(
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

    return {
        "location": {
            "id": str(location.id),
            "name": location.name,
            "category": location.category,
            "city": location.city
        },
        "forecast": forecast
    }


# ============================================================================
# GET CURRENT PREDICTION
# ============================================================================

@router.get("/{location_id}/current")
def get_current_prediction(
    location_id: str,
    db: Session = Depends(get_db)
):

    location = get_location_or_404(
        location_id,
        db
    )

    forecast_service = ForecastService(db)

    forecast = forecast_service.get_location_forecast(
        location_id=str(location.id),
        hours=1
    )

    current = forecast.get("current", {})

    return {
        "location_id": str(location.id),
        "location_name": location.name,
        "prediction_time": current.get("timestamp"),
        "crowd_level": current.get("crowd_level"),
        "wait_time_minutes": current.get(
            "wait_time_minutes"
        ),
        "confidence": current.get("confidence"),
        "status": current.get("status")
    }


# ============================================================================
# GET CROWD FORECAST TIMELINE
# ============================================================================

@router.get("/{location_id}/timeline")
def get_prediction_timeline(
    location_id: str,
    hours: int = Query(default=12, ge=1, le=48),
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

    return {
        "location": {
            "id": str(location.id),
            "name": location.name
        },
        "hours": hours,
        "timeline": forecast.get("forecast", [])
    }


# ============================================================================
# GET BEST TIME TO VISIT
# ============================================================================

@router.get("/{location_id}/best-time")
def get_best_time(
    location_id: str,
    hours: int = Query(default=12, ge=1, le=48),
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

    best_time = forecast.get("best_time")

    if not best_time:

        return {
            "location_id": str(location.id),
            "best_time": None,
            "message": (
                "Not enough prediction data is "
                "available yet."
            )
        }

    return {
        "location_id": str(location.id),
        "location_name": location.name,
        "best_time": best_time
    }


# ============================================================================
# GET CROWD TREND
# ============================================================================

@router.get("/{location_id}/trend")
def get_crowd_trend(
    location_id: str,
    db: Session = Depends(get_db)
):

    location = get_location_or_404(
        location_id,
        db
    )

    forecast_service = ForecastService(db)

    forecast = forecast_service.get_location_forecast(
        location_id=str(location.id),
        hours=6
    )

    return {
        "location_id": str(location.id),
        "location_name": location.name,
        "trend": forecast.get("trend", {})
    }


# ============================================================================
# GET PREDICTION CONFIDENCE
# ============================================================================

@router.get("/{location_id}/confidence")
def get_prediction_confidence(
    location_id: str,
    db: Session = Depends(get_db)
):

    location = get_location_or_404(
        location_id,
        db
    )

    forecast_service = ForecastService(db)

    forecast = forecast_service.get_location_forecast(
        location_id=str(location.id),
        hours=6
    )

    current = forecast.get("current", {})

    return {
        "location_id": str(location.id),
        "location_name": location.name,
        "confidence": current.get("confidence", 0),
        "data_status": current.get(
            "status",
            "unknown"
        )
    }


# ============================================================================
# GET FULL PREDICTION INTELLIGENCE
# ============================================================================

@router.get("/{location_id}/intelligence")
def get_prediction_intelligence(
    location_id: str,
    hours: int = Query(default=12, ge=1, le=48),
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

    return {
        "location": {
            "id": str(location.id),
            "name": location.name,
            "category": location.category,
            "city": location.city
        },
        "current": forecast.get("current"),
        "trend": forecast.get("trend"),
        "forecast": forecast.get("forecast"),
        "best_time": forecast.get("best_time"),
        "anomaly": forecast.get("anomaly"),
        "generated_at": forecast.get("generated_at")
    }
