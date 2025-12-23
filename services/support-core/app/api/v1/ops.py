"""
Ops Center API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models.case import Case, CaseStatus, CasePriority, CaseCategory, CaseMessage
from app.models.intake import IntakeEvent, IntentClassification, Intent
from app.models.sla import SLAEvent, SLAEventType
from app.models.ai import AIArtifact
from app.models.tenant import PlanTier, Tenant
from app.models.onboarding import OnboardingSession, OnboardingStatus

router = APIRouter()


class CaseUpdateRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    owner_identity_id: Optional[uuid.UUID] = None
    internal_notes: Optional[str] = None


@router.get("/metrics/intake")
async def get_intake_metrics(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Get intake metrics by intent"""
    if not start_time:
        start_time = datetime.utcnow() - timedelta(days=7)
    if not end_time:
        end_time = datetime.utcnow()
    
    # Get intake events in time window
    intake_events = db.query(IntakeEvent).filter(
        and_(
            IntakeEvent.created_at >= start_time,
            IntakeEvent.created_at <= end_time
        )
    ).all()
    
    # Get latest classification for each intake event
    intent_counts = {}
    for event in intake_events:
        classification = db.query(IntentClassification).filter(
            IntentClassification.intake_event_id == event.id
        ).order_by(IntentClassification.created_at.desc()).first()
        
        if classification:
            intent_value = classification.intent.value
            intent_counts[intent_value] = intent_counts.get(intent_value, 0) + 1
    
    total = sum(intent_counts.values())
    
    return {
        "time_window": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "total_intake": total,
        "by_intent": intent_counts,
        "distribution": {
            intent: round(count / total * 100, 2) if total > 0 else 0
            for intent, count in intent_counts.items()
        }
    }


@router.get("/cases")
async def get_ops_cases(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get cases with filters for ops center"""
    query = db.query(Case)
    
    # Apply filters
    if status:
        try:
            status_enum = CaseStatus(status)
            query = query.filter(Case.status == status_enum)
        except ValueError:
            pass
    
    if priority:
        try:
            priority_enum = CasePriority(priority)
            query = query.filter(Case.priority == priority_enum)
        except ValueError:
            pass
    
    if tenant_id:
        query = query.filter(Case.tenant_id == tenant_id)
    
    if tier:
        try:
            tier_enum = PlanTier(tier)
            # Join with tenant to filter by tier
            query = query.join(Tenant).filter(Tenant.plan_tier == tier_enum)
        except ValueError:
            pass
    
    # Order by created_at desc
    query = query.order_by(Case.created_at.desc())
    
    # Paginate
    total = query.count()
    cases = query.offset(offset).limit(limit).all()
    
    # Get message counts and SLA status
    result_cases = []
    for case in cases:
        message_count = db.query(func.count()).select_from(CaseMessage).filter(
            CaseMessage.case_id == case.id
        ).scalar()
        
        # Check SLA breaches
        breach_events = db.query(SLAEvent).filter(
            and_(
                SLAEvent.case_id == case.id,
                SLAEvent.event_type.in_([SLAEventType.BREACHED_FIRST_RESPONSE, SLAEventType.BREACHED_RESOLUTION])
            )
        ).all()
        
        # Check onboarding status
        onboarding_session = db.query(OnboardingSession).filter(
            OnboardingSession.tenant_id == case.tenant_id
        ).first()
        
        onboarding_status = None
        if onboarding_session and onboarding_session.status == OnboardingStatus.ACTIVE:
            onboarding_status = {
                "status": onboarding_session.status.value,
                "phase": onboarding_session.current_phase.value,
                "is_onboarding": True
            }
        
        result_cases.append({
            "id": str(case.id),
            "tenant_id": str(case.tenant_id),
            "title": case.title,
            "status": case.status.value,
            "priority": case.priority.value,
            "category": case.category.value,
            "created_at": case.created_at.isoformat(),
            "updated_at": case.updated_at.isoformat(),
            "messages_count": message_count or 0,
            "sla_breached": len(breach_events) > 0,
            "onboarding": onboarding_status
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "cases": result_cases
    }


@router.get("/alerts")
async def get_ops_alerts(
    db: Session = Depends(get_db)
):
    """Get alerts for SLA risk, compliance flags, low confidence"""
    alerts = []
    
    # SLA breaches
    breach_events = db.query(SLAEvent).filter(
        SLAEvent.event_type.in_([SLAEventType.BREACHED_FIRST_RESPONSE, SLAEventType.BREACHED_RESOLUTION])
    ).order_by(SLAEvent.created_at.desc()).limit(50).all()
    
    for event in breach_events:
        case = db.query(Case).filter(Case.id == event.case_id).first()
        if case:
            alerts.append({
                "type": "sla_breach",
                "severity": "high",
                "case_id": str(case.id),
                "case_title": case.title,
                "event_type": event.event_type.value,
                "created_at": event.created_at.isoformat()
            })
    
    # Compliance flags
    compliance_classifications = db.query(IntentClassification).filter(
        IntentClassification.compliance_flag == True
    ).order_by(IntentClassification.created_at.desc()).limit(50).all()
    
    for classification in compliance_classifications:
        intake_event = db.query(IntakeEvent).filter(
            IntakeEvent.id == classification.intake_event_id
        ).first()
        if intake_event:
            alerts.append({
                "type": "compliance_flag",
                "severity": "critical",
                "intake_event_id": str(intake_event.id),
                "from_email": intake_event.from_email,
                "intent": classification.intent.value,
                "created_at": classification.created_at.isoformat()
            })
    
    # Low confidence AI classifications
    low_confidence = db.query(IntentClassification).filter(
        IntentClassification.confidence < 0.5
    ).order_by(IntentClassification.created_at.desc()).limit(50).all()
    
    for classification in low_confidence:
        intake_event = db.query(IntakeEvent).filter(
            IntakeEvent.id == classification.intake_event_id
        ).first()
        if intake_event:
            alerts.append({
                "type": "low_confidence",
                "severity": "medium",
                "intake_event_id": str(intake_event.id),
                "from_email": intake_event.from_email,
                "confidence": classification.confidence,
                "intent": classification.intent.value,
                "created_at": classification.created_at.isoformat()
            })
    
    # Sort by severity and created_at
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda x: (severity_order.get(x["severity"], 99), x["created_at"]), reverse=True)
    
    return {
        "alerts": alerts[:100]  # Limit to top 100
    }


@router.patch("/cases/{case_id}")
async def update_case(
    case_id: uuid.UUID,
    request: CaseUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update case (ops only)"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    changes = []
    
    if request.status:
        try:
            old_status = case.status.value
            case.status = CaseStatus(request.status)
            changes.append(f"status: {old_status} -> {request.status}")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    if request.priority:
        try:
            old_priority = case.priority.value
            case.priority = CasePriority(request.priority)
            changes.append(f"priority: {old_priority} -> {request.priority}")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {request.priority}")
    
    if request.owner_identity_id:
        old_owner = str(case.owner_identity_id) if case.owner_identity_id else None
        case.owner_identity_id = request.owner_identity_id
        changes.append(f"owner: {old_owner} -> {request.owner_identity_id}")
    
    case.updated_at = datetime.utcnow()
    db.commit()
    
    # Log audit
    from app.services.audit_service import log_audit_event
    log_audit_event(
        db,
        event_type="case_updated_by_ops",
        case_id=case_id,
        payload={
            "changes": changes,
            "internal_notes": request.internal_notes
        }
    )
    
    return {
        "case_id": str(case_id),
        "changes": changes,
        "status": case.status.value,
        "priority": case.priority.value
    }

