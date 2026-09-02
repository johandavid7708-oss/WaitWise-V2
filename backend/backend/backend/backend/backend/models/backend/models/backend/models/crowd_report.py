import uuid

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class CrowdReport(Base):

    __tablename__ = "crowd_reports"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # ------------------------------------------------------------------
    # Location this report belongs to
    # ------------------------------------------------------------------

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id"),
        nullable=False,
        index=True
    )

    # ------------------------------------------------------------------
    # Crowd intelligence
    # Crowd level:
    # 1 = Empty
    # 2 = Quiet
    # 3 = Moderate
    # 4 = Crowded
    # 5 = Very Crowded
    # ------------------------------------------------------------------

    crowd_level = Column(
        Integer,
        nullable=False
    )

    wait_time_minutes = Column(
        Integer,
        nullable=True
    )

    comment = Column(
        Text,
        nullable=True
    )

    # How confident the user was in their report
    confidence = Column(
        Float,
        default=0.5,
        nullable=False
    )

    # ------------------------------------------------------------------
    # Reliability and AI learning
    # ------------------------------------------------------------------

    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    accuracy_score = Column(
        Float,
        default=0.5,
        nullable=False
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    location = relationship(
        "Location",
        back_populates="crowd_reports"
    )

    # ------------------------------------------------------------------
    # API-friendly dictionary
    # ------------------------------------------------------------------

    def to_dict(self):

        return {

            "id": str(self.id),

            "location_id": str(self.location_id),

            "crowd_level": self.crowd_level,

            "crowd_level_text":
            self.get_crowd_level_text(),

            "wait_time_minutes":
            self.wait_time_minutes,

            "comment":
            self.comment,

            "confidence":
            self.confidence,

            "is_verified":
            self.is_verified,

            "accuracy_score":
            self.accuracy_score,

            "created_at":
            self.created_at.isoformat()
            if self.created_at else None

        }

    # ------------------------------------------------------------------
    # Convert numeric crowd level into readable intelligence
    # ------------------------------------------------------------------

    def get_crowd_level_text(self):

        levels = {

            1: "Empty",

            2: "Quiet",

            3: "Moderate",

            4: "Crowded",

            5: "Very Crowded"

        }

        return levels.get(
            self.crowd_level,
            "Unknown"
        )

    # ------------------------------------------------------------------
    # Validate report values
    # ------------------------------------------------------------------

    def is_valid(self):

        if not 1 <= self.crowd_level <= 5:
            return False

        if self.confidence < 0 or self.confidence > 1:
            return False

        if (
            self.wait_time_minutes is not None
            and self.wait_time_minutes < 0
        ):
            return False

        return True

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self):

        return (

            f"<CrowdReport "

            f"id={self.id} "

            f"location_id={self.location_id} "

            f"crowd_level={self.crowd_level} "

            f"verified={self.is_verified}>"

        )
