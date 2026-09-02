import uuid

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Alert(Base):

    __tablename__ = "alerts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # ------------------------------------------------------------------------
    # User receiving the alert
    # ------------------------------------------------------------------------

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=True,
        index=True
    )

    # ------------------------------------------------------------------------
    # Location related to the alert
    # ------------------------------------------------------------------------

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "locations.id",
            ondelete="CASCADE"
        ),
        nullable=True,
        index=True
    )

    # ------------------------------------------------------------------------
    # Alert Classification
    # ------------------------------------------------------------------------

    alert_type = Column(
        String(100),
        nullable=False,
        index=True
    )

    priority = Column(
        String(50),
        default="normal",
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Alert Content
    # ------------------------------------------------------------------------

    title = Column(
        String(255),
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Delivery Intelligence
    # ------------------------------------------------------------------------

    channel = Column(
        String(50),
        default="in_app",
        nullable=False
    )

    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    is_sent = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Alert Timing
    # ------------------------------------------------------------------------

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    scheduled_for = Column(
        DateTime,
        nullable=True,
        index=True
    )

    sent_at = Column(
        DateTime,
        nullable=True
    )

    expires_at = Column(
        DateTime,
        nullable=True,
        index=True
    )

    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    user = relationship(
        "User"
    )

    location = relationship(
        "Location"
    )

    # ------------------------------------------------------------------------
    # API-friendly representation
    # ------------------------------------------------------------------------

    def to_dict(self):

        return {

            "id": str(self.id),

            "user_id": (
                str(self.user_id)
                if self.user_id else None
            ),

            "location_id": (
                str(self.location_id)
                if self.location_id else None
            ),

            "alert_type": self.alert_type,

            "priority": self.priority,

            "title": self.title,

            "message": self.message,

            "channel": self.channel,

            "is_read": self.is_read,

            "is_sent": self.is_sent,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),

            "scheduled_for": (
                self.scheduled_for.isoformat()
                if self.scheduled_for else None
            ),

            "sent_at": (
                self.sent_at.isoformat()
                if self.sent_at else None
            ),

            "expires_at": (
                self.expires_at.isoformat()
                if self.expires_at else None
            )

        }

    # ------------------------------------------------------------------------
    # Alert State Management
    # ------------------------------------------------------------------------

    def mark_as_read(self):

        self.is_read = True

    def mark_as_sent(self):

        self.is_sent = True

        self.sent_at = datetime.utcnow()

    # ------------------------------------------------------------------------
    # Check whether alert has expired
    # ------------------------------------------------------------------------

    def is_expired(self):

        if not self.expires_at:
            return False

        return datetime.utcnow() > self.expires_at

    # ------------------------------------------------------------------------
    # Check whether alert should be sent
    # ------------------------------------------------------------------------

    def should_send(self):

        # Don't send expired alerts

        if self.is_expired():
            return False

        # Don't send twice

        if self.is_sent:
            return False

        # Send immediately if no schedule exists

        if not self.scheduled_for:
            return True

        # Send when scheduled time arrives

        return datetime.utcnow() >= self.scheduled_for

    # ------------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------------

    def __repr__(self):

        return (

            f"<Alert "

            f"id={self.id} "

            f"type='{self.alert_type}' "

            f"priority='{self.priority}' "

            f"sent={self.is_sent}>"

        )
