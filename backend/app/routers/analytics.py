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
    'Road performance tracking' -- groups recent readings by road type
    (highway / arterial / local) rather than by individual zone, so an
    operator can compare e.g. "how are highways performing city-wide"
    against "how are local roads performing," distinct from the per-zone
    trend charts above.
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

        # Zone within this road type with the most heavy-congestion readings
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

    # Highway first, then arterial, then local -- matches typical road hierarchy
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
    Hourly-bucketed traffic trend per zone over the requested window (default
    24h, max 7 days). Powers the trend line charts on the Analytics page.
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
    Two sources of recommendations:
      1. Congestion-pattern alerts -- driven by the trained RandomForest
         classifier (see app/traffic_model.py, same model used by
         /predict/congestion), run against each zone's recent live
         readings rather than a fixed heavy-reading-ratio threshold.
      2. Currently active incidents -- these are direct human reports, not
         predictions, so they stay rule-based by nature.

    Each recommendation still traces back to concrete inputs (readings,
    confidence score, active accident reports) rather than being an opaque
    output, so it stays explainable even though source 1 is now genuinely
    model-driven.
    """
    recommendations = []

    now = datetime.utcnow()
    dismissed_zone_ids = {
        d.zone_id
        for d in db.query(models.AlertDismissal)
        .filter(models.AlertDismissal.expires_at > now)
        .all()
    }

    accident_zone_ids = {
        i.zone_id
        for i in db.query(models.IncidentReport)
        .filter(
            models.IncidentReport.is_resolved == 0,
            models.IncidentReport.incident_type == models.IncidentType.accident,
        )
        .all()
    }

    zones = db.query(models.TrafficZone).all()
    for zone in zones:
        if zone.id in dismissed_zone_ids:
            continue
        recent = (
            db.query(models.TrafficData)
            .filter(models.TrafficData.zone_id == zone.id)
            .order_by(models.TrafficData.recorded_at.desc())
            .limit(3)
            .all()
        )
        if len(recent) < 2:
            continue

        # Smooth over the last few readings rather than feeding the model a
        # single noisy data point -- averages out sensor jitter between
        # simulator ticks while still reflecting current conditions.
        avg_vehicle_count = sum(r.vehicle_count for r in recent) / len(recent)
        avg_speed = sum(r.avg_speed_kmph for r in recent) / len(recent)
        road_occupancy_pct = traffic_model.estimate_road_occupancy_pct(
            avg_vehicle_count, zone.road_type
        )
        has_accident = zone.id in accident_zone_ids

        predicted_label, confidence, _probs = traffic_model.predict_congestion(
            vehicle_count=avg_vehicle_count,
            avg_speed_kmph=avg_speed,
            road_occupancy_pct=road_occupancy_pct,
            accident_report=1 if has_accident else 0,
        )

        if predicted_label == "high" and confidence >= 0.5:
            accident_note = " and an active accident report" if has_accident else ""
            recommendations.append(
                schemas.RecommendationOut(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    title=f"AI predicts high congestion at {zone.name}",
                    message=(
                        f"Model confidence {round(confidence * 100)}%, based on "
                        f"~{round(avg_vehicle_count)} vehicles, {round(avg_speed, 1)} km/h "
                        f"avg speed{accident_note}. Consider recommending alternate routes "
                        f"for trips through this zone."
                    ),
                    severity="critical" if confidence >= 0.85 else "warning",
                    source="congestion",
                )
            )

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
                title=f"Active {incident_type.replace('_', ' ')} at {zone_name}",
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
    minutes: int = Query(30, ge=1, le=1440, description="How long to suppress this zone's persistent-congestion alert for."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    """
    Dismiss/acknowledge the 'persistent congestion' recommendation for a
    zone. Only applies to congestion-pattern alerts (source='congestion') --
    those aren't stored rows like incidents, so there's nothing to PATCH
    resolved. Instead this records a cooldown window; get_recommendations
    suppresses the zone's congestion alert until it expires. If the
    underlying congestion clears before the cooldown ends, the alert simply
    won't come back once it does expire, since the model will no longer
    predict high congestion for that zone.
    """
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
