from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models.location import Location
from models.crowd_report import CrowdReport


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


# ============================================================================
# HELPER
# ============================================================================

def calculate_location_statistics(
    location: Location,
    reports: list
):

    total_reports = len(reports)

    if total_reports == 0:

        return {
            "location_id": str(location.id),
            "location_name": location.name,
            "category": location.category,
            "city": location.city,
            "total_reports": 0,
            "verified_reports": 0,
            "average_crowd_level": None,
            "average_wait_minutes": None
        }

    verified_reports = [
        report
        for report in reports
        if report.is_verified
    ]

    average_crowd = round(
        sum(report.crowd_level for report in reports)
        / total_reports,
        2
    )

    average_wait = round(
        sum(report.estimated_wait_minutes for report in reports)
        / total_reports,
        2
    )

    return {
        "location_id": str(location.id),
        "location_name": location.name,
        "category": location.category,
        "city": location.city,
        "total_reports": total_reports,
        "verified_reports": len(verified_reports),
        "average_crowd_level": average_crowd,
        "average_wait_minutes": average_wait
    }


# ============================================================================
# OVERALL PLATFORM ANALYTICS
# ============================================================================

@router.get("/overview")
def get_platform_overview(
    city: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):

    location_query = db.query(Location)

    if city:
        location_query = location_query.filter(
            Location.city == city
        )

    locations = location_query.all()

    location_ids = [
        location.id
        for location in locations
    ]

    if not location_ids:

        return {
            "total_locations": 0,
            "total_reports": 0,
            "verified_reports": 0,
            "average_crowd_level": None,
            "average_wait_minutes": None
        }

    reports = (
        db.query(CrowdReport)
        .filter(
            CrowdReport.location_id.in_(location_ids)
        )
        .all()
    )

    total_reports = len(reports)

    verified_reports = sum(
        1
        for report in reports
        if report.is_verified
    )

    average_crowd = None
    average_wait = None

    if total_reports > 0:

        average_crowd = round(
            sum(
                report.crowd_level
                for report in reports
            ) / total_reports,
            2
        )

        average_wait = round(
            sum(
                report.estimated_wait_minutes
                for report in reports
            ) / total_reports,
            2
        )

    return {
        "city": city,
        "total_locations": len(locations),
        "total_reports": total_reports,
        "verified_reports": verified_reports,
        "unverified_reports": (
            total_reports - verified_reports
        ),
        "average_crowd_level": average_crowd,
        "average_wait_minutes": average_wait
    }


# ============================================================================
# BUSIEST LOCATIONS
# ============================================================================

@router.get("/busiest")
def get_busiest_locations(
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):

    location_query = db.query(Location)

    if city:
        location_query = location_query.filter(
            Location.city == city
        )

    locations = location_query.all()

    results = []

    for location in locations:

        reports = (
            db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location.id,
                CrowdReport.is_verified.is_(True)
            )
            .all()
        )

        if not reports:
            continue

        average_crowd = (
            sum(
                report.crowd_level
                for report in reports
            )
            / len(reports)
        )

        average_wait = (
            sum(
                report.estimated_wait_minutes
                for report in reports
            )
            / len(reports)
        )

        results.append({
            "location_id": str(location.id),
            "location_name": location.name,
            "category": location.category,
            "city": location.city,
            "average_crowd_level": round(
                average_crowd,
                2
            ),
            "average_wait_minutes": round(
                average_wait,
                2
            ),
            "report_count": len(reports)
        })

    results.sort(
        key=lambda item: item["average_crowd_level"],
        reverse=True
    )

    return {
        "count": min(len(results), limit),
        "locations": results[:limit]
    }


# ============================================================================
# LEAST CROWDED LOCATIONS
# ============================================================================

@router.get("/least-crowded")
def get_least_crowded_locations(
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):

    location_query = db.query(Location)

    if city:
        location_query = location_query.filter(
            Location.city == city
        )

    locations = location_query.all()

    results = []

    for location in locations:

        reports = (
            db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location.id,
                CrowdReport.is_verified.is_(True)
            )
            .all()
        )

        if not reports:
            continue

        average_crowd = (
            sum(
                report.crowd_level
                for report in reports
            )
            / len(reports)
        )

        average_wait = (
            sum(
                report.estimated_wait_minutes
                for report in reports
            )
            / len(reports)
        )

        results.append({
            "location_id": str(location.id),
            "location_name": location.name,
            "category": location.category,
            "city": location.city,
            "average_crowd_level": round(
                average_crowd,
                2
            ),
            "average_wait_minutes": round(
                average_wait,
                2
            ),
            "report_count": len(reports)
        })

    results.sort(
        key=lambda item: item["average_crowd_level"]
    )

    return {
        "count": min(len(results), limit),
        "locations": results[:limit]
    }


# ============================================================================
# CITY INTELLIGENCE
# ============================================================================

@router.get("/city/{city_name}")
def get_city_intelligence(
    city_name: str,
    db: Session = Depends(get_db)
):

    locations = (
        db.query(Location)
        .filter(Location.city == city_name)
        .all()
    )

    if not locations:

        return {
            "city": city_name,
            "total_locations": 0,
            "message": "No locations found for this city"
        }

    location_statistics = []

    for location in locations:

        reports = (
            db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location.id
            )
            .all()
        )

        location_statistics.append(
            calculate_location_statistics(
                location,
                reports
            )
        )

    locations_with_data = [
        item
        for item in location_statistics
        if item["average_crowd_level"] is not None
    ]

    city_average_crowd = None

    if locations_with_data:

        city_average_crowd = round(
            sum(
                item["average_crowd_level"]
                for item in locations_with_data
            )
            / len(locations_with_data),
            2
        )

    hotspots = sorted(
        locations_with_data,
        key=lambda item: item["average_crowd_level"],
        reverse=True
    )[:5]

    return {
        "city": city_name,
        "total_locations": len(locations),
        "locations_with_data": len(
            locations_with_data
        ),
        "average_crowd_level": city_average_crowd,
        "hotspots": hotspots,
        "location_statistics": location_statistics
    }


# ============================================================================
# CATEGORY ANALYTICS
# ============================================================================

@router.get("/category/{category_name}")
def get_category_analytics(
    category_name: str,
    city: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):

    query = (
        db.query(Location)
        .filter(Location.category == category_name)
    )

    if city:
        query = query.filter(
            Location.city == city
        )

    locations = query.all()

    results = []

    for location in locations:

        reports = (
            db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location.id
            )
            .all()
        )

        results.append(
            calculate_location_statistics(
                location,
                reports
            )
        )

    locations_with_data = [
        item
        for item in results
        if item["average_crowd_level"] is not None
    ]

    category_average = None

    if locations_with_data:

        category_average = round(
            sum(
                item["average_crowd_level"]
                for item in locations_with_data
            )
            / len(locations_with_data),
            2
        )

    return {
        "category": category_name,
        "city": city,
        "total_locations": len(locations),
        "average_crowd_level": category_average,
        "locations": results
    }
