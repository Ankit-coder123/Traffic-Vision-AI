from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db
from app.email_utils import send_incident_alert_email

router = APIRouter(prefix="/incidents", tags=["Incident Reporting"])


@router.post("", response_model=schemas.IncidentReportOut, status_code=status.HTTP_201_CREATED)
def report_incident(
    payload: schemas.IncidentReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    """
    Report a new traffic incident (operator or admin).
    Feeds the real-time alerts system and persists the report.
    """
    zone = db.query(models.TrafficZone).filter(models.TrafficZone.id == payload.zone_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

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

    # Optional email alert broadcast to the reporter (or operator list)
    recipient_emails = [current_user.email] if current_user.email else []
    if recipient_emails:
        background_tasks.add_task(
            send_incident_alert_email,
            recipient_emails=recipient_emails,
            zone_name=zone.name,
            incident_type=str(payload.incident_type),
            severity=str(payload.severity),
            description=payload.description,
        )

    incident.zone_name = zone.name
    return incident


@router.get("", response_model=List[schemas.IncidentReportOut])
def list_incidents(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    List incident reports. Any authenticated user can view them.
    Optional query param ?active_only=true returns only unresolved incidents.
    """
    query = db.query(models.IncidentReport)
    if active_only:
        query = query.filter(models.IncidentReport.is_resolved == 0)

    incidents = query.order_by(models.IncidentReport.created_at.desc()).all()

    for inc in incidents:
        inc.zone_name = inc.zone.name if inc.zone else f"Zone #{inc.zone_id}"

    return incidents


@router.patch("/{incident_id}/resolve", response_model=schemas.IncidentReportOut)
def resolve_incident(
    incident_id: int,
    payload: schemas.IncidentResolveRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    """
    Mark an active incident report as resolved (or reopen it).
    Operator or admin only.
    """
    incident = db.query(models.IncidentReport).filter(models.IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.is_resolved = 1 if payload.is_resolved else 0
    db.commit()
    db.refresh(incident)

    incident.zone_name = incident.zone.name if incident.zone else f"Zone #{incident.zone_id}"
    return incident