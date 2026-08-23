from datetime import datetime
from typing import List, Optional

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


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None   # required only if setting new_password
    new_password: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    credential: str   # the ID token JWT returned by Google Identity Services


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


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
    incident_warnings: list[str] = []


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


# ---------- Analytics (Milestone 3) ----------

class DashboardSummary(BaseModel):
    total_zones: int
    active_incidents: int
    total_predictions_24h: int
    congestion_distribution: dict          # {"low": 5, "medium": 10, "high": 7}
    busiest_zone: Optional[str] = None       # zone with most 'high' readings recently
    city_avg_speed_kmph: Optional[float] = None


class HeatmapPoint(BaseModel):
    zone_id: int
    zone_name: str
    latitude: float
    longitude: float
    congestion_level: str        # most recent reading's level
    vehicle_count: Optional[int] = None


class RoadConditionOut(BaseModel):
    zone_id: int
    zone_name: str
    road_type: str
    status: str                       # 'normal' | 'congested' | 'impaired' | 'closed'
    congestion_level: Optional[str]   # most recent reading's level, if any
    active_incident_type: Optional[str] = None
    active_incident_severity: Optional[str] = None
    last_updated: Optional[datetime] = None


class RoadPerformance(BaseModel):
    road_type: str                    # 'highway' | 'arterial' | 'local'
    zone_count: int                   # how many zones of this road type
    reading_count: int                # how many recent readings this is based on
    avg_speed_kmph: float
    avg_vehicle_count: float
    avg_congestion_score: float       # 0=low .. 3=severe
    worst_zone: Optional[str] = None  # zone with the most 'high'/'severe' readings in this group


class TrendPoint(BaseModel):
    period: str            # e.g. "2026-07-28 14:00" (hourly bucket)
    avg_vehicle_count: float
    avg_speed_kmph: float
    congestion_score: float   # numeric encoding of avg congestion (0=low .. 3=severe)


class ZoneTrend(BaseModel):
    zone_id: int
    zone_name: str
    points: list[TrendPoint]


class RecommendationOut(BaseModel):
    zone_id: Optional[int]
    zone_name: Optional[str]
    title: str
    message: str
    severity: str   # 'info' | 'warning' | 'critical'
    source: str     # 'congestion' | 'incident' -- lets the UI avoid double-counting
                    # an incident that already appears in the incidents list


class AlertDismissalOut(BaseModel):
    zone_id: int
    dismissed_at: datetime
    expires_at: datetime


class HourlyPatternPoint(BaseModel):
    hour: int              # 0-23
    avg_congestion_score: float   # 0 (low) - 3 (severe)
    sample_count: int
    is_peak: bool          # True if this hour is among the top peak hours


class DailyPatternPoint(BaseModel):
    day_of_week: int       # 0=Monday ... 6=Sunday (Python's datetime.weekday() convention)
    day_name: str
    avg_congestion_score: float
    sample_count: int
    is_peak: bool


class PeakHourAnalysisOut(BaseModel):
    zone_id: Optional[int]
    zone_name: Optional[str]
    lookback_days: int
    total_readings_analyzed: int
    hourly_pattern: List[HourlyPatternPoint]
    daily_pattern: List[DailyPatternPoint]
    peak_hours: List[int]      # the actual hour numbers flagged as peak
    peak_days: List[str]       # the actual day names flagged as peak
    summary: str                # plain-language takeaway
