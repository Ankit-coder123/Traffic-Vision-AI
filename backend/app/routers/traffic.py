from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/traffic", tags=["Traffic Monitoring"])


@router.post("/zones", response_model=schemas.TrafficZoneOut)
def create_zone(
    zone_in: schemas.TrafficZoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),  # only admins add zones
):
    zone = models.TrafficZone(**zone_in.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("/zones", response_model=List[schemas.TrafficZoneOut])
def list_zones(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.TrafficZone).all()


@router.post("/data", response_model=schemas.TrafficDataOut, status_code=201)
def ingest_traffic_data(
    data_in: schemas.TrafficDataCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Called by the simulator (or, in production, real sensor gateways) to
    push a new traffic reading for a zone.
    """
    reading = models.TrafficData(**data_in.model_dump())
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/live", response_model=List[schemas.TrafficDataOut])
def get_live_traffic(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """
    Returns the MOST RECENT traffic reading per zone — this is what the
    live dashboard will poll every few seconds.
    """
    zones = db.query(models.TrafficZone).all()
    latest_readings = []
    for zone in zones:
        latest = (
            db.query(models.TrafficData)
            .filter(models.TrafficData.zone_id == zone.id)
            .order_by(models.TrafficData.recorded_at.desc())
            .first()
        )
        if latest:
            latest_readings.append(latest)
    return latest_readings


@router.get("/history/{zone_id}", response_model=List[schemas.TrafficDataOut])
def get_zone_history(zone_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.TrafficData)
        .filter(models.TrafficData.zone_id == zone_id)
        .order_by(models.TrafficData.recorded_at.desc())
        .limit(50)
        .all()
    )
