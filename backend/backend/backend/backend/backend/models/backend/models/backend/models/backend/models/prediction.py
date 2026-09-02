import uuid

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Prediction(Base):

    __tablename__ = "predictions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # ------------------------------------------------------------------
    # Location being predicted
    # ------------------------------------------------------------------

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id"),
        nullable=False,
        index=True
    )

    # ------------------------------------------------------------------
    # AI Prediction Results
    # ------------------------------------------------------------------

    predicted_crowd_level = Column(
        Float,
        nullable=False
    )

    predicted_wait_time = Column(
        Integer,
        nullable=True
    )

    confidence_score = Column(
        Float,
        default=0.5,
        nullable=False
    )

    # ------------------------------------------------------------------
    # Prediction Configuration
    # ------------------------------------------------------------------

    prediction_horizon = Column(
        Integer,
        nullable=False
    )

    model_version = Column(
        String(100),
        default="1.0",
        nullable=False
    )

    # ------------------------------------------------------------------
    # Timing Intelligence
    # ------------------------------------------------------------------

    predicted_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    forecast_for = Column(
        DateTime,
        nullable=False,
        index=True
    )

    # ------------------------------------------------------------------
    # Accuracy / Learning Results
    # ------------------------------------------------------------------

    actual_crowd_level = Column(
        Float,
        nullable=True
    )

    actual_wait_time = Column(
        Integer,
        nullable=True
    )

    accuracy_score = Column(
        Float,
        nullable=True
    )

    is_evaluated = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    evaluated_at = Column(
        DateTime,
        nullable=True
    )

    # ------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------

    location = relationship(
        "Location",
        back_populates="predictions"
    )

    # ------------------------------------------------------------------
    # Convert prediction to API-friendly dictionary
    # ------------------------------------------------------------------

    def to_dict(self):

        return {

            "id": str(self.id),

            "location_id": str(self.location_id),

            "predicted_crowd_level":
            self.predicted_crowd_level,

            "predicted_wait_time":
            self.predicted_wait_time,

            "confidence_score":
            self.confidence_score,

            "prediction_horizon":
            self.prediction_horizon,

            "model_version":
            self.model_version,

            "predicted_at":
            self.predicted_at.isoformat()
            if self.predicted_at else None,

            "forecast_for":
            self.forecast_for.isoformat()
            if self.forecast_for else None,

            "actual_crowd_level":
            self.actual_crowd_level,

            "actual_wait_time":
            self.actual_wait_time,

            "accuracy_score":
            self.accuracy_score,

            "is_evaluated":
            self.is_evaluated,

            "evaluated_at":
            self.evaluated_at.isoformat()
            if self.evaluated_at else None

        }

    # ------------------------------------------------------------------
    # Evaluate prediction against actual data
    # ------------------------------------------------------------------

    def evaluate(
        self,
        actual_crowd_level,
        actual_wait_time=None
    ):

        self.actual_crowd_level = actual_crowd_level

        if actual_wait_time is not None:
            self.actual_wait_time = actual_wait_time

        crowd_error = abs(
            self.predicted_crowd_level
            - actual_crowd_level
        )

        # Maximum possible crowd error is 4
        crowd_accuracy = max(
            0,
            1 - (crowd_error / 4)
        )

        if (
            self.predicted_wait_time is not None
            and actual_wait_time is not None
        ):

            max_wait = max(
                self.predicted_wait_time,
                actual_wait_time,
                1
            )

            wait_error = abs(
                self.predicted_wait_time
                - actual_wait_time
            )

            wait_accuracy = max(
                0,
                1 - (wait_error / max_wait)
            )

            # Crowd prediction matters more
            # than waiting-time precision
            self.accuracy_score = (
                crowd_accuracy * 0.7
                + wait_accuracy * 0.3
            )

        else:

            self.accuracy_score = crowd_accuracy

        self.is_evaluated = True

        self.evaluated_at = datetime.utcnow()

        return self.accuracy_score

    # ------------------------------------------------------------------
    # Human-readable prediction
    # ------------------------------------------------------------------

    def get_crowd_level_text(self):

        level = self.predicted_crowd_level

        if level < 1.5:
            return "Empty"

        elif level < 2.5:
            return "Quiet"

        elif level < 3.5:
            return "Moderate"

        elif level < 4.5:
            return "Crowded"

        return "Very Crowded"

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self):

        return (

            f"<Prediction "

            f"id={self.id} "

            f"location_id={self.location_id} "

            f"crowd={self.predicted_crowd_level} "

            f"confidence={self.confidence_score}>"

        )
