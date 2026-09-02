from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.location import Location
from services.crowd_service import CrowdService


router = APIRouter(
    prefix="/locations",
    tags=["Locations"]
)


# ============================================================================
# GET ALL LOCATIONS
# ============================================================================

@router.get("/")
def get_locations(
    category: Optional[str] = Query(
        default=None
    ),
    city: Optional[str] = Query(
        default=None
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200
    ),
    db: Session = Depends(get_db)
):

    query = db.query(Location)

    if category:

        query = query.filter(
            Location.category == category
        )

    if city:

        query = query.filter(
            Location.city == city
        )

    locations = (
        query
        .limit(limit)
        .all()
    )

    return {

        "count": len(locations),

        "locations": [

            {
                "id": str(location.id),

                "name": location.name,

                "category": location.category,

                "address": location.address,

                "city": location.city,

                "latitude": location.latitude,

                "longitude": location.longitude,

                "created_at":

                (
                    location.created_at.isoformat()

                    if location.created_at

                    else None
                )

            }

            for location in locations

        ]

    }


# ============================================================================
# SEARCH LOCATIONS
# ============================================================================

@router.get("/search")
def search_locations(
    q: str = Query(
        ...,
        min_length=1
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db)
):

    search_term = f"%{q}%"

    locations = (

        db.query(Location)

        .filter(

            Location.name.ilike(
                search_term
            )

        )

        .limit(limit)

        .all()

    )

    return {

        "query": q,

        "count": len(locations),

        "locations": [

            {
                "id": str(location.id),

                "name": location.name,

                "category": location.category,

                "address": location.address,

                "city": location.city,

                "latitude": location.latitude,

                "longitude": location.longitude

            }

            for location in locations

        ]

    }


# ============================================================================
# GET LOCATION BY ID
# ============================================================================

@router.get("/{location_id}")
def get_location(
    location_id: str,
    db: Session = Depends(get_db)
):

    location = (

        db.query(Location)

        .filter(
            Location.id == location_id
        )

        .first()

    )

    if not location:

        raise HTTPException(

            status_code=404,

            detail="Location not found"

        )

    return {

        "id": str(location.id),

        "name": location.name,

        "category": location.category,

        "address": location.address,

        "city": location.city,

        "latitude": location.latitude,

        "longitude": location.longitude,

        "created_at":

        (
            location.created_at.isoformat()

            if location.created_at

            else None
        )

    }


# ============================================================================
# GET LIVE CROWD INTELLIGENCE
# ============================================================================

@router.get("/{location_id}/crowd")
def get_location_crowd(
    location_id: str,
    db: Session = Depends(get_db)
):

    location = (

        db.query(Location)

        .filter(
            Location.id == location_id
        )

        .first()

    )

    if not location:

        raise HTTPException(

            status_code=404,

            detail="Location not found"

        )

    crowd_service = CrowdService(
        db
    )

    crowd_data = (

        crowd_service
        .get_current_crowd(
            location_id
        )

    )

    return {

        "location": {

            "id": str(location.id),

            "name": location.name,

            "category": location.category

        },

        "crowd_intelligence":

        crowd_data

    }


# ============================================================================
# GET LOCATIONS WITH LIVE CROWD DATA
# ============================================================================

@router.get("/intelligence/live")
def get_live_location_intelligence(
    limit: int = Query(
        default=50,
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db)
):

    locations = (

        db.query(Location)

        .limit(limit)

        .all()

    )

    crowd_service = CrowdService(
        db
    )

    results = []

    for location in locations:

        try:

            crowd_data = (

                crowd_service
                .get_current_crowd(
                    str(location.id)
                )

            )

        except Exception:

            crowd_data = {

                "crowd_level": None,

                "wait_time_minutes": None,

                "confidence": 0,

                "status": "unavailable"

            }

        results.append({

            "id": str(location.id),

            "name": location.name,

            "category": location.category,

            "city": location.city,

            "latitude": location.latitude,

            "longitude": location.longitude,

            "crowd":

           
