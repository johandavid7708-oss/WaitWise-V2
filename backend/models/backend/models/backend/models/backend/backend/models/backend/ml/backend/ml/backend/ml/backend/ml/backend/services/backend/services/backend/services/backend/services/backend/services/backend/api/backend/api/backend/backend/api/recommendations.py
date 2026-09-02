from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.location import Location
from services.recommendation_service import RecommendationService


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"]
)


# ============================================================================
# HELPER: GET LOCATION OR RETURN 404
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
# GET BEST RECOMMENDATIONS
# ============================================================================

@router.get("/")
def get_recommendations(
    category: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):

    recommendation_service = RecommendationService(db)

    recommendations = (
        recommendation_service.get_recommendations(
            category=category,
            city=city,
            limit=limit
        )
    )

    return {
        "count": len(recommendations),
        "category": category,
        "city": city,
        "recommendations": recommendations
    }


# ============================================================================
# GET BEST PLACES RIGHT NOW
# ============================================================================

@router.get("/best-now")
def get_best_places_now(
    category: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):

    recommendation_service = RecommendationService(db)

    recommendations = (
        recommendation_service.get_best_places_now(
            category=category,
            city=city,
            limit=limit
        )
    )

    return {
        "count": len(recommendations),
        "message": "Best places to visit right now",
        "recommendations": recommendations
    }


# ============================================================================
# GET PLACES TO AVOID
# ============================================================================

@router.get("/avoid")
def get_places_to_avoid(
    category: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):

    recommendation_service = RecommendationService(db)

    locations = (
        recommendation_service.get_places_to_avoid(
            category=category,
            city=city,
            limit=limit
        )
    )

    return {
        "count": len(locations),
        "message": "Locations currently best avoided",
        "locations": locations
    }


# ============================================================================
# GET SMART ALTERNATIVES FOR A LOCATION
# ============================================================================

@router.get("/{location_id}/alternatives")
def get_alternatives(
    location_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db)
):

    location = get_location_or_404(
        location_id,
        db
    )

    recommendation_service = RecommendationService(db)

    alternatives = (
        recommendation_service.get_alternatives(
            location_id=str(location.id),
            limit=limit
        )
    )

    return {
        "location": {
            "id": str(location.id),
            "name": location.name,
            "category": location.category,
            "city": location.city
        },
        "count": len(alternatives),
        "alternatives": alternatives
    }


# ============================================================================
# GET RECOMMENDATION FOR A SPECIFIC LOCATION
# ============================================================================

@router.get("/{location_id}")
def get_location_recommendation(
    location_id: str,
    db: Session = Depends(get_db)
):

    location = get_location_or_404(
        location_id,
        db
    )

    recommendation_service = RecommendationService(db)

    recommendation = (
        recommendation_service.evaluate_location(
            location_id=str(location.id)
        )
    )

    return {
        "location": {
            "id": str(location.id),
            "name": location.name,
            "category": location.category,
            "city": location.city
        },
        "recommendation": recommendation
    }
