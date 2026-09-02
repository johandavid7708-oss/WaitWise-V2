from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.crowd_report import CrowdReport


class CrowdPredictor:

    """
    WaitWise Crowd Prediction Engine.

    Generates crowd and waiting-time predictions using:

    - Verified historical reports
    - Time-of-day patterns
    - Day-of-week patterns
    - Recent crowd trends
    - Data freshness
    - Forecast horizon
    """

    def __init__(self, session: Session):

        self.session = session

    # ========================================================================
    # MAIN PREDICTION METHOD
    # ========================================================================

    def predict(
        self,
        location_id,
        horizon_minutes=30
    ):

        forecast_time = (
            datetime.utcnow()
            + timedelta(minutes=horizon_minutes)
        )

        reports = self._get_verified_reports(
            location_id
        )

        # --------------------------------------------------------------------
        # No reliable data available
        # --------------------------------------------------------------------

        if not reports:

            return self._default_prediction(
                horizon_minutes
            )

        # --------------------------------------------------------------------
        # Calculate different intelligence signals
        # --------------------------------------------------------------------

        historical_crowd = (
            self._calculate_historical_average(
                reports
            )
        )

        time_pattern = (
            self._calculate_time_pattern(
                reports,
                forecast_time
            )
        )

        recent_trend = (
            self._calculate_recent_trend(
                reports
            )
        )

        predicted_crowd = (
            self._combine_signals(
                historical_crowd,
                time_pattern,
                recent_trend
            )
        )

        predicted_wait = (
            self._predict_wait_time(
                reports,
                predicted_crowd
            )
        )

        confidence = (
            self._calculate_confidence(
                reports,
                forecast_time
            )
        )

        return {

            "predicted_crowd_level":
            round(predicted_crowd, 2),

            "predicted_wait_time":
            predicted_wait,

            "confidence_score":
            round(confidence, 3),

            "forecast_for":
            forecast_time,

            "prediction_horizon":
            horizon_minutes,

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
                CrowdReport.location_id == location_id,
                CrowdReport.is_verified == True
            )

            .order_by(
                CrowdReport.created_at.asc()
            )

            .all()

        )

        return reports

    # ========================================================================
    # HISTORICAL AVERAGE
    # ========================================================================

    def _calculate_historical_average(
        self,
        reports
    ):

        if not reports:
            return 3.0

        total = sum(
            report.crowd_level
            for report in reports
        )

        return total / len(reports)

    # ========================================================================
    # TIME-BASED PATTERN ANALYSIS
    # ========================================================================

    def _calculate_time_pattern(
        self,
        reports,
        forecast_time
    ):

        matching_reports = []

        forecast_hour = forecast_time.hour

        forecast_weekday = (
            forecast_time.weekday()
        )

        for report in reports:

            report_time = report.created_at

            same_hour = (
                abs(
                    report_time.hour
                    - forecast_hour
                ) <= 1
            )

            same_day = (
                report_time.weekday()
                == forecast_weekday
            )

            if same_hour and same_day:

                matching_reports.append(
                    report
                )

        if not matching_reports:

            return None

        total = sum(
            report.crowd_level
            for report in matching_reports
        )

        return (
            total
            / len(matching_reports)
        )

    # ========================================================================
    # RECENT TREND ANALYSIS
    # ========================================================================

    def _calculate_recent_trend(
        self,
        reports
    ):

        # Need enough reports to identify a trend

        if len(reports) < 4:

            return 0.0

        recent_reports = reports[-5:]

        first_value = (
            recent_reports[0].crowd_level
        )

        last_value = (
            recent_reports[-1].crowd_level
        )

        trend = (
            last_value - first_value
        )

        # Normalize trend

        return max(
            -1.0,
            min(1.0, trend / 4.0)
        )

    # ========================================================================
    # SIGNAL COMBINATION
    # ========================================================================

    def _combine_signals(
        self,
        historical_crowd,
        time_pattern,
        recent_trend
    ):

        prediction = historical_crowd

        # Time pattern is highly useful

        if time_pattern is not None:

            prediction = (

                historical_crowd * 0.4

                +

                time_pattern * 0.6

            )

        # Recent trend slightly adjusts
        # the future prediction

        prediction += (
            recent_trend * 0.8
        )

        # Crowd level must stay between 1 and 5

        prediction = max(
            1.0,
            min(5.0, prediction)
        )

        return prediction

    # ========================================================================
    # WAIT TIME PREDICTION
    # ========================================================================

    def _predict_wait_time(
        self,
        reports,
        predicted_crowd
    ):

        reports_with_wait = [

            report

            for report in reports

            if report.wait_time_minutes
            is not None

        ]

        # No waiting data

        if not reports_with_wait:

            # Basic fallback relationship

            estimated_wait = (
                max(
                    0,
                    (predicted_crowd - 1)
                    * 10
                )
            )

            return round(
                estimated_wait
            )

        # Calculate average wait

        average_wait = (

            sum(
                report.wait_time_minutes
                for report in reports_with_wait
            )

            /

            len(reports_with_wait)

        )

        average_crowd = (

            sum(
                report.crowd_level
                for report in reports_with_wait
            )

            /

            len(reports_with_wait)

        )

        # Adjust waiting time according
        # to predicted crowd

        if average_crowd > 0:

            crowd_ratio = (
                predicted_crowd
                / average_crowd
            )

        else:

            crowd_ratio = 1.0

        predicted_wait = (
            average_wait * crowd_ratio
        )

        return max(
            0,
            round(predicted_wait)
        )

    # ========================================================================
    # CONFIDENCE CALCULATION
    # ========================================================================

    def _calculate_confidence(
        self,
        reports,
        forecast_time
    ):

        data_count = len(reports)

        # --------------------------------------------------------------------
        # More historical data = higher confidence
        # --------------------------------------------------------------------

        data_score = min(
            1.0,
            data_count / 50
        )

        # --------------------------------------------------------------------
        # Check data freshness
        # --------------------------------------------------------------------

        latest_report = reports[-1]

        age_hours = (

            datetime.utcnow()
            - latest_report.created_at

        ).total_seconds() / 3600

        freshness_score = max(

            0.0,

            1.0
            - (
                age_hours / 168
            )

        )

        # --------------------------------------------------------------------
        # Time pattern availability
        # --------------------------------------------------------------------

        time_pattern = (
            self._calculate_time_pattern(
                reports,
                forecast_time
            )
        )

        pattern_score = (

            1.0

            if time_pattern
            is not None

            else 0.4

        )

        # --------------------------------------------------------------------
        # Final weighted confidence
        # --------------------------------------------------------------------

        confidence = (

            data_score * 0.45

            +

            freshness_score * 0.35

            +

            pattern_score * 0.20

        )

        return max(
            0.05,
            min(0.99, confidence)
        )

    # ========================================================================
    # DEFAULT PREDICTION
    # ========================================================================

    def _default_prediction(
        self,
        horizon_minutes
    ):

        forecast_time = (

            datetime.utcnow()

            +

            timedelta(
                minutes=horizon_minutes
            )

        )

        return {

            "predicted_crowd_level": 3.0,

            "predicted_wait_time": 20,

            "confidence_score": 0.05,

            "forecast_for": forecast_time,

            "prediction_horizon":
            horizon_minutes,

            "data_points": 0

        }
