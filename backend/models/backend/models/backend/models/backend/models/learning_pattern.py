import uuid

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class LearningPattern(Base):

    __tablename__ = "learning_patterns"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # ------------------------------------------------------------------------
    # Location this pattern belongs to
    # ------------------------------------------------------------------------

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "locations.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # ------------------------------------------------------------------------
    # Pattern Classification
    # ------------------------------------------------------------------------

    pattern_type = Column(
        String(100),
        nullable=False,
        index=True
    )

    pattern_name = Column(
        String(255),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    # ------------------------------------------------------------------------
    # Pattern Data
    #
    # Stored as JSON text initially so the system can evolve without
    # requiring constant database schema changes.
    # ------------------------------------------------------------------------

    pattern_data = Column(
        Text,
        nullable=True
    )

    # ------------------------------------------------------------------------
    # Intelligence Scores
    # ------------------------------------------------------------------------

    confidence_score = Column(
        Float,
        default=0.5,
        nullable=False
    )

    importance_score = Column(
        Float,
        default=0.5,
        nullable=False
    )

    occurrence_count = Column(
        Integer,
        default=1,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Pattern Status
    # ------------------------------------------------------------------------

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )

    is_verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------------

    first_detected_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    last_detected_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------------

    location = relationship(
        "Location"
    )

    # ------------------------------------------------------------------------
    # Pattern strengthening
    #
    # Every time the AI detects the same pattern again,
    # the pattern becomes stronger.
    # ------------------------------------------------------------------------

    def reinforce(
        self,
        confidence_increase=0.05
    ):

        self.occurrence_count += 1

        self.confidence_score = min(
            1.0,
            self.confidence_score + confidence_increase
        )

        self.last_detected_at = datetime.utcnow()

    # ------------------------------------------------------------------------
    # Pattern weakening
    #
    # If a previously detected pattern stops appearing,
    # its confidence can gradually decrease.
    # ------------------------------------------------------------------------

    def weaken(
        self,
        confidence_decrease=0.05
    ):

        self.confidence_score = max(
            0.0,
            self.confidence_score - confidence_decrease
        )

        if self.confidence_score < 0.2:
            self.is_active = False

    # ------------------------------------------------------------------------
    # API-friendly representation
    # ------------------------------------------------------------------------

    def to_dict(self):

        return {

            "id": str(self.id),

            "location_id": str(self.location_id),

            "pattern_type": self.pattern_type,

            "pattern_name": self.pattern_name,

            "description": self.description,

            "pattern_data": self.pattern_data,

            "confidence_score":
            round(self.confidence_score, 3),

            "importance_score":
            round(self.importance_score, 3),

            "occurrence_count":
            self.occurrence_count,

            "is_active":
            self.is_active,

            "is_verified":
            self.is_verified,

            "first_detected_at":
            (
                self.first_detected_at.isoformat()
                if self.first_detected_at else None
            ),

            "last_detected_at":
            (
                self.last_detected_at.isoformat()
                if self.last_detected_at else None
            )

        }

    # ------------------------------------------------------------------------
    # Human-readable representation
    # ------------------------------------------------------------------------

    def __repr__(self):

        return (

            f"<LearningPattern "

            f"id={self.id} "

            f"type='{self.pattern_type}' "

            f"confidence={self.confidence_score} "

            f"occurrences={self.occurrence_count}>"

        )
