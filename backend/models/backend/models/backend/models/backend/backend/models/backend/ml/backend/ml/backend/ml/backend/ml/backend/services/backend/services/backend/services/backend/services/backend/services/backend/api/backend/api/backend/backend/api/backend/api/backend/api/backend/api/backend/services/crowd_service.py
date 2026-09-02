from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models.crowd_report import CrowdReport
from models.location import Location


class CrowdService:
    """
    Core service for calculating reliable crowd intelligence
    from verified crowd reports.
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # LOCATION VALIDATION
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
    # RECENT VERIFIED REPORTS
    # =========================================================================

    def get_recent_verified_reports(
        self,
        location_id: str,
        hours: int = 6
    ):

        cutoff_time = (
            datetime.utcnow()
            - timedelta(hours=hours)
        )

        return (
            self.db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location_id,
                CrowdReport.is_verified.is_(True),
                CrowdReport.created_at >= cutoff_time
            )
            .order_by(CrowdReport.created_at.desc())
            .all()
        )

    # =========================================================================
    # ALL VERIFIED REPORTS
    # =========================================================================

    def get_verified_reports(
        self,
        location_id: str,
        limit: int = 500
    ):

        return (
            self.db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location_id,
                CrowdReport.is_verified.is_(True)
            )
            .order_by(CrowdReport.created_at.desc())
            .limit(limit)
            .all()
        )

    # =========================================================================
    # CURRENT CROWD INTELLIGENCE
    # =========================================================================

    def get_current_crowd(
        self,
        location_id: str,
        hours: int = 6
    ) -> dict:

        location = self.get_location(location_id)

        if not location:

            return {
                "location_id": location_id,
                "available": False,
                "reason": "Location not found"
            }

        reports = self.get_recent_verified_reports(
            location_id,
            hours
        )

        if not reports:

            return {
                "location_id": str(location.id),
                "location_name": location.name,
                "available": False,
                "reason": "No recent verified reports",
                "crowd_level": None,
                "wait_time_minutes": None,
                "report_count": 0,
                "confidence": 0
            }

        crowd_values = [
            report.crowd_level
            for report in reports
            if report.crowd_level is not None
        ]

        wait_values = [
            report.estimated_wait_minutes
            for report in reports
            if report.estimated_wait_minutes is not None
        ]

        if not crowd_values:

            return {
                "location_id": str(location.id),
                "location_name": location.name,
                "available": False,
                "reason": "Reports contain no crowd data",
                "crowd_level": None,
                "wait_time_minutes": None,
                "report_count": len(reports),
                "confidence": 0
            }

        average_crowd = (
            sum(crowd_values)
            / len(crowd_values)
        )

        average_wait = (
            sum(wait_values)
            / len(wait_values)
            if wait_values
            else 0
        )

        confidence = self.calculate_confidence(
            reports,
            hours
        )

        return {
            "location_id": str(location.id),
            "location_name": location.name,
            "available": True,
            "crowd_level": round(
                average_crowd,
                2
            ),
            "wait_time_minutes": round(
                average_wait,
                2
            ),
            "report_count": len(reports),
            "confidence": confidence,
            "latest_report_at": (
                reports[0].created_at.isoformat()
                if reports[0].created_at
                else None
            )
        }

    # =========================================================================
    # CONFIDENCE CALCULATION
    # =========================================================================

    def calculate_confidence(
        self,
        reports,
        hours: int
    ) -> int:

        if not reports:

            return 0

        # ---------------------------------------------------------------------
        # REPORT VOLUME
        # More independent reports = more confidence.
        # ---------------------------------------------------------------------

        report_score = min(
            len(reports) / 10,
            1.0
        ) * 50

        # ---------------------------------------------------------------------
        # RECENCY
        # Newer reports deserve more confidence.
        # ---------------------------------------------------------------------

        newest_report = reports[0]

        if newest_report.created_at:

            age_hours = (
                datetime.utcnow()
                - newest_report.created_at
            ).total_seconds() / 3600

            recency_ratio = max(
                0,
                1 - (age_hours / max(hours, 1))
            )

            recency_score = (
                recency_ratio * 30
            )

        else:

            recency_score = 0

        # ---------------------------------------------------------------------
        # AGREEMENT
        # Reports that agree with each other are more reliable.
        # ---------------------------------------------------------------------

        crowd_values = [
            report.crowd_level
            for report in reports
            if report.crowd_level is not None
        ]

        if len(crowd_values) <= 1:

            agreement_score = 10

        else:

            average = (
                sum(crowd_values)
                / len(crowd_values)
            )

            variance = (
                sum(
                    (value - average) ** 2
                    for value in crowd_values
                )
                / len(crowd_values)
            )

            # Lower variance means stronger agreement.
            normalized_variance = min(
                variance / 2500,
                1
            )

            agreement_score = (
                (1 - normalized_variance)
                * 20
            )

        confidence = (
            report_score
            + recency_score
            + agreement_score
        )

        return max(
            0,
            min(100, round(confidence))
        )

    # =========================================================================
    # CROWD TREND
    # =========================================================================

    def get_crowd_trend(
        self,
        location_id: str,
        hours: int = 6
    ) -> dict:

        reports = self.get_recent_verified_reports(
            location_id,
            hours
        )

        if len(reports) < 2:

            return {
                "direction": "stable",
                "change": 0,
                "confidence": 0
            }

        # Reports arrive newest first.
        newest = reports[0]
        oldest = reports[-1]

        change = (
            newest.crowd_level
            - oldest.crowd_level
        )

        if change >= 25:

            direction = "rapidly_increasing"

        elif change >= 8:

            direction = "increasing"

        elif change <= -25:

            direction = "rapidly_decreasing"

        elif change <= -8:

            direction = "decreasing"

        else:

            direction = "stable"

        return {
            "direction": direction,
            "change": round(change, 2),
            "confidence": self.calculate_confidence(
                reports,
                hours
            )
        }
