from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db

router = APIRouter(prefix="/routes", tags=["Route Optimization"])

# Public OSRM demo server -- free, no API key required. For production use,
# self-hosting OSRM (or switching to a paid provider like Google/Mapbox) is
# recommended, since the public demo server has rate limits and no uptime
# guarantee. Swapping providers only requires changing OSRM_BASE_URL and the
# request/response parsing below, since the rest of this router (congestion
# adjustment, DB lookups, response shaping) is provider-agnostic.
OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"

# How much a given average congestion level inflates the raw travel time
# estimate. These are reasonable placeholder multipliers -- calibrating them
# against real historical travel-time data would be the natural next step.
CONGESTION_MULTIPLIERS = {
    "low": 1.0,
    "medium": 1.25,
    "high": 1.6,
    "severe": 2.0,
}


def _resolve_point(zone_id: Optional[int], lat: Optional[float], lng: Optional[float], db: Session, label: str):
    """Resolve a request's origin/destination into concrete (lat, lng),
    preferring a zone lookup over raw coordinates if both are given."""
    if zone_id is not None:
        zone = db.query(models.TrafficZone).filter(models.TrafficZone.id == zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail=f"{label} zone_id {zone_id} not found")
        return zone.latitude, zone.longitude

    if lat is not None and lng is not None:
        return lat, lng

    raise HTTPException(
        status_code=422,
        detail=f"Provide either {label.lower()}_zone_id or both {label.lower()}_lat/{label.lower()}_lng",
    )


def _current_congestion_level(db: Session) -> str:
    """Uses the average congestion across all zones' most recent readings as
    a city-wide proxy for route-time congestion. This is a simplification --
    a more accurate system would map specific road segments along the route
    geometry to nearby traffic zones -- but it's a reasonable first pass and
    is documented as such rather than presented as more precise than it is."""
    recent = (
        db.query(models.TrafficData.congestion_level)
        .order_by(models.TrafficData.recorded_at.desc())
        .limit(20)
        .all()
    )
    if not recent:
        return "low"

    levels = [r[0].value if hasattr(r[0], "value") else r[0] for r in recent]
    most_common = max(set(levels), key=levels.count)
    return most_common


def _active_incidents_for_zones(db: Session, zone_ids: list) -> list:
    """Returns unresolved incidents reported at the given zone IDs. Used to
    connect Milestone 2's route optimization with Milestone 3's incident
    reporting -- a route touching a zone with an active major incident
    should be flagged, not silently recommended as the fastest option."""
    zone_ids = [z for z in zone_ids if z is not None]
    if not zone_ids:
        return []
    return (
        db.query(models.IncidentReport)
        .filter(
            models.IncidentReport.zone_id.in_(zone_ids),
            models.IncidentReport.is_resolved == 0,
        )
        .all()
    )


@router.post("/optimize", response_model=schemas.RouteOptimizeResponse)
def optimize_route(
    payload: schemas.RouteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Fetches alternate driving routes between an origin and destination via
    OSRM, then ranks them by a congestion-adjusted travel time estimate
    using the platform's current live traffic data.
    """
    origin_lat, origin_lng = _resolve_point(
        payload.origin_zone_id, payload.origin_lat, payload.origin_lng, db, "Origin"
    )
    dest_lat, dest_lng = _resolve_point(
        payload.destination_zone_id, payload.destination_lat, payload.destination_lng, db, "Destination"
    )

    # OSRM expects "lng,lat" order (GeoJSON convention), not "lat,lng"
    coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    url = f"{OSRM_BASE_URL}/{coords}"
    params = {"alternatives": "true", "overview": "full", "geometries": "geojson"}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Routing service unavailable: {exc}",
        )

    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(status_code=502, detail="No routes found for the given points")

    congestion_level = _current_congestion_level(db)
    multiplier = CONGESTION_MULTIPLIERS.get(congestion_level, 1.0)

    # Milestone 2 x Milestone 3 integration: check whether the origin or
    # destination zone has an active incident, and penalize the ETA + surface
    # an explicit warning if so, rather than silently recommending a route
    # through it as "fastest."
    incidents = _active_incidents_for_zones(
        db, [payload.origin_zone_id, payload.destination_zone_id]
    )
    incident_penalty = 1.0
    incident_warnings = []
    for inc in incidents:
        severity = inc.severity.value if hasattr(inc.severity, "value") else inc.severity
        incident_type = inc.incident_type.value if hasattr(inc.incident_type, "value") else inc.incident_type
        zone_name = inc.zone.name if inc.zone else "this zone"
        incident_warnings.append(
            f"Active {incident_type.replace('_', ' ')} ({severity}) reported at {zone_name} — "
            f"expect delays on routes through this area."
        )
        # Major incidents add a heavier penalty than minor ones
        incident_penalty = max(incident_penalty, {"minor": 1.15, "moderate": 1.35, "major": 1.75}.get(severity, 1.2))

    combined_multiplier = round(multiplier * incident_penalty, 2)

    route_options = []
    for r in data["routes"]:
        base_duration_min = r["duration"] / 60
        distance_km = r["distance"] / 1000
        # OSRM geometry is [lng, lat] pairs -- swap to [lat, lng] for standard
        # web-map libraries (Leaflet, etc.) which expect lat first
        geometry = [[pt[1], pt[0]] for pt in r["geometry"]["coordinates"]]

        route_options.append(
            schemas.RouteOption(
                distance_km=round(distance_km, 2),
                base_duration_min=round(base_duration_min, 1),
                congestion_multiplier=combined_multiplier,
                estimated_duration_min=round(base_duration_min * combined_multiplier, 1),
                geometry=geometry,
            )
        )

    # Recommend the route with the lowest congestion-adjusted time
    route_options.sort(key=lambda r: r.estimated_duration_min)
    if route_options:
        route_options[0].is_recommended = True

    return schemas.RouteOptimizeResponse(
        origin={"lat": origin_lat, "lng": origin_lng},
        destination={"lat": dest_lat, "lng": dest_lng},
        congestion_level_used=congestion_level,
        routes=route_options,
        incident_warnings=incident_warnings,
    )


# ---------- Saved Routes ----------
# Available to every role -- primarily aimed at regular public users who
# want to quickly re-run a route they check often (e.g. "Home to Office"),
# but operators/admins can use it too since there's no reason to restrict it.

@router.post("/saved", response_model=schemas.SavedRouteOut, status_code=201)
def save_route(
    payload: schemas.SavedRouteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    origin = db.query(models.TrafficZone).filter(models.TrafficZone.id == payload.origin_zone_id).first()
    destination = db.query(models.TrafficZone).filter(models.TrafficZone.id == payload.destination_zone_id).first()
    if not origin or not destination:
        raise HTTPException(status_code=404, detail="Origin or destination zone not found")

    saved = models.SavedRoute(
        user_id=current_user.id,
        label=payload.label,
        origin_zone_id=payload.origin_zone_id,
        destination_zone_id=payload.destination_zone_id,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return schemas.SavedRouteOut(
        id=saved.id,
        label=saved.label,
        origin_zone_id=saved.origin_zone_id,
        destination_zone_id=saved.destination_zone_id,
        origin_zone_name=origin.name,
        destination_zone_name=destination.name,
        created_at=saved.created_at,
    )


@router.get("/saved", response_model=list[schemas.SavedRouteOut])
def list_saved_routes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Only returns the current user's own saved routes -- not anyone else's."""
    saved_routes = (
        db.query(models.SavedRoute)
        .filter(models.SavedRoute.user_id == current_user.id)
        .order_by(models.SavedRoute.created_at.desc())
        .all()
    )
    results = []
    for s in saved_routes:
        results.append(
            schemas.SavedRouteOut(
                id=s.id,
                label=s.label,
                origin_zone_id=s.origin_zone_id,
                destination_zone_id=s.destination_zone_id,
                origin_zone_name=s.origin_zone.name if s.origin_zone else None,
                destination_zone_name=s.destination_zone.name if s.destination_zone else None,
                created_at=s.created_at,
            )
        )
    return results


@router.delete("/saved/{saved_route_id}", status_code=204)
def delete_saved_route(
    saved_route_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    saved = (
        db.query(models.SavedRoute)
        .filter(models.SavedRoute.id == saved_route_id, models.SavedRoute.user_id == current_user.id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail="Saved route not found")
    db.delete(saved)
    db.commit()
    return None
