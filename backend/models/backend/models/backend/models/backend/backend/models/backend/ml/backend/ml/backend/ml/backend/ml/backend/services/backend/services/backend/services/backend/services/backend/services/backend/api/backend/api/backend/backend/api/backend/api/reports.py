from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.location import Location
from models.crowd_report import CrowdReport


router = APIRouter(
    prefix="/reports",
    tags=["Crowd Reports"]
)


# ============================================================================
# REQUEST MODELS
# ============================================================================

class CrowdReportCreate(BaseModel):
    location_id: str

    crowd_level: int = Field(
        ...,
        ge=0,
        le=100,
        description="Crowd level from 0 to 100"
    )

    estimated_wait_minutes: int = Field(
        ...,
        ge=0,
        le=600,
        description="Estimated waiting time in minutes"
    )

    source: str = Field(
        default="user",
        max_length=50
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=500
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


def get_report_or_404(
    report_id: str,
    db: Session
) -> CrowdReport:

    report = (
        db.query(CrowdReport)
        .filter(CrowdReport.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Crowd report not found"
        )

    return report


# ============================================================================
# SUBMIT A CROWD REPORT
# ============================================================================

@router.post("/", status_code=201)
def create_report(
    report_data: CrowdReportCreate,
    db: Session = Depends(get_db)
):

    get_location_or_404(
        report_data.location_id,
        db
    )

    report = CrowdReport(
        location_id=report_data.location_id,
        crowd_level=report_data.crowd_level,
        estimated_wait_minutes=(
            report_data.estimated_wait_minutes
        ),
        source=report_data.source,
        notes=report_data.notes,
        is_verified=False,
        created_at=datetime.utcnow()
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Crowd report submitted successfully",
        "report": {
            "id": str(report.id),
            "location_id": str(report.location_id),
            "crowd_level": report.crowd_level,
            "estimated_wait_minutes": (
                report.estimated_wait_minutes
            ),
            "source": report.source,
            "is_verified": report.is_verified,
            "created_at": (
                report.created_at.isoformat()
                if report.created_at
                else None
            )
        }
    }


# ============================================================================
# GET ALL REPORTS
# ============================================================================

@router.get("/")
def get_reports(
    location_id: Optional[str] = Query(default=None),
    verified: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):

    query = db.query(CrowdReport)

    if location_id:

        query = query.filter(
            CrowdReport.location_id == location_id
        )

    if verified is not None:

        query = query.filter(
            CrowdReport.is_verified == verified
        )

    reports = (
        query
        .order_by(CrowdReport.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "count": len(reports),
        "reports": [
            {
                "id": str(report.id),
                "location_id": str(report.location_id),
                "crowd_level": report.crowd_level,
                "estimated_wait_minutes": (
                    report.estimated_wait_minutes
                ),
                "source": report.source,
                "notes": report.notes,
                "is_verified": report.is_verified,
                "created_at": (
                    report.created_at.isoformat()
                    if report.created_at
                    else None
                )
            }
            for report in reports
        ]
    }


# ============================================================================
# GET ONE REPORT
# ============================================================================

@router.get("/{report_id}")
def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):

    report = get_report_or_404(
        report_id,
        db
    )

    return {
        "id": str(report.id),
        "location_id": str(report.location_id),
        "crowd_level": report.crowd_level,
        "estimated_wait_minutes": (
            report.estimated_wait_minutes
        ),
        "source": report.source,
        "notes": report.notes,
        "is_verified": report.is_verified,
        "created_at": (
            report.created_at.isoformat()
            if report.created_at
            else None
        )
    }


# ============================================================================
# VERIFY ONE REPORT
# ============================================================================

@router.post("/{report_id}/verify")
def verify_report(
    report_id: str,
    db: Session = Depends(get_db)
):

    report = get_report_or_404(
        report_id,
        db
    )

    if report.is_verified:

        return {
            "message": "Report is already verified",
            "report_id": str(report.id),
            "is_verified": True
        }

    report.is_verified = True

    db.commit()
    db.refresh(report)

    return {
        "message": "Report verified successfully",
        "report_id": str(report.id),
        "location_id": str(report.location_id),
        "is_verified": report.is_verified
    }


# ============================================================================
# BULK VERIFY REPORTS FOR A LOCATION
# ============================================================================

@router.post("/bulk-verify/{location_id}")
def bulk_verify_reports(
    location_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db)
):

    get_location_or_404(
        location_id,
        db
    )

    reports = (
        db.query(CrowdReport)
        .filter(
            CrowdReport.location_id == location_id,
            CrowdReport.is_verified.is_(False)
        )
        .order_by(CrowdReport.created_at.desc())
        .limit(limit)
        .all()
    )

    verified_count = 0

    for report in reports:

        report.is_verified = True

        verified_count += 1

    db.commit()

    return {
        "message": "Reports verified successfully",
        "location_id": location_id,
        "verified_count": verified_count
    }


# ============================================================================
# GET REPORT STATISTICS
# ============================================================================

@router.get("/location/{location_id}/stats")
def get_location_report_stats(
    location_id: str,
    db: Session = Depends(get_db)
):

    get_location_or_404(
        location_id,
        db
    )

    reports = (
        db.query(CrowdReport)
        .filter(
            CrowdReport.location_id == location_id
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
        "location_id": location_id,
        "total_reports": total_reports,
        "verified_reports": verified_reports,
        "unverified_reports": (
            total_reports - verified_reports
        ),
        "average_crowd_level": average_crowd,
        "average_wait_minutes": average_wait
    }
