from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db

router = APIRouter(prefix="/incidents", tags=["Incident Reports"])


def _to_out(incident: models.IncidentReport) -> schemas.IncidentReportOut:
    return schemas.IncidentReportOut(
        id=incident.id,
        zone_id=incident.zone_id,
        zone_name=incident.zone.name if incident.zone else None,
        incident_type=incident.incident_type.value if hasattr(incident.incident_type, "value") else incident.incident_type,
        severity=incident.severity.value if hasattr(incident.severity, "value") else incident.severity,
        description=incident.description,
        reported_by_user_id=incident.reported_by_user_id,
        is_resolved=bool(incident.is_resolved),
        created_at=incident.created_at,
    )


@router.post("", response_model=schemas.IncidentReportOut, status_code=201)
def report_incident(
    payload: schemas.IncidentReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    """Operators/admins only -- regular public 'user' accounts cannot report
    incidents, only view them (see GET below)."""
    zone = db.query(models.TrafficZone).filter(models.TrafficZone.id == payload.zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    if payload.incident_type not in [t.value for t in models.IncidentType]:
        raise HTTPException(status_code=422, detail="Invalid incident_type")
    if payload.severity not in [s.value for s in models.IncidentSeverity]:
        raise HTTPException(status_code=422, detail="Invalid severity")

    incident = models.IncidentReport(
        zone_id=payload.zone_id,
        incident_type=payload.incident_type,
        severity=payload.severity,
        description=payload.description,
        reported_by_user_id=current_user.id,
        is_resolved=0,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return _to_out(incident)


@router.get("", response_model=List[schemas.IncidentReportOut])
def list_incidents(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Any authenticated role can VIEW incidents -- reporting is restricted,
    viewing is not, since regular users benefit from seeing active alerts."""
    query = db.query(models.IncidentReport)
    if active_only:
        query = query.filter(models.IncidentReport.is_resolved == 0)
    incidents = query.order_by(models.IncidentReport.created_at.desc()).limit(50).all()
    return [_to_out(i) for i in incidents]


@router.patch("/{incident_id}/resolve", response_model=schemas.IncidentReportOut)
def resolve_incident(
    incident_id: int,
    payload: schemas.IncidentResolveRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    incident = db.query(models.IncidentReport).filter(models.IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.is_resolved = 1 if payload.is_resolved else 0
    db.commit()
    db.refresh(incident)
    return _to_out(incident)
