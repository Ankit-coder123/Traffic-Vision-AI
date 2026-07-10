from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ---------- User / Auth ----------

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "operator"   # 'admin' or 'operator'


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True   # allows returning SQLAlchemy objects directly


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Traffic Zones ----------

class TrafficZoneCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    road_type: Optional[str] = "arterial"


class TrafficZoneOut(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    road_type: str

    class Config:
        from_attributes = True


# ---------- Traffic Data ----------

class TrafficDataOut(BaseModel):
    id: int
    zone_id: int
    vehicle_count: int
    avg_speed_kmph: float
    congestion_level: str
    recorded_at: datetime

    class Config:
        from_attributes = True


class TrafficDataCreate(BaseModel):
    zone_id: int
    vehicle_count: int
    avg_speed_kmph: float
    congestion_level: str
