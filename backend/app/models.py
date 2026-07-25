import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    user = "user"


class CongestionLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    severe = "severe"


class IncidentSeverity(str, enum.Enum):
    minor = "minor"
    moderate = "moderate"
    major = "major"


class IncidentType(str, enum.Enum):
    accident = "accident"
    road_closure = "road_closure"
    construction = "construction"
    hazard = "hazard"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.operator, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TrafficZone(Base):
    __tablename__ = "traffic_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)          # e.g. "MG Road Junction"
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    road_type = Column(String, default="arterial")  # highway | arterial | local
    created_at = Column(DateTime, default=datetime.utcnow)

    traffic_data = relationship("TrafficData", back_populates="zone")


class TrafficData(Base):
    __tablename__ = "traffic_data"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("traffic_zones.id"), nullable=False)
    vehicle_count = Column(Integer, nullable=False)
    avg_speed_kmph = Column(Float, nullable=False)
    congestion_level = Column(Enum(CongestionLevel), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    zone = relationship("TrafficZone", back_populates="traffic_data")


class TrafficPrediction(Base):
    __tablename__ = "traffic_predictions"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("traffic_zones.id"), nullable=True)
    vehicle_count = Column(Integer, nullable=False)
    avg_speed_kmph = Column(Float, nullable=False)
    road_occupancy_pct = Column(Float, nullable=False)
    weather_condition = Column(String, default="Clear", nullable=False)
    predicted_congestion = Column(String, nullable=False)   # 'low' | 'medium' | 'high'
    confidence = Column(Float, nullable=False)                # model's probability for the predicted class
    predicted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class IncidentReport(Base):
    """Manually reported real-world incidents (accidents, closures, etc.),
    reportable only by operators/admins -- feeds the alerts/notifications
    work planned for Milestone 3, and gives operator accounts a genuinely
    distinct capability from regular public user accounts."""
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("traffic_zones.id"), nullable=False)
    incident_type = Column(Enum(IncidentType), nullable=False)
    severity = Column(Enum(IncidentSeverity), nullable=False)
    description = Column(String, nullable=True)
    reported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_resolved = Column(Integer, default=0)  # 0/1 boolean flag (portable across SQLite/Postgres)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    zone = relationship("TrafficZone")


class SavedRoute(Base):
    """A user's personally saved origin/destination pair for quick re-use
    on the Routes page -- available to every role, but framed as primarily
    a convenience feature for regular public users."""
    __tablename__ = "saved_routes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    label = Column(String, nullable=False)  # e.g. "Home to Office"
    origin_zone_id = Column(Integer, ForeignKey("traffic_zones.id"), nullable=False)
    destination_zone_id = Column(Integer, ForeignKey("traffic_zones.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    origin_zone = relationship("TrafficZone", foreign_keys=[origin_zone_id])
    destination_zone = relationship("TrafficZone", foreign_keys=[destination_zone_id])

