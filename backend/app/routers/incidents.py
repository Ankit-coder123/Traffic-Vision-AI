from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db
from app.email_utils import send_incident_alert_email

router = APIRouter(prefix="/incidents", tags=["Incident Reporting"])


def _broadcast_incident_alert(db: Session, background_tasks: BackgroundTasks, incident: models.IncidentReport, zone_name: str):
    """Helper to collect all valid registered user emails and trigger individual SMTP sends."""
    all_users = db.query(models.User.email).all()
    recipient_emails = [
        user.email.strip()
        for user in all_users
        if user.email and "@" in user.email and not user.email.strip().lower().endswith("@trafficvision.ai")
    ]

    if recipient_emails:
        severity_str = str(incident.severity.value if hasattr(incident.severity, "value") else incident.severity)
        type_str = str(incident.incident_type.value if hasattr(incident.incident_type, "value") else incident.incident_type)

        background_tasks.add_task(
            send_incident_alert_email,
            recipient_emails=recipient_emails,
            zone_name=zone_name,
            incident_type=type_str,
            severity=severity_str,
            description=incident.description,
        )


@router.post("", response_model=schemas.IncidentReportOut, status_code=status.HTTP_201_CREATED)
def report_incident(
    payload: schemas.IncidentReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    """
    Report a new traffic incident.
    - Admins: Auto-verified and email alerts are dispatched immediately.
    - Operators: Saved as unverified pending Admin approval (no spam broadcast).
    """
    zone = db.query(models.TrafficZone).filter(models.TrafficZone.id == payload.zone_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    is_admin = current_user.role == models.UserRole.admin or str(current_user.role) == "admin"

    incident = models.IncidentReport(
        zone_id=payload.zone_id,
        incident_type=payload.incident_type,
        severity=payload.severity,
        description=payload.description,
        reported_by_user_id=current_user.id,
        is_resolved=0,
        is_verified=1 if is_admin else 0,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    incident.zone_name = zone.name

    # Trigger instant broadcast only if reported directly by an Admin
    if is_admin:
        _broadcast_incident_alert(db, background_tasks, incident, zone.name)

    return incident


@router.patch("/{incident_id}/verify", response_model=schemas.IncidentReportOut)
def verify_incident(
    incident_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_admin),
):
    """
    Admin-only endpoint: Approve an operator-reported incident and trigger email broadcast to all users.
    """
    incident = db.query(models.IncidentReport).filter(models.IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    if bool(incident.is_verified):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident is already verified")

    incident.is_verified = 1
    db.commit()
    db.refresh(incident)

    zone_name = incident.zone.name if getattr(incident, "zone", None) else f"Zone #{incident.zone_id}"
    incident.zone_name = zone_name

    _broadcast_incident_alert(db, background_tasks, incident, zone_name)

    return incident


@router.get("", response_model=List[schemas.IncidentReportOut])
def list_incidents(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    List incident reports.
    """
    query = db.query(models.IncidentReport)
    if active_only:
        query = query.filter(models.IncidentReport.is_resolved == 0)

    incidents = query.order_by(models.IncidentReport.created_at.desc()).all()

    # Safely attach zone_name and boolean states
    for inc in incidents:
        inc.zone_name = inc.zone.name if getattr(inc, "zone", None) else f"Zone #{inc.zone_id}"
        inc.is_resolved = bool(inc.is_resolved)
        inc.is_verified = bool(getattr(inc, "is_verified", 0))

    return incidents


@router.patch("/{incident_id}/resolve", response_model=schemas.IncidentReportOut)
def resolve_incident(
    incident_id: int,
    payload: schemas.IncidentResolveRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_operator_or_admin),
):
    """
    Mark an active incident report as resolved.
    """
    incident = db.query(models.IncidentReport).filter(models.IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.is_resolved = 1 if payload.is_resolved else 0
    db.commit()
    db.refresh(incident)

    incident.zone_name = incident.zone.name if getattr(incident, "zone", None) else f"Zone #{incident.zone_id}"
    incident.is_resolved = bool(incident.is_resolved)
    incident.is_verified = bool(getattr(incident, "is_verified", 0))

    return incident