from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ---------- User / Auth ----------

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "user"   # 'operator' or 'user' -- 'admin' is never self-assignable via signup


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


# ---------- Congestion Prediction ----------

class CongestionPredictionRequest(BaseModel):
    origin_zone_id: Optional[int] = None
    destination_zone_id: Optional[int] = None
    vehicle_count: int
    avg_speed_kmph: float
    road_occupancy_pct: float
    weather_condition: Optional[str] = "Clear"   # 'Clear' | 'Fog' | 'Rain' | 'Snow'
    hour: Optional[int] = None          # 0-23; defaults to current server hour if omitted
    is_weekend: Optional[bool] = None    # defaults based on current server date if omitted


class CongestionPredictionResponse(BaseModel):
    predicted_congestion: str
    confidence: float
    probabilities: dict            # e.g. {"low": 0.1, "medium": 0.7, "high": 0.2}
    origin_zone_id: Optional[int] = None
    destination_zone_id: Optional[int] = None


class TrafficPredictionOut(BaseModel):
    id: int
    origin_zone_id: Optional[int]
    destination_zone_id: Optional[int]
    vehicle_count: int
    avg_speed_kmph: float
    road_occupancy_pct: float
    weather_condition: str
    predicted_congestion: str
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Route Optimization ----------

class RouteRequest(BaseModel):
    # Either pick existing zones (uses their stored lat/lng) or supply raw
    # coordinates directly -- zone_id takes priority if both are given.
    origin_zone_id: Optional[int] = None
    destination_zone_id: Optional[int] = None
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None


class RouteOption(BaseModel):
    distance_km: float
    base_duration_min: float          # raw OSRM estimate, no congestion factored in
    congestion_multiplier: float        # derived from current live traffic data
    estimated_duration_min: float        # base_duration_min * congestion_multiplier
    geometry: list                          # list of [lat, lng] points for map rendering
    is_recommended: bool = False


class RouteOptimizeResponse(BaseModel):
    origin: dict            # {"lat":..., "lng":...}
    destination: dict
    congestion_level_used: str   # what congestion level informed the multiplier
    routes: list[RouteOption]


# ---------- Incident Reports (operator/admin only) ----------

class IncidentReportCreate(BaseModel):
    zone_id: int
    incident_type: str   # accident | road_closure | construction | hazard | other
    severity: str          # minor | moderate | major
    description: Optional[str] = None


class IncidentReportOut(BaseModel):
    id: int
    zone_id: int
    zone_name: Optional[str] = None
    incident_type: str
    severity: str
    description: Optional[str]
    reported_by_user_id: int
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentResolveRequest(BaseModel):
    is_resolved: bool = True


# ---------- Saved Routes (any authenticated user) ----------

class SavedRouteCreate(BaseModel):
    label: str
    origin_zone_id: int
    destination_zone_id: int


class SavedRouteOut(BaseModel):
    id: int
    label: str
    origin_zone_id: int
    destination_zone_id: int
    origin_zone_name: Optional[str] = None
    destination_zone_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
