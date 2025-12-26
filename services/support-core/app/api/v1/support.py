"""
AI-First Support Intake API
Replaces traditional manual ticketing with AI-first resolution
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.case import Case, CaseStatus, CasePriority, CaseCategory, CaseMessage, SenderType
from app.models.ai import AIArtifact, ArtifactType
from app.models.tenant import Tenant, PlanTier
from app.services.ai_client import get_ai_client
from app.services.tenant_service import get_tenant_tier, get_or_create_identity
from app.services.audit_service import log_audit_event
from app.services.sla_service import start_sla_tracking
from app.services.outline_client import get_outline_client

router = APIRouter()


class IntakeRequest(BaseModel):
    tenant_id: Optional[uuid.UUID] = None  # Optional - will be resolved from user_id (email domain) if not provided
    user_id: str  # User identifier (email or ID)
    subject: str
    message: str
    attachments: Optional[List[str]] = None  # File IDs
    category: Optional[str] = None
    priority_requested: Optional[str] = "normal"  # low|normal|high|critical


class EscalateRequest(BaseModel):
    case_id: uuid.UUID
    reason: str


@router.post("/intakeRequest")
async def intake_request(
    request: IntakeRequest,
    db: Session = Depends(get_db)
):
    """
    AI-first support intake endpoint
    
    Flow:
    1. Validate tenant + entitlements (resolve from email if tenant_id not provided)
    2. Run AI classification (intent, topic, urgency)
    3. Attempt AI resolution via KB search + answer generation
    4. If confidence >= 0.78 & user doesn't reject → auto resolve
    5. Else → create case record
    """
    # Resolve tenant - either from tenant_id or from email domain
    if request.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == request.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
    else:
        # Resolve tenant from email domain
        from app.services.tenant_service import resolve_tenant_by_domain, get_or_create_prospect_tenant
        tenant = resolve_tenant_by_domain(db, request.user_id)
        if not tenant:
            tenant = get_or_create_prospect_tenant(db)
    
    tier = get_tenant_tier(db, str(tenant.id))
    
    # Get or create identity
    identity = get_or_create_identity(db, str(tenant.id), request.user_id)
    
    # Step 1: AI Classification
    ai_client = get_ai_client()
    classification = await ai_client.classify_intent(
        subject=request.subject,
        body_text=request.message,
        from_email=request.user_id
    )
    
    # Step 2: Attempt AI Resolution
    outline_client = get_outline_client()
    kb_results = await outline_client.search(request.message[:500], limit=5)
    
    kb_answer = await ai_client.kb_answer_with_citations(
        question=f"{request.subject}\n\n{request.message}",
        kb_context=kb_results
    )
    
    ai_confidence = kb_answer.get("confidence", 0.0)
    ai_answer = kb_answer.get("answer", "")
    citations = kb_answer.get("citations", [])
    
    # Step 3: Determine next action
    # If AI confidence >= 0.78, attempt auto-resolution
    if ai_confidence >= 0.78:
        # Auto-resolve: Return AI answer without creating case
        # Store as AI artifact for analytics
        ai_artifact = AIArtifact(
            tenant_id=tenant.id,
            artifact_type=ArtifactType.KB_ANSWER,
            content=ai_answer,
            citations=citations,
            confidence=ai_confidence,
            model_used=kb_answer.get("model_used", "unknown")
        )
        db.add(ai_artifact)
        db.commit()
        
        # Log audit
        log_audit_event(
            db,
            event_type="support_ai_auto_resolved",
            tenant_id=tenant.id,
            payload={
                "subject": request.subject,
                "confidence": ai_confidence,
                "user_id": request.user_id
            }
        )
        
        return {
            "status": "ai_response",
            "confidence": ai_confidence,
            "answer": ai_answer,
            "citations": citations,
            "suggest_escalation": False,
            "remediation_steps": kb_answer.get("remediation_steps", [])
        }
    
    # Step 4: Create case (AI couldn't resolve with high confidence)
    # Map priority
    priority_map = {
        "low": CasePriority.LOW,
        "normal": CasePriority.NORMAL,
        "high": CasePriority.HIGH,
        "critical": CasePriority.CRITICAL
    }
    priority = priority_map.get(
        request.priority_requested.lower() if request.priority_requested else "normal",
        CasePriority.NORMAL
    )
    
    # Override with AI-determined urgency if higher
    urgency_map = {
        "low": CasePriority.LOW,
        "normal": CasePriority.NORMAL,
        "high": CasePriority.HIGH,
        "critical": CasePriority.CRITICAL
    }
    urgency_value = classification["urgency"].value if hasattr(classification["urgency"], "value") else str(classification["urgency"])
    ai_priority = urgency_map.get(urgency_value, CasePriority.NORMAL)
    # Compare enum values (higher priority = higher enum value)
    priority_values = {CasePriority.LOW: 0, CasePriority.NORMAL: 1, CasePriority.HIGH: 2, CasePriority.CRITICAL: 3}
    if priority_values.get(ai_priority, 1) > priority_values.get(priority, 1):
        priority = ai_priority
    
    # Map category
    category_map = {
        "support": CaseCategory.SUPPORT,
        "onboarding": CaseCategory.ONBOARDING,
        "billing": CaseCategory.BILLING,
        "compliance": CaseCategory.COMPLIANCE,
        "outage": CaseCategory.OUTAGE
    }
    category = category_map.get(
        request.category.lower() if request.category else "support",
        CaseCategory.SUPPORT
    )
    
    # Determine tier route based on tier and urgency
    tier_route = 1  # Default
    if tier == PlanTier.TIER2:
        tier_route = 2
    urgency_value = classification["urgency"].value if hasattr(classification["urgency"], "value") else str(classification["urgency"])
    if urgency_value == "critical" or classification.get("compliance_flag", False):
        tier_route = 2  # Critical/compliance → Tier 2
    
    # Create case
    case = Case(
        tenant_id=tenant.id,
        title=request.subject,
        status=CaseStatus.NEW,
        priority=priority,
        category=category,
        created_by_identity_id=identity.id,
        ai_confidence=ai_confidence,
        tier_route=tier_route
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Create initial message
    case_message = CaseMessage(
        case_id=case.id,
        sender_type=SenderType.CUSTOMER,
        sender_email=request.user_id,
        body_text=request.message,
        attachments=request.attachments
    )
    db.add(case_message)
    
    # Store AI classification and attempted resolution as artifacts
    summary_artifact = AIArtifact(
        case_id=case.id,
        artifact_type=ArtifactType.SUMMARY,
        content=f"AI Classification: {classification['intent'].value}\n\nAI Attempted Resolution:\n{ai_answer}",
        confidence=ai_confidence,
        model_used=kb_answer.get("model_used", "unknown")
    )
    db.add(summary_artifact)
    db.commit()
    
    # Start SLA tracking
    start_sla_tracking(db, case.id)
    
    # Log audit
    log_audit_event(
        db,
        event_type="support_case_created_ai_first",
        case_id=case.id,
        payload={
            "ai_confidence": ai_confidence,
            "tier_route": tier_route,
            "classification": classification["intent"].value
        }
    )
    
    # Determine SLA policy name
    sla_applied = "standard"
    if tier == PlanTier.TIER2:
        sla_applied = "premium"
    elif tier == PlanTier.TIER0:
        sla_applied = "basic"
    
    return {
        "status": "case_created",
        "case_id": str(case.id),
        "tier_route": tier_route,
        "sla_applied": sla_applied,
        "ai_confidence": ai_confidence,
        "ai_attempted_answer": ai_answer,  # Include for user reference
        "suggest_escalation": ai_confidence < 0.5  # Suggest if very low confidence
    }


@router.post("/escalate")
async def escalate_case(
    request: EscalateRequest,
    db: Session = Depends(get_db)
):
    """
    User-requested escalation
    Marks case for escalation and triggers Ops Center visibility
    """
    case = db.query(Case).filter(Case.id == request.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update case status
    old_status = case.status
    case.status = CaseStatus.ESCALATED
    case.updated_at = datetime.utcnow()
    db.commit()
    
    # Log audit
    log_audit_event(
        db,
        event_type="case_escalated_user",
        case_id=case.id,
        payload={
            "reason": request.reason,
            "previous_status": old_status.value
        }
    )
    
    return {
        "case_id": str(case.id),
        "status": "escalated",
        "message": "Case has been escalated to support team"
    }


@router.post("/auto-escalate")
async def auto_escalate(
    case_id: uuid.UUID,
    reason: str,
    db: Session = Depends(get_db)
):
    """
    Internal hook for AI auto-escalation
    Triggered when:
    - AI confidence is low
    - Repeated user dissatisfaction
    - SLA time threshold reached
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update case status
    old_status = case.status
    case.status = CaseStatus.ESCALATED
    case.updated_at = datetime.utcnow()
    db.commit()
    
    # Log audit
    log_audit_event(
        db,
        event_type="case_escalated_auto",
        case_id=case.id,
        payload={
            "reason": reason,
            "previous_status": old_status.value
        }
    )
    
    return {
        "case_id": str(case.id),
        "status": "escalated",
        "reason": reason
    }

