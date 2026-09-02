from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.crowd_report import CrowdReport
from models.prediction import Prediction
from models.learning_pattern import LearningPattern


class CrowdLearner:

    """
    WaitWise Self-Learning Intelligence System.

    Responsibilities:

    - Evaluate prediction accuracy
    - Compare predictions with real outcomes
    - Discover recurring crowd patterns
    - Reinforce existing patterns
    - Weaken unreliable patterns
    - Generate learning insights
    """

    def __init__(self, session: Session):

        self.session = session

    # ========================================================================
    # MAIN LEARNING CYCLE
    # ========================================================================

    def run_learning_cycle(
        self,
        location_id
    ):

        prediction_results = (
            self.evaluate_predictions(
                location_id
            )
        )

        pattern_results = (
            self.detect_patterns(
                location_id
            )
        )

        return {

            "location_id":
            str(location_id),

            "predictions_evaluated":
            prediction_results["evaluated"],

            "average_prediction_error":
            prediction_results["average_error"],

            "patterns_detected":
            pattern_results["patterns_detected"],

            "patterns_reinforced":
            pattern_results["patterns_reinforced"],

            "learning_completed_at":
            datetime.utcnow().isoformat()

        }

    # ========================================================================
    # EVALUATE PREDICTION ACCURACY
    # ========================================================================

    def evaluate_predictions(
        self,
        location_id
    ):

        predictions = (

            self.session
            .query(Prediction)

            .filter(
                Prediction.location_id
                == location_id
            )

            .order_by(
                Prediction.created_at.asc()
            )

            .all()

        )

        evaluated = 0

        total_error = 0.0

        for prediction in predictions:

            # Skip predictions that have
            # already been evaluated

            if getattr(
                prediction,
                "actual_crowd_level",
                None
            ) is not None:

                continue

            forecast_time = getattr(
                prediction,
                "forecast_for",
                None
            )

            if forecast_time is None:

                continue

            # Don't evaluate predictions
            # about the future

            if forecast_time > datetime.utcnow():

                continue

            actual_report = (
                self._find_actual_report(
                    location_id,
                    forecast_time
                )
            )

            if actual_report is None:

                continue

            predicted_value = (
                self._get_predicted_crowd(
                    prediction
                )
            )

            if predicted_value is None:

                continue

            actual_value = (
                actual_report.crowd_level
            )

            error = abs(
                predicted_value
                - actual_value
            )

            # Store learning outcome

            if hasattr(
                prediction,
                "actual_crowd_level"
            ):

                prediction.actual_crowd_level = (
                    actual_value
                )

            if hasattr(
                prediction,
                "prediction_error"
            ):

                prediction.prediction_error = (
                    error
                )

            if hasattr(
                prediction,
                "accuracy_score"
            ):

                prediction.accuracy_score = (
                    max(
                        0.0,
                        1.0 - (error / 4.0)
                    )
                )

            evaluated += 1

            total_error += error

        self.session.commit()

        average_error = (

            total_error / evaluated

            if evaluated > 0

            else None

        )

        return {

            "evaluated":
            evaluated,

            "average_error":
            (
                round(average_error, 3)

                if average_error
                is not None

                else None
            )

        }

    # ========================================================================
    # FIND REAL CROWD OUTCOME
    # ========================================================================

    def _find_actual_report(
        self,
        location_id,
        forecast_time
    ):

        tolerance = timedelta(
            minutes=30
        )

        start_time = (
            forecast_time - tolerance
        )

        end_time = (
            forecast_time + tolerance
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
                >= start_time,

                CrowdReport.created_at
                <= end_time

            )

            .order_by(
                CrowdReport.created_at.asc()
            )

            .all()

        )

        if not reports:

            return None

        # If multiple reports exist,
        # use the one closest to the
        # prediction's forecast time.

        return min(

            reports,

            key=lambda report:

            abs(
                report.created_at
                - forecast_time
            )

        )

    # ========================================================================
    # GET PREDICTED CROWD VALUE
    # ========================================================================

    def _get_predicted_crowd(
        self,
        prediction
    ):

        possible_fields = [

            "predicted_crowd_level",

            "crowd_level",

            "predicted_value"

        ]

        for field in possible_fields:

            if hasattr(
                prediction,
                field
            ):

                value = getattr(
                    prediction,
                    field
                )

                if value is not None:

                    return float(value)

        return None

    # ========================================================================
    # DETECT RECURRING PATTERNS
    # ========================================================================

    def detect_patterns(
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

        if len(reports) < 5:

            return {

                "patterns_detected": 0,

                "patterns_reinforced": 0

            }

        detected = 0

        reinforced = 0

        # --------------------------------------------------------------------
        # GROUP REPORTS BY WEEKDAY + HOUR
        # --------------------------------------------------------------------

        groups = {}

        for report in reports:

            timestamp = (
                report.created_at
            )

            key = (

                timestamp.weekday(),

                timestamp.hour

            )

            if key not in groups:

                groups[key] = []

            groups[key].append(
                report.crowd_level
            )

        # --------------------------------------------------------------------
        # ANALYZE GROUPS
        # --------------------------------------------------------------------

        for key, values in groups.items():

            # Require repeated observations

            if len(values) < 3:

                continue

            average_crowd = (

                sum(values)
                / len(values)

            )

            weekday = key[0]

            hour = key[1]

            # Only store meaningful
            # crowd patterns

            if average_crowd < 3.0:

                continue

            pattern_name = (

                f"weekday_{weekday}_hour_{hour}"

            )

            confidence = min(

                0.95,

                len(values) / 20

            )

            result = (
                self._create_or_reinforce_pattern(

                    location_id=

                    location_id,

                    pattern_type=

                    "time_based_crowd_pattern",

                    pattern_name=

                    pattern_name,

                    average_crowd=

                    average_crowd,

                    occurrence_count=

                    len(values),

                    confidence=

                    confidence,

                    weekday=

                    weekday,

                    hour=

                    hour

                )
            )

            detected += 1

            if result == "reinforced":

                reinforced += 1

        self.session.commit()

        return {

            "patterns_detected":
            detected,

            "patterns_reinforced":
            reinforced

        }

    # ========================================================================
    # CREATE OR REINFORCE PATTERN
    # ========================================================================

    def _create_or_reinforce_pattern(

        self,

        location_id,

        pattern_type,

        pattern_name,

        average_crowd,

        occurrence_count,

        confidence,

        weekday,

        hour

    ):

        existing_pattern = (

            self.session
            .query(LearningPattern)

            .filter(

                LearningPattern.location_id
                == location_id,

                LearningPattern.pattern_type
                == pattern_type,

                LearningPattern.pattern_name
                == pattern_name

            )

            .first()

        )

        pattern_data = (

            f'{{'

            f'"weekday": {weekday}, '

            f'"hour": {hour}, '

            f'"average_crowd": '

            f'{round(average_crowd, 2)}'

            f'}}'

        )

        # --------------------------------------------------------------------
        # Reinforce existing pattern
        # --------------------------------------------------------------------

        if existing_pattern:

            existing_pattern.occurrence_count = (

                max(

                    existing_pattern.occurrence_count,

                    occurrence_count

                )

            )

            existing_pattern.confidence_score = min(

                0.99,

                max(

                    existing_pattern.confidence_score,

                    confidence

                )

                + 0.02

            )

            existing_pattern.pattern_data = (
                pattern_data
            )

            existing_pattern.last_detected_at = (
                datetime.utcnow()
            )

            existing_pattern.is_active = True

            return "reinforced"

        # --------------------------------------------------------------------
        # Create new learned pattern
        # --------------------------------------------------------------------

        new_pattern = LearningPattern(

            location_id=
            location_id,

            pattern_type=
            pattern_type,

            pattern_name=
            pattern_name,

            description=(

                f"Recurring crowd pattern "

                f"detected on weekday "

                f"{weekday} around "

                f"{hour}:00."

            ),

            pattern_data=
            pattern_data,

            confidence_score=
            confidence,

            importance_score=
            min(
                1.0,
                average_crowd / 5.0
            ),

            occurrence_count=
            occurrence_count,

            is_active=
            True

        )

        self.session.add(
            new_pattern
        )

        return "created"

    # ========================================================================
    # GET LEARNING INSIGHTS
    # ========================================================================

    def get_learning_insights(
        self,
        location_id
    ):

        patterns = (

            self.session
            .query(LearningPattern)

            .filter(

                LearningPattern.location_id
                == location_id,

                LearningPattern.is_active
                == True

            )

            .order_by(

                LearningPattern.confidence_score
                .desc()

            )

            .all()

        )

        return [

            pattern.to_dict()

            for pattern in patterns

        ]
