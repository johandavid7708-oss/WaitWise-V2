from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.crowd_report import CrowdReport


class CrowdAnomalyDetector:

    """
    WaitWise Crowd Anomaly Detection Engine.

    Detects unusual crowd behavior by comparing
    recent verified reports against historical data.

    Current detection methods:

    - Statistical deviation
    - Sudden crowd changes
    - Historical time-pattern deviation
    - Rapid acceleration

    The detector returns explainable results so the
    frontend and alert system can tell users WHY
    something unusual is happening.
    """

    def __init__(self, session: Session):

        self.session = session

    # ========================================================================
    # MAIN ANALYSIS
    # ========================================================================

    def analyze(
        self,
        location_id
    ):

        reports = self._get_verified_reports(
            location_id
        )

        if len(reports) < 3:

            return self._insufficient_data_result(
                len(reports)
            )

        latest_report = reports[-1]

        statistical_result = (
            self._detect_statistical_anomaly(
                reports
            )
        )

        sudden_change_result = (
            self._detect_sudden_change(
                reports
            )
        )

        historical_result = (
            self._detect_historical_deviation(
                reports,
                latest_report
            )
        )

        acceleration_result = (
            self._detect_acceleration(
                reports
            )
        )

        anomalies = []

        # --------------------------------------------------------------------
        # Collect detected anomalies
        # --------------------------------------------------------------------

        for result in [

            statistical_result,
            sudden_change_result,
            historical_result,
            acceleration_result

        ]:

            if result["is_anomaly"]:

                anomalies.append(
                    result
                )

        # --------------------------------------------------------------------
        # Calculate overall anomaly score
        # --------------------------------------------------------------------

        if anomalies:

            anomaly_score = (

                sum(
                    anomaly["severity"]
                    for anomaly in anomalies
                )

                / len(anomalies)

            )

        else:

            anomaly_score = 0.0

        anomaly_score = max(
            0.0,
            min(1.0, anomaly_score)
        )

        # --------------------------------------------------------------------
        # Determine overall status
        # --------------------------------------------------------------------

        if anomaly_score >= 0.8:

            status = "critical"

        elif anomaly_score >= 0.6:

            status = "high"

        elif anomaly_score >= 0.3:

            status = "moderate"

        else:

            status = "normal"

        return {

            "location_id":
            str(location_id),

            "anomaly_detected":
            len(anomalies) > 0,

            "anomaly_score":
            round(anomaly_score, 3),

            "status":
            status,

            "latest_crowd_level":
            latest_report.crowd_level,

            "anomalies":
            anomalies,

            "analyzed_at":
            datetime.utcnow().isoformat(),

            "data_points":
            len(reports)

        }

    # ========================================================================
    # GET VERIFIED REPORTS
    # ========================================================================

    def _get_verified_reports(
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
                CrowdReport.created_at.asc()
            )

            .all()

        )

        return reports

    # ========================================================================
    # STATISTICAL ANOMALY
    # ========================================================================

    def _detect_statistical_anomaly(
        self,
        reports
    ):

        if len(reports) < 5:

            return {

                "type":
                "statistical_deviation",

                "is_anomaly":
                False,

                "severity":
                0.0,

                "message":
                "Not enough historical data."

            }

        historical_reports = (
            reports[:-1]
        )

        latest_value = (
            reports[-1].crowd_level
        )

        values = [

            report.crowd_level

            for report
            in historical_reports

        ]

        average = (
            sum(values)
            / len(values)
        )

        variance = (

            sum(
                (value - average) ** 2
                for value in values
            )

            / len(values)

        )

        standard_deviation = (
            variance ** 0.5
        )

        # Avoid division by zero

        if standard_deviation == 0:

            difference = abs(
                latest_value - average
            )

            is_anomaly = (
                difference >= 2
            )

            severity = min(
                1.0,
                difference / 4
            )

        else:

            z_score = abs(
                latest_value - average
            ) / standard_deviation

            is_anomaly = (
                z_score >= 2.0
            )

            severity = min(
                1.0,
                z_score / 4
            )

        return {

            "type":
            "statistical_deviation",

            "is_anomaly":
            is_anomaly,

            "severity":
            round(severity, 3),

            "message":

            (
                "Current
