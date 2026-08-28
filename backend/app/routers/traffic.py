import math
import random
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db

router = APIRouter(prefix="/traffic", tags=["Traffic Monitoring"])


@router.get("/zones", response_model=List[schemas.TrafficZoneOut])
def list_zones(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    List all traffic monitoring zones.
    """
    return db.query(models.TrafficZone).order_by(models.TrafficZone.id.asc()).all()


@router.get("/live", response_model=List[schemas.TrafficDataOut])
def get_live_traffic(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Returns simulated real-time traffic state for every zone.
    Generates dynamic readings on each 5-second poll cycle based on
    time-of-day curves and active road incidents.
    """
    zones = db.query(models.TrafficZone).order_by(models.TrafficZone.id.asc()).all()
    if not zones:
        return []

    now = datetime.utcnow()
    current_hour = now.hour

    # Query any active (unresolved) incidents affecting zone conditions
    active_incidents = db.query(models.IncidentReport).filter(models.IncidentReport.is_resolved == 0).all()
    incident_map = {inc.zone_id: inc.severity for inc in active_incidents}

    # Rush-hour wave (peaks at 9 AM and 6 PM)
    morning_peak = math.exp(-((current_hour - 9) ** 2) / 8)
    evening_peak = math.exp(-((current_hour - 18) ** 2) / 8)
    time_factor = 0.35 + 0.65 * max(morning_peak, evening_peak)

    readings = []

    for zone in zones:
        # Base count + 5-second dynamic jitter
        base_count = int(30 + 65 * time_factor)
        noise = random.randint(-8, 8)
        vehicle_count = max(10, min(140, base_count + noise))

        # Dynamic speed calculation
        base_speed = 62.0 - (vehicle_count * 0.35)
        speed_noise = random.uniform(-3.5, 3.5)
        avg_speed = max(12.0, min(75.0, round(base_speed + speed_noise, 1)))

        # Adjust for active incidents in this zone
        if zone.id in incident_map:
            sev = str(incident_map[zone.id]).lower()
            if "major" in sev:
                avg_speed = max(8.0, round(avg_speed * 0.4, 1))
                vehicle_count = min(150, vehicle_count + 35)
            elif "moderate" in sev:
                avg_speed = max(14.0, round(avg_speed * 0.65, 1))
                vehicle_count = min(130, vehicle_count + 18)

        # Categorize congestion status
        if avg_speed < 22.0 or vehicle_count >= 85:
            congestion_level = "severe" if avg_speed < 15.0 else "high"
        elif avg_speed < 40.0 or vehicle_count >= 50:
            congestion_level = "medium"
        else:
            congestion_level = "low"

        readings.append(
            schemas.TrafficDataOut(
                id=zone.id,
                zone_id=zone.id,
                vehicle_count=vehicle_count,
                avg_speed_kmph=avg_speed,
                congestion_level=congestion_level,
                recorded_at=now,
            )
        )

    return readings