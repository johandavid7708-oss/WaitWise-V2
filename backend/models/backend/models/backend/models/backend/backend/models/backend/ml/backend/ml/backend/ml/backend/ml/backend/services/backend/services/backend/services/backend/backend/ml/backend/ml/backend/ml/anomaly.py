from datetime import datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session

from models.crowd_report import CrowdReport


class AnomalyDetector:
    """
    Detects unusual crowd reports.

    The detector compares a new report against recent
    verified reports from the same location.

    It can identify:

    - Extremely unusual crowd levels
    - Unusual waiting times
    - Sudden changes from recent conditions
    - Reports that statistically differ from normal patterns
    """

    MIN_BASELINE_SAMPLES = 5

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # BASELINE DATA
    # =========================================================================

    def get_recent_verified_reports(
        self,
        location_id: str,
        hours: int = 24,
        limit: int = 100
    ) -> list:

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
            .order_by(
                CrowdReport.created_at.desc()
            )
            .limit(limit)
            .all()
        )

    # =========================================================================
    # Z-SCORE
    # =========================================================================

    @staticmethod
    def calculate_z_score(
        value: float,
        values: list
    ) -> float:

        if len(values) < 2:
            return 0.0

        mean = float(np.mean(values))
        standard_deviation = float(np.std(values))

        # If all historical values are identical,
        # avoid division by zero.

        if standard_deviation == 0:

            if value == mean:
                return 0.0

            return float("inf")

        return abs(
            (value - mean)
            / standard_deviation
        )

    # =========================================================================
    # CROWD LEVEL ANOMALY
    # =========================================================================

    def analyze_crowd_level(
        self,
        location_id: str,
        crowd_level: float
    ) -> dict:

        reports = self.get_recent_verified_reports(
            location_id
        )

        crowd_values = [
            report.crowd_level
            for report in reports
            if report.crowd_level is not None
        ]

        if len(crowd_values) < self.MIN_BASELINE_SAMPLES:

            return {
                "available": False,
                "is_anomaly": False,
                "reason": "Not enough baseline data",
                "z_score": None
            }

        z_score = self.calculate_z_score(
            crowd_level,
            crowd_values
        )

        # General statistical anomaly threshold.
        is_anomaly = z_score >= 3.0

        average = float(np.mean(crowd_values))

        difference = abs(
            crowd_level - average
        )

        return {
            "available": True,

            "is_anomaly": is_anomaly,

            "z_score": round(z_score, 2),

            "recent_average": round(
                average,
                2
            ),

            "difference_from_average": round(
                difference,
                2
            ),

            "baseline_samples": len(
                crowd_values
            )
        }

    # =========================================================================
    # WAIT TIME ANOMALY
    # =========================================================================

    def analyze_wait_time(
        self,
        location_id: str,
        wait_time_minutes: float
    ) -> dict:

        reports = self.get_recent_verified_reports(
            location_id
        )

        wait_values = [
            report.estimated_wait_minutes
            for report in reports
            if report.estimated_wait_minutes is not None
        ]

        if len(wait_values) < self.MIN_BASELINE_SAMPLES:

            return {
                "available": False,
                "is_anomaly": False,
                "reason": "Not enough baseline data",
                "z_score": None
            }

        z_score = self.calculate_z_score(
            wait_time_minutes,
            wait_values
        )

        is_anomaly = z_score >= 3.0

        average = float(np.mean(wait_values))

        difference = abs(
            wait_time_minutes - average
        )

        return {
            "available": True,

            "is_anomaly": is_anomaly,

            "z_score": round(z_score, 2),

            "recent_average": round(
                average,
                2
            ),

            "difference_from_average": round(
                difference,
                2
            ),

            "baseline_samples": len(
                wait_values
            )
        }

    # =========================================================================
    # COMPLETE REPORT ANALYSIS
    # =========================================================================

    def analyze_report(
        self,
        location_id: str,
        crowd_level: float | None,
        wait_time_minutes: float | None
    ) -> dict:

        crowd_analysis = None
        wait_analysis = None

        if crowd_level is not None:

            crowd_analysis = self.analyze_crowd_level(
                location_id=location_id,
                crowd_level=crowd_level
            )

        if wait_time_minutes is not None:

            wait_analysis = self.analyze_wait_time(
                location_id=location_id,
                wait_time_minutes=wait_time_minutes
            )

        anomaly_flags = []

        if (
            crowd_analysis
            and crowd_analysis.get("is_anomaly")
        ):

            anomaly_flags.append(
                "unusual_crowd_level"
            )

        if (
            wait_analysis
            and wait_analysis.get("is_anomaly")
        ):

            anomaly_flags.append(
                "unusual_wait_time"
            )

        # ---------------------------------------------------------------------
        # SEVERITY
        # ---------------------------------------------------------------------

        if len(anomaly_flags) >= 2:

            severity = "high"

        elif len(anomaly_flags) == 1:

            severity = "medium"

        else:

            severity = "normal"

        return {
            "location_id": location_id,

            "is_anomaly": len(anomaly_flags) > 0,

            "severity": severity,

            "flags": anomaly_flags,

            "crowd_analysis": crowd_analysis,

            "wait_analysis": wait_analysis
        }

    # =========================================================================
    # SUDDEN CROWD CHANGE
    # =========================================================================

    def detect_sudden_change(
        self,
        location_id: str,
        crowd_level: float,
        threshold: float = 30
    ) -> dict:

        reports = self.get_recent_verified_reports(
            location_id=location_id,
            hours=6,
            limit=10
        )

        if not reports:

            return {
                "available": False,
                "sudden_change": False,
                "reason": "No recent verified reports"
            }

        latest_report = reports[0]

        if latest_report.crowd_level is None:

            return {
                "available": False,
                "sudden_change": False,
                "reason": "Latest report has no crowd data"
            }

        difference = abs(
            crowd_level
            - latest_report.crowd_level
        )

        sudden_change = (
            difference >= threshold
        )

        return {
            "available": True,

            "sudden_change": sudden_change,

            "previous_crowd_level": (
                latest_report.crowd_level
            ),

            "new_crowd_level": crowd_level,

            "change": round(
                difference,
                2
            )
        }
