from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models.prediction import Prediction
from models.crowd_report import CrowdReport


class PredictionLearner:
    """
    Tracks prediction accuracy using later verified crowd reports.

    Learning loop:

        Prediction created
                ↓
        Time passes
                ↓
        Verified real-world report arrives
                ↓
        Compare prediction vs reality
                ↓
        Store accuracy metrics
                ↓
        Future ML training uses growing verified history
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # FIND VERIFIED REALITY
    # =========================================================================

    def find_actual_report(
        self,
        location_id: str,
        prediction_time: datetime,
        tolerance_minutes: int = 60
    ) -> Optional[CrowdReport]:
        """
        Find the verified crowd report closest to the time
        that a prediction was made for.
        """

        reports = (
            self.db.query(CrowdReport)
            .filter(
                CrowdReport.location_id == location_id,
                CrowdReport.is_verified.is_(True),
                CrowdReport.created_at.isnot(None)
            )
            .all()
        )

        if not reports:
            return None

        closest_report = None
        closest_difference = None

        for report in reports:

            difference = abs(
                (
                    report.created_at
                    - prediction_time
                ).total_seconds()
                / 60
            )

            if difference <= tolerance_minutes:

                if (
                    closest_difference is None
                    or difference < closest_difference
                ):
                    closest_difference = difference
                    closest_report = report

        return closest_report

    # =========================================================================
    # CALCULATE ACCURACY
    # =========================================================================

    @staticmethod
    def calculate_accuracy(
        predicted_value: float,
        actual_value: float
    ) -> float:
        """
        Returns accuracy from 0 to 100.

        Example:
            predicted = 80
            actual = 80
            accuracy = 100

            predicted = 80
            actual = 60
            accuracy = 80
        """

        if predicted_value is None or actual_value is None:
            return 0.0

        error = abs(
            predicted_value
            - actual_value
        )

        accuracy = 100 - error

        return max(
            0.0,
            min(100.0, accuracy)
        )

    # =========================================================================
    # VERIFY A SINGLE PREDICTION
    # =========================================================================

    def evaluate_prediction(
        self,
        prediction: Prediction,
        tolerance_minutes: int = 60
    ) -> dict:

        # The model can only learn after the predicted time
        # has actually occurred.

        if prediction.predicted_for > datetime.utcnow():

            return {
                "evaluated": False,
                "reason": "Prediction time has not occurred yet"
            }

        actual_report = self.find_actual_report(
            location_id=str(prediction.location_id),
            prediction_time=prediction.predicted_for,
            tolerance_minutes=tolerance_minutes
        )

        if actual_report is None:

            return {
                "evaluated": False,
                "reason": (
                    "No verified real-world report available"
                )
            }

        # ---------------------------------------------------------------------
        # CROWD ACCURACY
        # ---------------------------------------------------------------------

        crowd_accuracy = None

        if (
            prediction.predicted_crowd_level is not None
            and actual_report.crowd_level is not None
        ):

            crowd_accuracy = self.calculate_accuracy(
                prediction.predicted_crowd_level,
                actual_report.crowd_level
            )

        # ---------------------------------------------------------------------
        # WAIT TIME ACCURACY
        # ---------------------------------------------------------------------

        wait_accuracy = None

        if (
            prediction.predicted_wait_minutes is not None
            and actual_report.estimated_wait_minutes is not None
        ):

            predicted_wait = (
                prediction.predicted_wait_minutes
            )

            actual_wait = (
                actual_report.estimated_wait_minutes
            )

            error = abs(
                predicted_wait
                - actual_wait
            )

            # Wait-time error is normalized more gently because
            # wait times can exceed 100 minutes.

            wait_accuracy = max(
                0.0,
                100 - (error * 2)
            )

        # ---------------------------------------------------------------------
        # OVERALL ACCURACY
        # ---------------------------------------------------------------------

        accuracy_values = [
            value
            for value in [
                crowd_accuracy,
                wait_accuracy
            ]
            if value is not None
        ]

        if not accuracy_values:

            return {
                "evaluated": False,
                "reason": (
                    "Prediction and actual report contain "
                    "no comparable data"
                )
            }

        overall_accuracy = (
            sum(accuracy_values)
            / len(accuracy_values)
        )

        return {
            "evaluated": True,

            "prediction_id": str(prediction.id),

            "actual_report_id": str(
                actual_report.id
            ),

            "crowd_accuracy": (
                round(crowd_accuracy, 2)
                if crowd_accuracy is not None
                else None
            ),

            "wait_accuracy": (
                round(wait_accuracy, 2)
                if wait_accuracy is not None
                else None
            ),

            "overall_accuracy": round(
                overall_accuracy,
                2
            )
        }

    # =========================================================================
    # EVALUATE LOCATION PREDICTIONS
    # =========================================================================

    def evaluate_location_predictions(
        self,
        location_id: str,
        limit: int = 100
    ) -> dict:
        """
        Evaluate historical predictions for one location.
        """

        predictions = (
            self.db.query(Prediction)
            .filter(
                Prediction.location_id == location_id,
                Prediction.predicted_for <= datetime.utcnow()
            )
            .order_by(
                Prediction.predicted_for.desc()
            )
            .limit(limit)
            .all()
        )

        results = []

        for prediction in predictions:

            evaluation = self.evaluate_prediction(
                prediction
            )

            if evaluation.get("evaluated"):
                results.append(evaluation)

        if not results:

            return {
                "location_id": location_id,
                "evaluated_predictions": 0,
                "average_accuracy": None,
                "results": []
            }

        average_accuracy = (
            sum(
                result["overall_accuracy"]
                for result in results
            )
            / len(results)
        )

        return {
            "location_id": location_id,

            "evaluated_predictions": len(results),

            "average_accuracy": round(
                average_accuracy,
                2
            ),

            "results": results
        }

    # =========================================================================
    # SYSTEM-WIDE LEARNING ANALYTICS
    # =========================================================================

    def get_learning_statistics(
        self,
        limit: int = 500
    ) -> dict:

        predictions = (
            self.db.query(Prediction)
            .filter(
                Prediction.predicted_for <= datetime.utcnow()
            )
            .order_by(
                Prediction.predicted_for.desc()
            )
            .limit(limit)
            .all()
        )

        evaluations = []

        for prediction in predictions:

            result = self.evaluate_prediction(
                prediction
            )

            if result.get("evaluated"):
                evaluations.append(result)

        if not evaluations:

            return {
                "evaluated_predictions": 0,
                "average_accuracy": None,
                "learning_status": "collecting_data"
            }

        average_accuracy = (
            sum(
                item["overall_accuracy"]
                for item in evaluations
            )
            / len(evaluations)
        )

        if average_accuracy >= 85:
            learning_status = "performing_well"

        elif average_accuracy >= 70:
            learning_status = "improving"

        else:
            learning_status = "needs_more_data"

        return {
            "evaluated_predictions": len(evaluations),

            "average_accuracy": round(
                average_accuracy,
                2
            ),

            "learning_status": learning_status
        }
