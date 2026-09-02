from sqlalchemy.orm import Session

from models.location import Location

from services.crowd_service import CrowdService
from services.forecast_service import ForecastService


class RecommendationService:

    """
    WaitWise Smart Recommendation Engine.

    Evaluates locations and recommends the best
    available option based on:

    - Current crowd level
    - Expected waiting time
    - Crowd trend
    - Future forecast
    - Crowd anomalies
    - User preferences

    The scoring system is intentionally explainable.
    Every recommendation includes the reason behind
    the decision.
    """

    def __init__(self, session: Session):

        self.session = session

        self.crowd_service = CrowdService(
            session
        )

        self.forecast_service = ForecastService(
            session
        )

    # ========================================================================
    # GET RECOMMENDATIONS
    # ========================================================================

    def get_recommendations(

        self,

        limit=5,

        category=None,

        max_wait=None,

        preferred_location_id=None

    ):

        query = self.session.query(
            Location
        )

        # --------------------------------------------------------------------
        # FILTER BY CATEGORY
        # --------------------------------------------------------------------

        if category:

            query = query.filter(
                Location.category == category
            )

        locations = query.all()

        recommendations = []

        for location in locations:

            result = self.evaluate_location(

                location,

                max_wait=max_wait,

                preferred_location_id=
                preferred_location_id

            )

            recommendations.append(
                result
            )

        # --------------------------------------------------------------------
        # SORT BY SMART SCORE
        # --------------------------------------------------------------------

        recommendations.sort(

            key=lambda item:
            item["smart_score"],

            reverse=True

        )

        return recommendations[:limit]

    # ========================================================================
    # EVALUATE SINGLE LOCATION
    # ========================================================================

    def evaluate_location(

        self,

        location,

        max_wait=None,

        preferred_location_id=None

    ):

        location_id = location.id

        # --------------------------------------------------------------------
        # GET CURRENT CROWD
        # --------------------------------------------------------------------

        current = (

            self.crowd_service
            .get_current_crowd(
                location_id
            )

        )

        # --------------------------------------------------------------------
        # GET TREND
        # --------------------------------------------------------------------

        trend = (

            self.crowd_service
            .get_crowd_trend(
                location_id
            )

        )

        # --------------------------------------------------------------------
        # GET FORECAST
        # --------------------------------------------------------------------

        forecast = (

            self.forecast_service
            .get_quick_forecast(
                location_id
            )

        )

        # --------------------------------------------------------------------
        # GET FULL FORECAST INTELLIGENCE
        # --------------------------------------------------------------------

        intelligence = (

            self.forecast_service
            .get_location_forecast(

                location_id,

                hours=2

            )

        )

        anomaly = intelligence.get(
            "anomaly",
            {}
        )

        # --------------------------------------------------------------------
        # CALCULATE SCORE
        # --------------------------------------------------------------------

        scoring = self._calculate_score(

            current=current,

            trend=trend,

            forecast=forecast,

            anomaly=anomaly,

            max_wait=max_wait,

            preferred_location_id=
            preferred_location_id,

            location_id=location_id

        )

        # --------------------------------------------------------------------
        # CREATE EXPLANATION
        # --------------------------------------------------------------------

        explanation = (

            self._generate_explanation(

                current=current,

                trend=trend,

                anomaly=anomaly,

                scoring=scoring

            )

        )

        return {

            "location_id":
            str(location.id),

            "location_name":
            location.name,

            "category":
            location.category,

            "latitude":
            float(location.latitude)
            if location.latitude is not None
            else None,

            "longitude":
            float(location.longitude)
            if location.longitude is not None
            else None,

            "current":
            current,

            "trend":
            trend,

            "forecast":
            forecast,

            "anomaly":
            anomaly,

            "smart_score":
            scoring["score"],

            "score_breakdown":
            scoring["breakdown"],

            "recommendation":
            explanation

        }

    # ========================================================================
    # SMART SCORING ENGINE
    # ========================================================================

    def _calculate_score(

        self,

        current,

        trend,

        forecast,

        anomaly,

        max_wait,

        preferred_location_id,

        location_id

    ):

        score = 100.0

        breakdown = {}

        # --------------------------------------------------------------------
        # CROWD SCORE
        # --------------------------------------------------------------------

        crowd_level = current.get(
            "crowd_level"
        )

        if crowd_level is None:

            crowd_penalty = 20

        else:

            crowd_penalty = (
                crowd_level - 1
            ) * 12

        score -= crowd_penalty

        breakdown["crowd_penalty"] = round(
            crowd_penalty,
            2
        )

        # --------------------------------------------------------------------
        # WAIT TIME SCORE
        # --------------------------------------------------------------------

        wait_time = current.get(
            "wait_time_minutes"
        )

        if wait_time is None:

            wait_penalty = 5

        else:

            wait_penalty = min(
                30,
                wait_time * 0.8
            )

        score -= wait_penalty

        breakdown["wait_penalty"] = round(
            wait_penalty,
            2
        )

        # --------------------------------------------------------------------
        # USER MAX WAIT PREFERENCE
        # --------------------------------------------------------------------

        preference_penalty = 0

        if (

            max_wait is not None

            and

            wait_time is not None

            and

            wait_time > max_wait

        ):

            preference_penalty = min(

                25,

                (
                    wait_time
                    - max_wait
                )
                * 2

            )

            score -= preference_penalty

        breakdown[
            "preference_penalty"
        ] = round(
            preference_penalty,
            2
        )

        # --------------------------------------------------------------------
        # CROWD TREND
        # --------------------------------------------------------------------

        trend_name = trend.get(
            "trend",
            "unknown"
        )

        trend_penalty = 0

        if trend_name == "increasing":

            trend_penalty = 12

        elif trend_name == "stable":

            trend_penalty = 3

        elif trend_name == "decreasing":

            trend_penalty = -5

        score -= trend_penalty

        breakdown[
            "trend_penalty"
        ] = trend_penalty

        # --------------------------------------------------------------------
        # FUTURE FORECAST
        # --------------------------------------------------------------------

        future_penalty = 0

        in_one_hour = forecast.get(
            "in_1_hour"
        )

        now_forecast = forecast.get(
            "now"
        )

        if (

            now_forecast

            and

            in_one_hour

        ):

            current_prediction = (
                now_forecast.get(
                    "crowd_level"
                )
            )

            future_prediction = (
                in_one_hour.get(
                    "crowd_level"
                )
            )

            if (

                current_prediction is not None

                and

                future_prediction is not None

            ):

                change = (

                    future_prediction

                    -

                    current_prediction

                )

                if change > 0:

                    future_penalty = min(
                        15,
                        change * 10
                    )

                    score -= future_penalty

                elif change < 0:

                    future_penalty = max(
                        -8,
                        change * 5
                    )

                    score -= future_penalty

        breakdown[
            "future_crowd_penalty"
        ] = round(
            future_penalty,
            2
        )

        # --------------------------------------------------------------------
        # ANOMALY PENALTY
        # --------------------------------------------------------------------

        anomaly_penalty = 0

        if anomaly.get(
            "anomaly_detected",
            False
        ):

            anomaly_score = anomaly.get(
                "anomaly_score",
                0
            )

            anomaly_penalty = (
                anomaly_score * 25
            )

            score -= anomaly_penalty

        breakdown[
            "anomaly_penalty"
        ] = round(
            anomaly_penalty,
            2
        )

        # --------------------------------------------------------------------
        # PREFERRED LOCATION BONUS
        # --------------------------------------------------------------------

        preference_bonus = 0

        if (

            preferred_location_id

            and

            str(location_id)
            == str(preferred_location_id)

        ):

            preference_bonus = 5

            score += preference_bonus

        breakdown[
            "preference_bonus"
        ] = preference_bonus

        # --------------------------------------------------------------------
        # DATA CONFIDENCE
        # --------------------------------------------------------------------

        confidence = current.get(
            "confidence",
            0
        )

        confidence_bonus = (
            confidence * 5
        )

        score += confidence_bonus

        breakdown[
            "confidence_bonus"
        ] = round(
            confidence_bonus,
            2
        )

        # --------------------------------------------------------------------
        # FINAL SCORE LIMIT
        # --------------------------------------------------------------------

        score = max(
            0,
            min(100, score)
        )

        return {

            "score":
            round(score, 2),

            "breakdown":
            breakdown

        }

    # ========================================================================
    # HUMAN EXPLANATION ENGINE
    # ========================================================================

    def _generate_explanation(

        self,

        current,

        trend,

        anomaly,

        scoring

    ):

        score = scoring["score"]

        crowd_level = current.get(
            "crowd_level"
        )

        wait_time = current.get(
            "wait_time_minutes"
        )

        trend_name = trend.get(
            "trend",
            "unknown"
        )

        anomaly_detected = anomaly.get(
            "anomaly_detected",
            False
        )

        # --------------------------------------------------------------------
        # BEST CHOICE
        # --------------------------------------------------------------------

        if score >= 80:

            decision = "excellent"

            message = (
                "This is currently one of the "
                "best choices available."
            )

        elif score >= 65:

            decision = "recommended"

            message = (
                "This location currently has "
                "good overall conditions."
            )

        elif score >= 45:

            decision = "consider"

            message = (
                "Conditions are acceptable, but "
                "there may be better alternatives."
            )

        else:

            decision = "avoid"

            message = (
                "Current conditions are not ideal. "
                "Consider another location."
            )

        reasons = []

        # --------------------------------------------------------------------
        # CROWD REASON
        # --------------------------------------------------------------------

        if crowd_level is not None:

            if crowd_level <= 2:

                reasons.append(
                    "low crowd level"
                )

            elif crowd_level >= 4:

                reasons.append(
                    "high crowd level"
                )

        # --------------------------------------------------------------------
        # WAIT REASON
        # --------------------------------------------------------------------

        if wait_time is not None:

            if wait_time <= 10:

                reasons.append(
                    "short waiting time"
                )

            elif wait_time >= 30:

                reasons.append(
                    "long expected wait"
                )

        # --------------------------------------------------------------------
        # TREND REASON
        # --------------------------------------------------------------------

        if trend_name == "increasing":

            reasons.append(
                "crowds are increasing"
            )

        elif trend_name == "decreasing":

            reasons.append(
                "crowds are decreasing"
            )

        # --------------------------------------------------------------------
        # ANOMALY REASON
        # --------------------------------------------------------------------

        if anomaly_detected:

            reasons.append(
                "unusual crowd activity detected"
            )

        return {

            "decision":
            decision,

            "message":
            message,

            "reasons":
            reasons,

            "smart_score":
            score

        }
