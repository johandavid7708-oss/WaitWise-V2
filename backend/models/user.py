import uuid

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


# ============================================================================
# USER
# ============================================================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    username = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    hashed_password = Column(
        String(255),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    is_verified = Column(
        Boolean,
        default=False,
        nullable=False
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
    # Relationships
    # ------------------------------------------------------------------------

    preferences = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------------
    # API-friendly representation
    # ------------------------------------------------------------------------

    def to_dict(self):

        return {

            "id": str(self.id),

            "username": self.username,

            "email": self.email,

            "is_active": self.is_active,

            "is_verified": self.is_verified,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )

        }

    def __repr__(self):

        return (
            f"<User "
            f"id={self.id} "
            f"username='{self.username}'>"
        )


# ============================================================================
# USER PREFERENCES
# ============================================================================

class UserPreferences(Base):

    __tablename__ = "user_preferences"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        unique=True,
        index=True
    )

    # ------------------------------------------------------------------------
    # Waiting preferences
    # ------------------------------------------------------------------------

    max_wait_minutes = Column(
        Float,
        default=20.0,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Travel preferences
    # ------------------------------------------------------------------------

    max_distance_km = Column(
        Float,
        default=5.0,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Preferred location categories
    #
    # Stored as simple comma-separated text for now.
    # Example:
    # "restaurant,cafe,mall"
    #
    # Can later be migrated to JSONB/PostgreSQL arrays.
    # ------------------------------------------------------------------------

    preferred_categories = Column(
        Text,
        nullable=True
    )

    # ------------------------------------------------------------------------
    # Crowd tolerance
    #
    # 1 = prefers very quiet
    # 5 = comfortable with very crowded places
    # ------------------------------------------------------------------------

    crowd_tolerance = Column(
        Float,
        default=3.0,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Smart recommendation preferences
    # ------------------------------------------------------------------------

    prefer_shortest_travel = Column(
        Boolean,
        default=False,
        nullable=False
    )

    prefer_shortest_wait = Column(
        Boolean,
        default=True,
        nullable=False
    )

    enable_smart_alerts = Column(
        Boolean,
        default=True,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------------

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

    user = relationship(
        "User",
        back_populates="preferences"
    )

    # ------------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------------

    def get_preferred_categories(self):

        if not self.preferred_categories:
            return []

        return [

            category.strip()

            for category in self.preferred_categories.split(",")

            if category.strip()

        ]

    def set_preferred_categories(self, categories):

        if not categories:

            self.preferred_categories = None
            return

        self.preferred_categories = ",".join(
            str(category).strip()
            for category in categories
            if str(category).strip()
        )

    # ------------------------------------------------------------------------
    # API-friendly representation
    # ------------------------------------------------------------------------

    def to_dict(self):

        return {

            "id": str(self.id),

            "user_id": str(self.user_id),

            "max_wait_minutes": self.max_wait_minutes,

            "max_distance_km": self.max_distance_km,

            "preferred_categories":
            self.get_preferred_categories(),

            "crowd_tolerance":
            self.crowd_tolerance,

            "prefer_shortest_travel":
            self.prefer_shortest_travel,

            "prefer_shortest_wait":
            self.prefer_shortest_wait,

            "enable_smart_alerts":
            self.enable_smart_alerts

        }

    def __repr__(self):

        return (
            f"<UserPreferences "
            f"user_id={self.user_id}>"
        )
