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
from app.models.audit import AuditEvent
from app.models.support_ai_log import SupportAILog
from app.services.sla_service import get_sla_policy, get_default_sla_policy

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
        
        # Check SLA breaches and calculate remaining
        breach_events = db.query(SLAEvent).filter(
            and_(
                SLAEvent.case_id == case.id,
                SLAEvent.event_type.in_([SLAEventType.BREACHED_FIRST_RESPONSE, SLAEventType.BREACHED_RESOLUTION])
            )
        ).all()
        
        sla_breached = len(breach_events) > 0
        sla_remaining = None
        
        if not sla_breached:
            # Get tenant and tier
            tenant = db.query(Tenant).filter(Tenant.id == case.tenant_id).first()
            if tenant:
                # Get SLA policy
                policy = get_sla_policy(db, case.tenant_id, tenant.plan_tier)
                if policy:
                    resolution_minutes = policy.resolution_minutes
                else:
                    defaults = get_default_sla_policy(tenant.plan_tier)
                    resolution_minutes = defaults["resolution"]
                
                # Calculate remaining time
                now = datetime.utcnow()
                case_age = now - case.created_at
                age_minutes = case_age.total_seconds() / 60
                
                if age_minutes < resolution_minutes:
                    remaining_minutes = resolution_minutes - age_minutes
                    sla_remaining = (remaining_minutes / resolution_minutes) * 100
                else:
                    sla_remaining = 0
        
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
            "sla_breached": sla_breached,
            "sla_remaining": round(sla_remaining, 1) if sla_remaining is not None else None,
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


@router.get("/cases/{case_id}")
async def get_ops_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get full case details for ops center"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get messages
    messages = db.query(CaseMessage).filter(
        CaseMessage.case_id == case_id
    ).order_by(CaseMessage.created_at).all()
    
    # Get AI artifacts
    ai_artifacts = db.query(AIArtifact).filter(
        AIArtifact.case_id == case_id
    ).order_by(AIArtifact.created_at).all()
    
    # Get SLA events
    sla_events = db.query(SLAEvent).filter(
        SLAEvent.case_id == case_id
    ).order_by(SLAEvent.created_at).all()
    
    # Calculate SLA remaining
    sla_remaining = None
    sla_breached = any(
        event.event_type in [SLAEventType.BREACHED_FIRST_RESPONSE, SLAEventType.BREACHED_RESOLUTION]
        for event in sla_events
    )
    
    if not sla_breached:
        # Get tenant and tier
        tenant = db.query(Tenant).filter(Tenant.id == case.tenant_id).first()
        if tenant:
            # Get SLA policy
            policy = get_sla_policy(db, case.tenant_id, tenant.plan_tier)
            if policy:
                resolution_minutes = policy.resolution_minutes
            else:
                defaults = get_default_sla_policy(tenant.plan_tier)
                resolution_minutes = defaults["resolution"]
            
            # Calculate remaining time
            now = datetime.utcnow()
            case_age = now - case.created_at
            age_minutes = case_age.total_seconds() / 60
            
            if age_minutes < resolution_minutes:
                remaining_minutes = resolution_minutes - age_minutes
                sla_remaining = (remaining_minutes / resolution_minutes) * 100
            else:
                sla_remaining = 0
    
    return {
        "id": str(case.id),
        "tenant_id": str(case.tenant_id),
        "title": case.title,
        "status": case.status.value,
        "priority": case.priority.value,
        "category": case.category.value,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat(),
        "owner_identity_id": str(case.owner_identity_id) if case.owner_identity_id else None,
        "messages": [
            {
                "id": str(msg.id),
                "sender_type": msg.sender_type.value,
                "sender_email": msg.sender_email,
                "body_text": msg.body_text,
                "attachments": msg.attachments,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ],
        "ai_artifacts": [
            {
                "id": str(artifact.id),
                "artifact_type": artifact.artifact_type.value,
                "content": artifact.content,
                "citations": artifact.citations,
                "confidence": artifact.confidence,
                "model_used": artifact.model_used,
                "created_at": artifact.created_at.isoformat()
            }
            for artifact in ai_artifacts
        ],
        "sla_breached": sla_breached,
        "sla_remaining": sla_remaining
    }


@router.get("/cases/{case_id}/audit")
async def get_ops_case_audit(
    case_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get audit trail for a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    audit_events = db.query(AuditEvent).filter(
        AuditEvent.case_id == case_id
    ).order_by(AuditEvent.created_at).all()
    
    return [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at.isoformat()
        }
        for event in audit_events
    ]


@router.get("/metrics/ai-confidence")
async def get_ai_confidence_metrics(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get AI confidence metrics"""
    start_time = datetime.utcnow() - timedelta(days=days)
    
    # Get all AI artifacts with confidence scores in the time window
    artifacts = db.query(AIArtifact).filter(
        and_(
            AIArtifact.created_at >= start_time,
            AIArtifact.confidence.isnot(None)
        )
    ).all()
    
    if not artifacts:
        return {
            "rolling_average": 0.0,
            "sample_size": 0,
            "trend": "stable",
            "time_window_days": days
        }
    
    # Calculate rolling average
    confidences = [a.confidence for a in artifacts if a.confidence is not None]
    rolling_average = sum(confidences) / len(confidences) if confidences else 0.0
    
    # Calculate trend (compare first half vs second half)
    sample_size = len(confidences)
    trend = "stable"
    
    if sample_size >= 10:
        midpoint = sample_size // 2
        first_half_avg = sum(confidences[:midpoint]) / midpoint if midpoint > 0 else 0.0
        second_half_avg = sum(confidences[midpoint:]) / (sample_size - midpoint) if (sample_size - midpoint) > 0 else 0.0
        
        diff = second_half_avg - first_half_avg
        if diff > 0.05:
            trend = "improving"
        elif diff < -0.05:
            trend = "declining"
    
    return {
        "rolling_average": round(rolling_average, 3),
        "sample_size": sample_size,
        "trend": trend,
        "time_window_days": days,
        "min_confidence": round(min(confidences), 3) if confidences else None,
        "max_confidence": round(max(confidences), 3) if confidences else None
    }


@router.get("/ai-logs")
async def get_support_ai_logs(
    tenant_id: Optional[uuid.UUID] = Query(None),
    case_id: Optional[uuid.UUID] = Query(None),
    resolved: Optional[bool] = Query(None),
    helpful: Optional[bool] = Query(None),
    min_confidence: Optional[float] = Query(None),
    used_in_training: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get support AI logs with filters"""
    query = db.query(SupportAILog)
    
    if tenant_id:
        query = query.filter(SupportAILog.tenant_id == tenant_id)
    if case_id:
        query = query.filter(SupportAILog.case_id == case_id)
    if resolved is not None:
        query = query.filter(SupportAILog.resolved == resolved)
    if helpful is not None:
        query = query.filter(SupportAILog.helpful == helpful)
    if min_confidence is not None:
        query = query.filter(SupportAILog.confidence >= min_confidence)
    if used_in_training is not None:
        query = query.filter(SupportAILog.used_in_training == used_in_training)
    
    total = query.count()
    logs = query.order_by(SupportAILog.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": str(log.id),
                "tenant_id": str(log.tenant_id),
                "case_id": str(log.case_id) if log.case_id else None,
                "message": log.message,
                "subject": log.subject,
                "ai_answer": log.ai_answer,
                "confidence": log.confidence,
                "resolved": log.resolved,
                "follow_up_flag": log.follow_up_flag,
                "escalation_triggered": log.escalation_triggered,
                "attempt_number": log.attempt_number,
                "citations": log.citations,
                "context_docs": log.context_docs,
                "user_feedback": log.user_feedback,
                "helpful": log.helpful,
                "model_used": log.model_used,
                "tier": log.tier,
                "kb_document_id": log.kb_document_id,
                "used_in_training": log.used_in_training,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }

