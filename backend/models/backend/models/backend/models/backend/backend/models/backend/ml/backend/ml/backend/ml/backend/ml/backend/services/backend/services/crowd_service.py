from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.crowd_report import CrowdReport


class CrowdService:

    """
    WaitWise Crowd Intelligence Service.

    Handles:

    - Crowd report creation
    - Report verification
    - Current crowd calculation
    - Recent crowd trends
    - Historical crowd summaries
    """

    def __init__(self, session: Session):

        self.session = session

    # ========================================================================
    # CREATE CROWD REPORT
    # ========================================================================

    def create_report(

        self,

        location_id,

        crowd_level,

        wait_time_minutes=None,

        user_id=None,

        source="user"

    ):

        if crowd_level < 1 or crowd_level > 5:

            raise ValueError(
                "Crowd level must be between 1 and 5."
            )

        if (

            wait_time_minutes is not None

            and

            wait_time_minutes < 0

        ):

            raise ValueError(
                "Wait time cannot be negative."
            )

        report = CrowdReport(

            location_id=location_id,

            user_id=user_id,

            crowd_level=crowd_level,

            wait_time_minutes=wait_time_minutes,

            source=source,

            is_verified=False,

            created_at=datetime.utcnow()

        )

        self.session.add(report)

        self.session.commit()

        self.session.refresh(report)

        return report

    # ========================================================================
    # VERIFY A REPORT
    # ========================================================================

    def verify_report(
        self,
        report_id
    ):

        report = (

            self.session
            .query(CrowdReport)

            .filter(
                CrowdReport.id == report_id
            )

            .first()

        )

        if report is None:

            return None

        report.is_verified = True

        self.session.commit()

        self.session.refresh(report)

        return report

    # ========================================================================
    # BULK VERIFY RECENT REPORTS
    # ========================================================================

    def bulk_verify_reports(

        self,

        location_id,

        hours=1

    ):

        cutoff_time = (

            datetime.utcnow()

            -

            timedelta(hours=hours)

        )

        reports = (

            self.session
            .query(CrowdReport)

            .filter(

                CrowdReport.location_id
                == location_id,

                CrowdReport.created_at
                >= cutoff_time,

                CrowdReport.is_verified
                == False

            )

            .all()

        )

        verified_count = 0

        for report in reports:

            report.is_verified = True

            verified_count += 1

        self.session.commit()

        return {

            "location_id":
            str(location_id),

            "verified_reports":
            verified_count

        }

    # ========================================================================
    # GET CURRENT CROWD STATUS
    # ========================================================================

    def get_current_crowd(
        self,
        location_id
    ):

        cutoff_time = (

            datetime.utcnow()

            -

            timedelta(hours=2)

        )

        reports = (

            self.session
            .query(CrowdReport)

            .filter(

                CrowdReport.location_id
                == location_id,

                CrowdReport.is_verified
                == True,

                CrowdReport.created_at
                >= cutoff_time

            )

            .order_by(
                CrowdReport.created_at.desc()
            )

            .all()

        )

        if not reports:

            return {

                "location_id":
                str(location_id),

                "crowd_level":
                None,

                "wait_time_minutes":
                None,

                "confidence":
                0.0,

                "data_points":
                0,

                "status":
                "no_recent_data"

            }

        # --------------------------------------------------------------------
        # Calculate average crowd
        # --------------------------------------------------------------------

        average_crowd = (

            sum(
                report.crowd_level
                for report in reports
            )

            /

            len(reports)

        )

        # --------------------------------------------------------------------
        # Calculate average wait
        # --------------------------------------------------------------------

        reports_with_wait = [

            report

            for report in reports

            if report.wait_time_minutes
            is not None

        ]

        if reports_with_wait:

            average_wait = (

                sum(

                    report.wait_time_minutes

                    for report
                    in reports_with_wait

                )

                /

                len(reports_with_wait)

            )

        else:

            average_wait = None

        # --------------------------------------------------------------------
        # Calculate confidence
        # --------------------------------------------------------------------

        confidence = min(

            0.95,

            0.3

            +

            (
                len(reports)
                * 0.1
            )

        )

        return {

            "location_id":
            str(location_id),

            "crowd_level":
            round(average_crowd, 2),

            "wait_time_minutes":

            (
                round(average_wait)

                if average_wait
                is not None

                else None
            ),

            "confidence":
            round(confidence, 3),

            "data_points":
            len(reports),

            "status":
            self._get_crowd_status(
                average_crowd
            )

        }

    # ========================================================================
    # GET RECENT CROWD TREND
    # ========================================================================

    def get_crowd_trend(
        self,
        location_id
    ):

        reports = (

            self.session
            .query(CrowdReport)

            .filter(

                CrowdReport.location_id
                == location_id,

                CrowdReport.is_verified
                == True

            )

            .order_by(
                CrowdReport.created_at.desc()
            )

            .limit(10)

            .all()

        )

        # Reverse into chronological order

        reports = list(
            reversed(reports)
        )

        if len(reports) < 2:

            return {

                "trend":
                "unknown",

                "change":
                0

            }

        first_value = (
            reports[0].crowd_level
        )

        last_value = (
            reports[-1].crowd_level
        )

        change = (
            last_value
            - first_value
        )

        if change >= 1:

            trend = "increasing"

        elif change <= -1:

            trend = "decreasing"

        else:

            trend = "stable"

        return {

            "trend":
            trend,

            "change":
            change,

            "data_points":
            len(reports)

        }

    # ========================================================================
    # GET CROWD HISTORY
    # ========================================================================

    def get_history(

        self,

        location_id,

        hours=24

    ):

        cutoff_time = (

            datetime.utcnow()

            -

            timedelta(hours=hours)

        )

        reports = (

            self.session
            .query(CrowdReport)

            .filter(

                CrowdReport.location_id
                == location_id,

                CrowdReport.is_verified
                == True,

                CrowdReport.created_at
                >= cutoff_time

            )

            .order_by(
                CrowdReport.created_at.asc()
            )

            .all()

        )

        return [

            {

                "id":
                str(report.id),

                "crowd_level":
                report.crowd_level,

                "wait_time_minutes":
                report.wait_time_minutes,

                "created_at":

                report.created_at.isoformat()

            }

            for report in reports

        ]

    # ========================================================================
    # CROWD LEVEL → HUMAN STATUS
    # ========================================================================

    def _get_crowd_status(
        self,
        crowd_level
    ):

        if crowd_level < 1.5:

            return "very_low"

        elif crowd_level < 2.5:

            return "low"

        elif crowd_level < 3.5:

            return "moderate"

       
