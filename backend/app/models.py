import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"


class CongestionLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    severe = "severe"


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
