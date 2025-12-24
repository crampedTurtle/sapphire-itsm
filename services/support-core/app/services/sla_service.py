"""
SLA tracking and policy service
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict
from app.models.sla import SLAPolicy, SLAEvent, SLAEventType
from app.models.case import Case
from app.models.tenant import PlanTier
import uuid


def get_sla_policy(db: Session, tenant_id: uuid.UUID, tier: PlanTier) -> Optional[SLAPolicy]:
    """Get SLA policy for tenant and tier"""
    return db.query(SLAPolicy).filter(
        SLAPolicy.tenant_id == tenant_id,
        SLAPolicy.tier == tier
    ).first()


def get_default_sla_policy(tier: PlanTier) -> Dict[str, int]:
    """Get default SLA times in minutes"""
    defaults = {
        PlanTier.TIER0: {"first_response": 1440, "resolution": 4320},  # 24h / 72h
        PlanTier.TIER1: {"first_response": 240, "resolution": 1440},   # 4h / 24h
        PlanTier.TIER2: {"first_response": 60, "resolution": 480},     # 1h / 8h
    }
    return defaults.get(tier, defaults[PlanTier.TIER0])


def start_sla_tracking(db: Session, case_id: uuid.UUID):
    """Start SLA tracking for a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return
    
    # Get SLA policy
    policy = get_sla_policy(db, case.tenant_id, case.tenant.plan_tier)
    if not policy:
        defaults = get_default_sla_policy(case.tenant.plan_tier)
        first_response_minutes = defaults["first_response"]
        resolution_minutes = defaults["resolution"]
    else:
        first_response_minutes = policy.first_response_minutes
        resolution_minutes = policy.resolution_minutes
    
    # Log SLA start event
    sla_event = SLAEvent(
        case_id=case_id,
        event_type=SLAEventType.STARTED,
        payload={
            "first_response_minutes": first_response_minutes,
            "resolution_minutes": resolution_minutes,
            "started_at": datetime.utcnow().isoformat()
        }
    )
    db.add(sla_event)
    db.commit()


def check_sla_breaches(db: Session, case_id: uuid.UUID) -> Dict[str, bool]:
    """
    Check if case has breached SLA
    
    Returns:
        {
            "breached_first_response": bool,
            "breached_resolution": bool
        }
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {"breached_first_response": False, "breached_resolution": False}
    
    policy = get_sla_policy(db, case.tenant_id, case.tenant.plan_tier)
    if not policy:
        defaults = get_default_sla_policy(case.tenant.plan_tier)
        first_response_minutes = defaults["first_response"]
        resolution_minutes = defaults["resolution"]
    else:
        first_response_minutes = policy.first_response_minutes
        resolution_minutes = policy.resolution_minutes
    
    now = datetime.utcnow()
    case_age = now - case.created_at
    
    breached_first_response = case_age > timedelta(minutes=first_response_minutes)
    breached_resolution = case_age > timedelta(minutes=resolution_minutes)
    
    # Check if we've already logged these breaches
    existing_breaches = db.query(SLAEvent).filter(
        SLAEvent.case_id == case_id,
        SLAEvent.event_type.in_([SLAEventType.BREACHED_FIRST_RESPONSE, SLAEventType.BREACHED_RESOLUTION])
    ).all()
    
    breach_types_logged = {e.event_type for e in existing_breaches}
    
    # Log new breaches
    if breached_first_response and SLAEventType.BREACHED_FIRST_RESPONSE not in breach_types_logged:
        breach_event = SLAEvent(
            case_id=case_id,
            event_type=SLAEventType.BREACHED_FIRST_RESPONSE,
            payload={"breached_at": now.isoformat()}
        )
        db.add(breach_event)
    
    if breached_resolution and SLAEventType.BREACHED_RESOLUTION not in breach_types_logged:
        breach_event = SLAEvent(
            case_id=case_id,
            event_type=SLAEventType.BREACHED_RESOLUTION,
            payload={"breached_at": now.isoformat()}
        )
        db.add(breach_event)
    
    if breached_first_response or breached_resolution:
        db.commit()
    
    return {
        "breached_first_response": breached_first_response,
        "breached_resolution": breached_resolution
    }

