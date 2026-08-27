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
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    credential: str


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
    hour: Optional[int] = None                  # 0-23
    is_weekend: Optional[bool] = None


class CongestionPredictionResponse(BaseModel):
    predicted_congestion: str
    confidence: float
    probabilities: dict                        # e.g. {"low": 0.1, "medium": 0.7, "high": 0.2}
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
    origin_zone_id: Optional[int] = None
    destination_zone_id: Optional[int] = None
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None


class RouteOption(BaseModel):
    distance_km: float
    base_duration_min: float
    congestion_multiplier: float
    estimated_duration_min: float
    geometry: list
    is_recommended: bool = False


class RouteOptimizeResponse(BaseModel):
    origin: dict
    destination: dict
    congestion_level_used: str
    routes: list[RouteOption]
    incident_warnings: list[str] = []


# ---------- Incident Reports (operator/admin only) ----------

class IncidentReportCreate(BaseModel):
    zone_id: int
    incident_type: str   # accident | road_closure | construction | hazard | other
    severity: str        # minor | moderate | major
    description: Optional[str] = None


class IncidentReportOut(BaseModel):
    id: int
    zone_id: int
    zone_name: Optional[str] = None
    incident_type: str
    severity: str
    description: Optional[str] = None
    reported_by_user_id: int
    is_resolved: bool
    created_at: Optional[datetime] = None

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


# ---------- Analytics ----------

class DashboardSummary(BaseModel):
    total_zones: int
    active_incidents: int
    total_predictions_24h: int
    congestion_distribution: dict
    busiest_zone: Optional[str] = None
    city_avg_speed_kmph: Optional[float] = None


class HeatmapPoint(BaseModel):
    zone_id: int
    zone_name: str
    latitude: float
    longitude: float
    congestion_level: str
    vehicle_count: Optional[int] = None


class RoadConditionOut(BaseModel):
    zone_id: int
    zone_name: str
    road_type: str
    status: str
    congestion_level: Optional[str] = None
    active_incident_type: Optional[str] = None
    active_incident_severity: Optional[str] = None
    last_updated: Optional[datetime] = None


class RoadPerformance(BaseModel):
    road_type: str
    zone_count: int
    reading_count: int
    avg_speed_kmph: float
    avg_vehicle_count: float
    avg_congestion_score: float
    worst_zone: Optional[str] = None


class TrendPoint(BaseModel):
    period: str
    avg_vehicle_count: float
    avg_speed_kmph: float
    congestion_score: float


class ZoneTrend(BaseModel):
    zone_id: int
    zone_name: str
    points: list[TrendPoint]


class RecommendationOut(BaseModel):
    zone_id: Optional[int]
    zone_name: Optional[str]
    title: str
    message: str
    severity: str
    source: str


class AlertDismissalOut(BaseModel):
    zone_id: int
    dismissed_at: datetime
    expires_at: datetime


class HourlyPatternPoint(BaseModel):
    hour: int
    avg_congestion_score: float
    sample_count: int
    is_peak: bool


class DailyPatternPoint(BaseModel):
    day_of_week: int
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
    peak_hours: List[int]
    peak_days: List[str]
    summary: str