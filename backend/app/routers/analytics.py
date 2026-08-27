from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas, security, traffic_model
from app.database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics & Insights"])

CONGESTION_SCORE = {"low": 0, "medium": 1, "high": 2, "severe": 3}


def _level_value(level) -> str:
    return level.value if hasattr(level, "value") else level


@router.get("/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """City-wide snapshot for the analytics dashboard header cards."""
    total_zones = db.query(models.TrafficZone).count()

    active_incidents = (
        db.query(models.IncidentReport).filter(models.IncidentReport.is_resolved == 0).count()
    )

    since = datetime.utcnow() - timedelta(hours=24)
    total_predictions_24h = (
        db.query(models.TrafficPrediction)
        .filter(models.TrafficPrediction.created_at >= since)
        .count()
    )

    zones = db.query(models.TrafficZone).all()
    distribution = {"low": 0, "medium": 0, "high": 0, "severe": 0}
    speeds = []
    high_counts = Counter()

    for zone in zones:
        latest = (
            db.query(models.TrafficData)
            .filter(models.TrafficData.zone_id == zone.id)
            .order_by(models.TrafficData.recorded_at.desc())
            .first()
        )
        if latest:
            level = _level_value(latest.congestion_level)
            distribution[level] = distribution.get(level, 0) + 1
            speeds.append(latest.avg_speed_kmph)
            if level in ("high", "severe"):
                high_counts[zone.name] += 1

    busiest_zone = high_counts.most_common(1)[0][0] if high_counts else None
    city_avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else None

    return schemas.DashboardSummary(
        total_zones=total_zones,
        active_incidents=active_incidents,
        total_predictions_24h=total_predictions_24h,
        congestion_distribution=distribution,
        busiest_zone=busiest_zone,
        city_avg_speed_kmph=city_avg_speed,
    )


@router.get("/heatmap", response_model=List[schemas.HeatmapPoint])
def get_heatmap_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Latest congestion reading per zone, shaped for map-based heatmap rendering."""
    zones = db.query(models.TrafficZone).all()
    points = []
    for zone in zones:
        latest = (
            db.query(models.TrafficData)
            .filter(models.TrafficData.zone_id == zone.id)
            .order_by(models.TrafficData.recorded_at.desc())
            .first()
        )
        points.append(
            schemas.HeatmapPoint(
                zone_id=zone.id,
                zone_name=zone.name,
                latitude=zone.latitude,
                longitude=zone.longitude,
                congestion_level=_level_value(latest.congestion_level) if latest else "low",
                vehicle_count=latest.vehicle_count if latest else None,
            )
        )
    return points


@router.get("/road-performance", response_model=List[schemas.RoadPerformance])
def get_road_performance(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Groups recent readings by road type (highway / arterial / local).
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    zones = db.query(models.TrafficZone).all()
    zones_by_type = defaultdict(list)
    for zone in zones:
        zones_by_type[zone.road_type].append(zone)

    results = []
    for road_type, type_zones in zones_by_type.items():
        zone_ids = [z.id for z in type_zones]
        readings = (
            db.query(models.TrafficData)
            .filter(models.TrafficData.zone_id.in_(zone_ids), models.TrafficData.recorded_at >= since)
            .all()
        )

        if not readings:
            results.append(
                schemas.RoadPerformance(
                    road_type=road_type,
                    zone_count=len(type_zones),
                    reading_count=0,
                    avg_speed_kmph=0.0,
                    avg_vehicle_count=0.0,
                    avg_congestion_score=0.0,
                    worst_zone=None,
                )
            )
            continue

        avg_speed = sum(r.avg_speed_kmph for r in readings) / len(readings)
        avg_vehicles = sum(r.vehicle_count for r in readings) / len(readings)
        avg_score = sum(
            CONGESTION_SCORE.get(_level_value(r.congestion_level), 0) for r in readings
        ) / len(readings)

        zone_id_names = {z.id: z.name for z in type_zones}
        heavy_counts = Counter()
        for r in readings:
            if _level_value(r.congestion_level) in ("high", "severe"):
                heavy_counts[r.zone_id] += 1
        worst_zone = zone_id_names.get(heavy_counts.most_common(1)[0][0]) if heavy_counts else None

        results.append(
            schemas.RoadPerformance(
                road_type=road_type,
                zone_count=len(type_zones),
                reading_count=len(readings),
                avg_speed_kmph=round(avg_speed, 1),
                avg_vehicle_count=round(avg_vehicles, 1),
                avg_congestion_score=round(avg_score, 2),
                worst_zone=worst_zone,
            )
        )

    order = {"highway": 0, "arterial": 1, "local": 2}
    results.sort(key=lambda r: order.get(r.road_type, 3))

    return results


@router.get("/trends", response_model=List[schemas.ZoneTrend])
def get_trends(
    hours: int = Query(24, ge=1, le=168),
    zone_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Hourly-bucketed traffic trend per zone over the requested window.
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(models.TrafficZone)
    if zone_id is not None:
        query = query.filter(models.TrafficZone.id == zone_id)
    zones = query.all()

    results = []
    for zone in zones:
        readings = (
            db.query(models.TrafficData)
            .filter(models.TrafficData.zone_id == zone.id, models.TrafficData.recorded_at >= since)
            .order_by(models.TrafficData.recorded_at.asc())
            .all()
        )

        buckets = defaultdict(list)
        for r in readings:
            bucket_key = r.recorded_at.strftime("%Y-%m-%d %H:00")
            buckets[bucket_key].append(r)

        points = []
        for period in sorted(buckets.keys()):
            bucket_readings = buckets[period]
            avg_vehicles = sum(r.vehicle_count for r in bucket_readings) / len(bucket_readings)
            avg_speed = sum(r.avg_speed_kmph for r in bucket_readings) / len(bucket_readings)
            avg_score = sum(
                CONGESTION_SCORE.get(_level_value(r.congestion_level), 0) for r in bucket_readings
            ) / len(bucket_readings)
            points.append(
                schemas.TrendPoint(
                    period=period,
                    avg_vehicle_count=round(avg_vehicles, 1),
                    avg_speed_kmph=round(avg_speed, 1),
                    congestion_score=round(avg_score, 2),
                )
            )

        results.append(schemas.ZoneTrend(zone_id=zone.id, zone_name=zone.name, points=points))

    return results


@router.get("/recommendations", response_model=List[schemas.RecommendationOut])
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Returns recommendations/alerts ONLY for active, unresolved incident reports.
    """
    recommendations = []

    active_incidents = (
        db.query(models.IncidentReport).filter(models.IncidentReport.is_resolved == 0).all()
    )
    for incident in active_incidents:
        zone_name = incident.zone.name if incident.zone else "Unknown zone"
        incident_type = _level_value(incident.incident_type)
        severity = _level_value(incident.severity)
        recommendations.append(
            schemas.RecommendationOut(
                zone_id=incident.zone_id,
                zone_name=zone_name,
                title=f"Active {incident_type.replace('_', ' ').title()} at {zone_name}",
                message=(
                    f"Reported severity: {severity}. "
                    f"Route optimization for trips through this zone should be re-checked."
                ),
                severity="critical" if severity == "major" else "warning",
                source="incident",
            )
        )

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    recommendations.sort(key=lambda r: severity_order.get(r.severity, 3))

    return recommendations


@router.post("/recommendations/{zone_id}/dismiss", response_model=schemas.AlertDismissalOut)
def dismiss_congestion_alert(
    zone_id: int,
    minutes: int = Query(30, ge=1, le=1440, description="How long to suppress this zone's alert for."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    zone = db.query(models.TrafficZone).filter(models.TrafficZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    now = datetime.utcnow()
    dismissal = models.AlertDismissal(
        zone_id=zone_id,
        dismissed_by_user_id=current_user.id,
        dismissed_at=now,
        expires_at=now + timedelta(minutes=minutes),
    )
    db.add(dismissal)
    db.commit()
    db.refresh(dismissal)

    return schemas.AlertDismissalOut(
        zone_id=dismissal.zone_id,
        dismissed_at=dismissal.dismissed_at,
        expires_at=dismissal.expires_at,
    )


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@router.get("/peak-hours", response_model=schemas.PeakHourAnalysisOut)
def get_peak_hour_analysis(
    zone_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365, description="How many days of history to analyze."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Peak-hour forecasting & pattern analysis from actual historical readings.
    """
    zone = None
    if zone_id is not None:
        zone = db.query(models.TrafficZone).filter(models.TrafficZone.id == zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

    cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(models.TrafficData).filter(models.TrafficData.recorded_at >= cutoff)
    if zone_id is not None:
        query = query.filter(models.TrafficData.zone_id == zone_id)
    readings = query.all()

    if not readings:
        raise HTTPException(
            status_code=404,
            detail="No traffic data in this time window yet -- run the simulator for a while first.",
        )

    hourly_scores = defaultdict(list)
    daily_scores = defaultdict(list)
    for r in readings:
        score = CONGESTION_SCORE.get(_level_value(r.congestion_level), 0)
        hourly_scores[r.recorded_at.hour].append(score)
        daily_scores[r.recorded_at.weekday()].append(score)

    hourly_avgs = {
        hour: sum(scores) / len(scores) for hour, scores in hourly_scores.items()
    }
    daily_avgs = {
        dow: sum(scores) / len(scores) for dow, scores in daily_scores.items()
    }

    overall_hourly_mean = sum(hourly_avgs.values()) / len(hourly_avgs)
    sorted_hours = sorted(hourly_avgs.items(), key=lambda x: x[1], reverse=True)
    peak_hour_count = max(1, len(sorted_hours) // 4)
    peak_hour_set = {
        h for h, score in sorted_hours[:peak_hour_count] if score > overall_hourly_mean
    }

    overall_daily_mean = sum(daily_avgs.values()) / len(daily_avgs)
    sorted_days = sorted(daily_avgs.items(), key=lambda x: x[1], reverse=True)
    peak_day_count = max(1, len(sorted_days) // 4)
    peak_day_set = {
        d for d, score in sorted_days[:peak_day_count] if score > overall_daily_mean
    }

    hourly_pattern = [
        schemas.HourlyPatternPoint(
            hour=h,
            avg_congestion_score=round(hourly_avgs.get(h, 0.0), 2),
            sample_count=len(hourly_scores.get(h, [])),
            is_peak=h in peak_hour_set,
        )
        for h in range(24)
        if h in hourly_avgs
    ]
    hourly_pattern.sort(key=lambda p: p.hour)

    daily_pattern = [
        schemas.DailyPatternPoint(
            day_of_week=d,
            day_name=DAY_NAMES[d],
            avg_congestion_score=round(daily_avgs.get(d, 0.0), 2),
            sample_count=len(daily_scores.get(d, [])),
            is_peak=d in peak_day_set,
        )
        for d in range(7)
        if d in daily_avgs
    ]
    daily_pattern.sort(key=lambda p: p.day_of_week)

    peak_hours_list = sorted(peak_hour_set)
    peak_days_list = [DAY_NAMES[d] for d in sorted(peak_day_set)]

    scope = zone.name if zone else "across all zones"
    if peak_hours_list:
        hours_label = ", ".join(f"{h:02d}:00" for h in peak_hours_list)
        day_clause = f", most notably on {', '.join(peak_days_list)}" if peak_days_list else ""
        summary = (
            f"Based on {len(readings)} readings over the last {days} day(s), "
            f"congestion {scope} peaks around {hours_label}{day_clause}."
        )
    else:
        summary = (
            f"Based on {len(readings)} readings over the last {days} day(s), "
            f"congestion {scope} is fairly uniform throughout the day -- "
            f"no hour stands out significantly above the average."
        )

    return schemas.PeakHourAnalysisOut(
        zone_id=zone_id,
        zone_name=zone.name if zone else None,
        lookback_days=days,
        total_readings_analyzed=len(readings),
        hourly_pattern=hourly_pattern,
        daily_pattern=daily_pattern,
        peak_hours=peak_hours_list,
        peak_days=peak_days_list,
        summary=summary,
    )


@router.get("/road-conditions", response_model=List[schemas.RoadConditionOut])
def get_road_conditions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Per-zone road condition status combining live readings and active incidents.
    """
    zones = db.query(models.TrafficZone).all()

    active_incidents_by_zone = {}
    active_incidents = (
        db.query(models.IncidentReport)
        .filter(models.IncidentReport.is_resolved == 0)
        .all()
    )
    for inc in active_incidents:
        existing = active_incidents_by_zone.get(inc.zone_id)
        severity_rank = {"minor": 0, "moderate": 1, "major": 2}
        inc_severity = _level_value(inc.severity)
        if existing is None or severity_rank.get(inc_severity, 0) > severity_rank.get(_level_value(existing.severity), 0):
            active_incidents_by_zone[inc.zone_id] = inc

    results = []
    for zone in zones:
        latest = (
            db.query(models.TrafficData)
            .filter(models.TrafficData.zone_id == zone.id)
            .order_by(models.TrafficData.recorded_at.desc())
            .first()
        )
        incident = active_incidents_by_zone.get(zone.id)
        congestion_level = _level_value(latest.congestion_level) if latest else None

        if incident and _level_value(incident.incident_type) == "road_closure":
            status = "closed"
        elif incident:
            status = "impaired"
        elif congestion_level in ("high", "severe"):
            status = "congested"
        else:
            status = "normal"

        results.append(
            schemas.RoadConditionOut(
                zone_id=zone.id,
                zone_name=zone.name,
                road_type=zone.road_type,
                status=status,
                congestion_level=congestion_level,
                active_incident_type=_level_value(incident.incident_type) if incident else None,
                active_incident_severity=_level_value(incident.severity) if incident else None,
                last_updated=latest.recorded_at if latest else None,
            )
        )

    status_rank = {"closed": 0, "impaired": 1, "congested": 2, "normal": 3}
    results.sort(key=lambda r: status_rank.get(r.status, 4))
    return results