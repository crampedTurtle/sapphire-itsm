"""
Audit logging service
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.models.audit import AuditEvent
import uuid


def log_audit_event(
    db: Session,
    event_type: str,
    case_id: Optional[uuid.UUID] = None,
    intake_event_id: Optional[uuid.UUID] = None,
    payload: Optional[Dict[str, Any]] = None
):
    """Log an audit event"""
    audit_event = AuditEvent(
        case_id=case_id,
        intake_event_id=intake_event_id,
        event_type=event_type,
        payload=payload or {}
    )
    db.add(audit_event)
    db.commit()

