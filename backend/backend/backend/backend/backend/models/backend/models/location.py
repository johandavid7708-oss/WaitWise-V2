import uuid
import math

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session

from .base import Base


class Location(Base):

    __tablename__ = "locations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name = Column(
        String(255),
        nullable=False,
        index=True
    )

    description = Column(
        Text,
        nullable=True
    )

    category = Column(
        String(100),
        nullable=False,
        index=True
    )

    latitude = Column(
        Float,
        nullable=False
    )

    longitude = Column(
        Float,
        nullable=False
    )

    capacity = Column(
        Integer,
        nullable=True
    )

    typical_peak_start = Column(
        Integer,
        nullable=True
    )

    typical_peak_end = Column(
        Integer,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
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

    # Relationships

    crowd_reports = relationship(
        "CrowdReport",
        back_populates="location",
        cascade="all, delete-orphan"
    )

    predictions = relationship(
        "Prediction",
        back_populates="location",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------
    # Convert location to API-friendly dictionary
    # ------------------------------------------------------------------

    def to_dict(
        self,
        include_current_crowd: bool = False,
        session: Session = None
    ):

        data = {

            "id": str(self.id),

            "name": self.name,

            "description": self.description,

            "category": self.category,

            "latitude": self.latitude,

            "longitude": self.longitude,

            "capacity": self.capacity,

            "typical_peak_start": self.typical_peak_start,

            "typical_peak_end": self.typical_peak_end,

            "is_active": self.is_active,

            "created_at": self.created_at.isoformat()
            if self.created_at else None

        }

        if include_current_crowd and session:

            current_crowd = self.get_current_crowd(session)

            data["current_crowd"] = current_crowd

        return data

    # ------------------------------------------------------------------
    # Get latest verified crowd intelligence
    # ------------------------------------------------------------------

    def get_current_crowd(self, session: Session):

        from .crowd_report import CrowdReport

        latest_report = (

            session.query(CrowdReport)

            .filter(
                CrowdReport.location_id == self.id,
                CrowdReport.is_verified == True
            )

            .order_by(
                CrowdReport.created_at.desc()
            )

            .first()

        )

        if not latest_report:

            return {

                "crowd_level": None,

                "wait_time_minutes": None,

                "confidence": 0.0,

                "updated_at": None,

                "status": "unknown"

            }

        return {

            "crowd_level": latest_report.crowd_level,

            "wait_time_minutes":
            latest_report.wait_time_minutes,

            "confidence":
            latest_report.confidence,

            "updated_at":
            latest_report.created_at.isoformat(),

            "status": "live"

        }

    # ------------------------------------------------------------------
    # Calculate distance between two locations
    # Uses Haversine Formula
    # ------------------------------------------------------------------

    def distance_to(self, other_location):

        earth_radius_km = 6371.0

        lat1 = math.radians(self.latitude)
        lon1 = math.radians(self.longitude)

        lat2 = math.radians(other_location.latitude)
        lon2 = math.radians(other_location.longitude)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        a = (

            math.sin(delta_lat / 2) ** 2

            +

            math.cos(lat1)
            * math.cos(lat2)

            * math.sin(delta_lon / 2) ** 2

        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

        distance = earth_radius_km * c

        return round(distance, 2)

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self):

        return (
            f"<Location "
            f"id={self.id} "
            f"name='{self.name}' "
            f"category='{self.category}'>"
        )
