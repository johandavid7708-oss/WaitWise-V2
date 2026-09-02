from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ml.predictor import CrowdPredictor
from ml.learner import CrowdLearner
from ml.anomaly import CrowdAnomalyDetector

from services.crowd_service import CrowdService


class ForecastService:

    """
    WaitWise Forecast Intelligence Service.

    Combines:

    - Current crowd intelligence
    - ML crowd prediction
    - Learning patterns
    - Crowd anomaly detection
    - Confidence calculation

    This service creates the complete intelligence
    response used by the WaitWise API and frontend.
    """

    def __init__(self, session: Session):

        self.session = session

        self.crowd_service = CrowdService(
            session
        )

        self.predictor = CrowdPredictor(
            session
        )

        self.learner = CrowdLearner(
            session
        )

        self.anomaly_detector = (
            CrowdAnomalyDetector(
                session
            )
        )

    # ========================================================================
    # COMPLETE LOCATION FORECAST
    # ========================================================================

    def get_location_forecast(
        self,
        location_id,
        hours=4
    ):

        # --------------------------------------------------------------------
        # CURRENT CROWD
        # --------------------------------------------------------------------

        current_crowd = (

            self.crowd_service
            .get_current_crowd(
                location_id
            )

        )

        # --------------------------------------------------------------------
        # CURRENT TREND
        # --------------------------------------------------------------------

        trend = (

            self.crowd_service
            .get_crowd_trend(
                location_id
            )

        )

        # --------------------------------------------------------------------
        # ANOMALY ANALYSIS
        # --------------------------------------------------------------------

        anomaly = (

            self.anomaly_detector
            .analyze(
                location_id
            )

        )

        # --------------------------------------------------------------------
        # FUTURE PREDICTIONS
        # --------------------------------------------------------------------

        predictions = self.get_forecast_timeline(

            location_id,

            hours

        )

        # --------------------------------------------------------------------
        # BEST TIME TO VISIT
        # --------------------------------------------------------------------

        best_time = (

            self.get_best_time_to_visit(
                predictions
            )

        )

        # --------------------------------------------------------------------
        # PEAK TIME
        # --------------------------------------------------------------------

        peak_time = (

            self.get_peak_time(
                predictions
            )

        )

        # --------------------------------------------------------------------
        # OVERALL RECOMMENDATION
        # --------------------------------------------------------------------

        recommendation = (

            self._generate_recommendation(

                current_crowd,

                trend,

                anomaly,

                best_time

            )

        )

        return {

            "location_id":
            str(location_id),

            "generated_at":
            datetime.utcnow().isoformat(),

            "current":
            current_crowd,

            "trend":
            trend,

            "anomaly":
            anomaly,

            "forecast":
            predictions,

            "best_time":
            best_time,

            "peak_time":
            peak_time,

            "recommendation":
            recommendation

        }

    # ========================================================================
    # FORECAST TIMELINE
    # ========================================================================

    def get_forecast_timeline(

        self,

        location_id,

        hours=4

    ):

        predictions = []

        now = datetime.utcnow()

        for hour_offset in range(
            hours + 1
        ):

            forecast_time = (

                now

                +

                timedelta(
                    hours=hour_offset
                )

            )

            prediction = (

                self.predictor.predict(

                    location_id,

                    forecast_time

                )

            )

            formatted_prediction = {

                "time":

                forecast_time.isoformat(),

                "hour_offset":

                hour_offset,

                "crowd_level":

                prediction.get(
                    "crowd_level"
                ),

                "wait_time_minutes":

                prediction.get(
                    "wait_time_minutes"
                ),

                "confidence":

                prediction.get(
                    "confidence"
                ),

                "status":

                self._crowd_level_to_status(

                    prediction.get(
                        "crowd_level"
                    )

                )

            }

            predictions.append(
                formatted_prediction
            )

        return predictions

    # ========================================================================
    # BEST TIME TO VISIT
    # ========================================================================

    def get_best_time_to_visit(
        self,
        predictions
    ):

        if not predictions:

            return None

        valid_predictions = [

            prediction

            for prediction
            in predictions

            if prediction.get(
                "crowd_level"
            )
            is not None

        ]

        if not valid_predictions:

            return None

        best = min(

            valid_predictions,

            key=lambda prediction:

            prediction[
                "crowd_level"
            ]

        )

        return {

            "time":
            best["time"],

            "hour_offset":
            best["hour_offset"],

            "predicted_crowd":
            best["crowd_level"],

            "predicted_wait":
            best["wait_time_minutes"],

            "confidence":
            best["confidence"]

        }

    # ========================================================================
    # PEAK TIME DETECTION
    # ========================================================================

    def get_peak_time(
        self,
        predictions
    ):

        if not predictions:

            return None

        valid_predictions = [

            prediction

            for prediction
            in predictions

            if prediction.get(
                "crowd_level"
            )
            is not None

        ]

        if not valid_predictions:

            return None

        peak = max(

            valid_predictions,

            key=lambda prediction:

            prediction[
                "crowd_level"
            ]

        )

        return {

            "time":
            peak["time"],

            "hour_offset":
            peak["hour_offset"],

            "predicted_crowd":
            peak["crowd_level"],

            "predicted_wait":
            peak["wait_time_minutes"],

            "confidence":
            peak["confidence"]

        }

    # ========================================================================
    # QUICK FORECAST
    # ========================================================================

    def get_quick_forecast(
        self,
        location_id
    ):

        predictions = (

            self.get_forecast_timeline(

                location_id,

                hours=2

            )

        )

        return {

            "now":

            predictions[0]
            if len(predictions) > 0
            else None,

            "in_1_hour":

            predictions[1]
            if len(predictions) > 1
            else None,

            "in_2_hours":

            predictions[2]
            if len(predictions) > 2
            else None

        }

    # ========================================================================
    # FORECAST CONFIDENCE
    # ========================================================================

    def calculate_forecast_confidence(

        self,

        location_id,

        predictions

    ):

        if not predictions:

            return 0.0

        confidence_values = [

            prediction.get(
                "confidence",
                0
            )

            for prediction
            in predictions

            if prediction.get(
                "confidence"
            )
            is not None

        ]

        if not confidence_values:

            return 0.0

        average_confidence = (

            sum(confidence_values)

            /

            len(confidence_values)

        )

        return round(
            average_confidence,
            3
        )

    # ========================================================================
    # GENERATE HUMAN RECOMMENDATION
    # ========================================================================

    def _generate_recommendation(

        self,

        current_crowd,

        trend,

        anomaly,

        best_time

    ):

        crowd_level = (

            current_crowd.get(
                "crowd_level"
            )

        )

        crowd_trend = (

            trend.get(
                "trend"
            )

        )

        anomaly_detected = (

            anomaly.get(
                "anomaly_detected",
                False
            )

        )

        anomaly_status = (

            anomaly.get(
                "status",
                "normal"
            )

        )

        # --------------------------------------------------------------------
        # NO DATA
        # --------------------------------------------------------------------

        if crowd_level is None:

            return {

                "decision":
                "unknown",

                "message":

                "Not enough recent crowd data is "

                "available for a reliable recommendation."

            }

        # --------------------------------------------------------------------
        # CRITICAL ANOMALY
        # --------------------------------------------------------------------

        if (

            anomaly_detected

            and

            anomaly_status
            in ["critical", "high"]

        ):

            return {

                "decision":
                "avoid",

                "message":

                "Unusual crowd activity has been "

                "detected. Consider avoiding this "

                "location temporarily.",

                "reason":
                "crowd_anomaly"

            }

        # --------------------------------------------------------------------
        # VERY HIGH CROWD
        # --------------------------------------------------------------------

        if crowd_level >= 4.5:

            return {

                "decision":
                "avoid",

                "message":

                "This location is currently extremely "

                "crowded. Waiting may be significant.",

                "reason":
                "very_high_crowd"

            }

        # --------------------------------------------------------------------
        # HIGH AND INCREASING
        # --------------------------------------------------------------------

        if (

            crowd_level >= 3.5

            and

            crowd_trend == "increasing"

        ):

            return {

                "decision":
                "wait",

                "message":

                "Crowds are increasing. It may be "

                "better to visit later.",

                "best_time":
                best_time,

                "reason":
                "increasing_crowd"

            }

        # --------------------------------------------------------------------
        # LOW CROWD
        # --------------------------------------------------------------------

        if crowd_level <= 2.5:

            return {

                "decision":
                "go_now",

                "message":

                "Current crowd conditions look good. "

                "This is a good time to visit.",

                "reason":
                "low_crowd"

            }

        # --------------------------------------------------------------------
        # MODERATE CROWD
        # --------------------------------------------------------------------

        return {

            "decision":
            "consider",

            "message":

            "Crowd levels are moderate. Your decision "

            "may depend on your waiting preference.",

            "best_time":
            best_time,

            "reason":
            "moderate_crowd"

        }

    # ========================================================================
    # CROWD LEVEL → STATUS
    # ========================================================================

    def _crowd_level_to_status(
        self,
        crowd_level
    ):

        if crowd_level is None:

            return "unknown"

        if crowd_level < 1.5:

            return "very_low"

        elif crowd_level < 2.5:

            return "low"

        elif crowd_level < 3.5:

            return "moderate"

        elif crowd_level < 4.5:

            return "high"

        return "very_high"
