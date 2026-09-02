from datetime import datetime

from sqlalchemy.orm import Session

from services.forecast_service import ForecastService
from services.crowd_service import CrowdService


class AlertService:

    """
    WaitWise Proactive Alert Intelligence Service.

    Evaluates crowd intelligence and generates alerts
    for important situations.

    Alert types include:

    - High crowd warnings
    - Rapid crowd increases
    - Crowd anomalies
    - Future congestion predictions
    - Good visiting opportunities
    """

    def __init__(self, session: Session):

        self.session = session

        self.forecast_service = ForecastService(
            session
        )

        self.crowd_service = CrowdService(
            session
        )

    # ========================================================================
    # GET ALL ALERTS FOR A LOCATION
    # ========================================================================

    def get_location_alerts(
        self,
        location_id
    ):

        forecast = (

            self.forecast_service
            .get_location_forecast(

                location_id,

                hours=3

            )

        )

        alerts = []

        current_alert = (

            self._check_current_crowd(
                forecast
            )

        )

        if current_alert:

            alerts.append(
                current_alert
            )

        trend_alert = (

            self._check_crowd_trend(
                forecast
            )

        )

        if trend_alert:

            alerts.append(
                trend_alert
            )

        anomaly_alert = (

            self._check_anomaly(
                forecast
            )

        )

        if anomaly_alert:

            alerts.append(
                anomaly_alert
            )

        future_alert = (

            self._check_future_crowd(
                forecast
            )

        )

        if future_alert:

            alerts.append(
                future_alert
            )

        opportunity_alert = (

            self._check_opportunity(
                forecast
            )

        )

        if opportunity_alert:

            alerts.append(
                opportunity_alert
            )

        alerts.sort(

            key=lambda alert:
            self._priority_value(
                alert["priority"]
            ),

            reverse=True

        )

        return {

            "location_id":
            str(location_id),

            "generated_at":
            datetime.utcnow().isoformat(),

            "alert_count":
            len(alerts),

            "alerts":
            alerts

        }

    # ========================================================================
    # HIGH CURRENT CROWD
    # ========================================================================

    def _check_current_crowd(
        self,
        forecast
    ):

        current = forecast.get(
            "current",
            {}
        )

        crowd_level = current.get(
            "crowd_level"
        )

        wait_time = current.get(
            "wait_time_minutes"
        )

        if crowd_level is None:

            return None

        if crowd_level >= 4.5:

            return {

                "type":
                "extreme_crowd",

                "priority":
                "critical",

                "title":
                "Extremely Crowded",

                "message":

                (
                    "This location is currently "
                    "extremely crowded. Significant "
                    "waiting is likely."
                ),

                "crowd_level":
                crowd_level,

                "wait_time_minutes":
                wait_time,

                "recommendation":
                "avoid"

            }

        if crowd_level >= 3.5:

            return {

                "type":
                "high_crowd",

                "priority":
                "high",

                "title":
                "High Crowd Detected",

                "message":

                (
                    "Crowd levels are currently "
                    "high. Consider visiting later "
                    "if possible."
                ),

                "crowd_level":
                crowd_level,

                "wait_time_minutes":
                wait_time,

                "recommendation":
                "consider_later"

            }

        return None

    # ========================================================================
    # CROWD TREND ALERT
    # ========================================================================

    def _check_crowd_trend(
        self,
        forecast
    ):

        trend = forecast.get(
            "trend",
            {}
        )

        current = forecast.get(
            "current",
            {}
        )

        trend_name = trend.get(
            "trend"
        )

        crowd_level = current.get(
            "crowd_level"
        )

        change = trend.get(
            "change",
            0
        )

        if (

            trend_name == "increasing"

            and

            crowd_level is not None

            and

            crowd_level >= 3

        ):

            return {

                "type":
                "crowd_increasing",

                "priority":
                "high",

                "title":
                "Crowd Increasing",

                "message":

                (
                    "Crowd levels are increasing "
                    "and may become significantly "
                    "higher soon."
                ),

                "change":
                change,

                "recommendation":
                "visit_soon_or_wait"

            }

        return None

    # ========================================================================
    # ANOMALY ALERT
    # ========================================================================

    def _check_anomaly(
        self,
        forecast
    ):

        anomaly = forecast.get(
            "anomaly",
            {}
        )

        if not anomaly.get(
            "anomaly_detected",
            False
        ):

            return None

        status = anomaly.get(
            "status",
            "moderate"
        )

        anomaly_score = anomaly.get(
            "anomaly_score",
            0
        )

        if status == "critical":

            priority = "critical"

        elif status == "high":

            priority = "high"

        else:

            priority = "medium"

        anomaly_messages = []

        for item in anomaly.get(
            "anomalies",
            []
        ):

            message = item.get(
                "message"
            )

            if message:

                anomaly_messages.append(
                    message
                )

        message = (

            anomaly_messages[0]

            if anomaly_messages

            else

            "Unusual crowd behavior has been detected."

        )

        return {

            "type":
            "crowd_anomaly",

            "priority":
            priority,

            "title":
            "Unusual Crowd Activity",

            "message":
            message,

            "anomaly_score":
            anomaly_score,

            "recommendation":
            "monitor"

        }

    # ========================================================================
    # FUTURE CROWD PREDICTION ALERT
    # ========================================================================

    def _check_future_crowd(
        self,
        forecast
    ):

        predictions = forecast.get(
            "forecast",
            []
        )

        if len(predictions) < 2:

            return None

        current_prediction = predictions[0]

        future_predictions = predictions[1:]

        current_crowd = current_prediction.get(
            "crowd_level"
        )

        if current_crowd is None:

            return None

        highest_future = max(

            future_predictions,

            key=lambda item:

            item.get(
                "crowd_level"
            )

            if item.get(
                "crowd_level"
            )
            is not None

            else -1

        )

        future_crowd = highest_future.get(
            "crowd_level"
        )

        if future_crowd is None:

            return None

        increase = (
            future_crowd
            - current_crowd
        )

        if (

            future_crowd >= 4

            and

            increase >= 0.8

        ):

            return {

                "type":
                "future_congestion",

                "priority":
                "high",

                "title":
                "Crowd Spike Predicted",

                "message":

                (
                    "Crowds are predicted to increase "
                    "significantly in the next few hours."
                ),

                "current_crowd":
                current_crowd,

                "predicted_crowd":
                future_crowd,

                "time":
                highest_future.get(
                    "time"
                ),

                "recommendation":
                "avoid_future_peak"

            }

        return None

    # ========================================================================
    # GOOD VISITING OPPORTUNITY
    # ========================================================================

    def _check_opportunity(
        self,
        forecast
    ):

        best_time = forecast.get(
            "best_time"
        )

        current = forecast.get(
            "current",
            {}
        )

        if not best_time:

            return None

        current_crowd = current.get(
            "crowd_level"
        )

        best_crowd = best_time.get(
            "predicted_crowd"
        )

        hour_offset = best_time.get(
            "hour_offset"
        )

        if (

            current_crowd is not None

            and

            best_crowd is not None

            and

            hour_offset is not None

            and

            hour_offset > 0

            and

            current_crowd
            - best_crowd
            >= 1.5

        ):

            return {

                "type":
                "better_time_ahead",

                "priority":
                "medium",

                "title":
                "Better Time Ahead",

                "message":

                (
                    "Crowd levels are expected to "
                    "drop significantly later."
                ),

                "best_time":
                best_time.get(
                    "time"
                ),

                "current_crowd":
                current_crowd,

                "predicted_crowd":
                best_crowd,

                "recommendation":
                "wait_for_better_time"

            }

        return None

    # ========================================================================
    # PRIORITY SCORE
    # ========================================================================

    def _priority_value(
        self,
        priority
    ):

        priorities = {

            "critical": 4,

            "high": 3,

            "medium": 2,

            "low": 1

        }

        return priorities.get(
            priority,
            0
        )

    # ========================================================================
    # GET HIGHEST PRIORITY ALERT
    # ========================================================================

    def get_top_alert(
        self,
        location_id
    ):

        result = self.get_location_alerts(
            location_id
        )

        alerts = result.get(
            "alerts",
            []
        )

        if not alerts:

            return {

                "has_alert":
                False,

                "alert":
                None

            }

        return {

            "has_alert":
            True,

            "alert":
            alerts[0]

        }
