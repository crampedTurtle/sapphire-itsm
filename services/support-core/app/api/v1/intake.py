"""
Intake API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.intake import IntakeEvent, IntakeSource, IntentClassification
from app.models.case import Case, CaseStatus, CasePriority, CaseCategory, CaseMessage, SenderType
from app.models.ai import AIArtifact, ArtifactType
from app.models.crm import CRMEvent, CRMEventType
from app.models.tenant import Tenant
from app.services.ai_client import get_ai_client
from app.services.tenant_service import resolve_tenant_by_domain, get_or_create_prospect_tenant, get_tenant_tier, get_or_create_identity
from app.services.audit_service import log_audit_event
from app.services.sla_service import start_sla_tracking
from app.models.tenant import PlanTier
from app.models.intake import Intent, Urgency, RecommendedAction

router = APIRouter()


class EmailIntakeRequest(BaseModel):
    from_email: EmailStr
    to_email: EmailStr
    subject: Optional[str] = None
    body_text: str
    raw_payload: Optional[Dict[str, Any]] = None


class PortalIntakeRequest(BaseModel):
    tenant_id: Optional[uuid.UUID] = None
    from_email: EmailStr
    category: str
    title: str
    description: str
    priority: Optional[str] = "normal"
    attachments: Optional[list] = None


@router.post("/email")
async def intake_email(
    request: EmailIntakeRequest,
    db: Session = Depends(get_db)
):
    """
    Process email intake from n8n
    
    Flow:
    1. Resolve tenant by domain
    2. Create intake event
    3. Classify intent with AI
    4. Route based on intent and tier
    """
    # Resolve tenant
    tenant = resolve_tenant_by_domain(db, request.from_email)
    if not tenant:
        tenant = get_or_create_prospect_tenant(db)
    
    # Create intake event
    intake_event = IntakeEvent(
        source=IntakeSource.EMAIL,
        tenant_id=tenant.id,
        from_email=request.from_email,
        subject=request.subject,
        body_text=request.body_text,
        raw_payload=request.raw_payload
    )
    db.add(intake_event)
    db.commit()
    db.refresh(intake_event)
    
    # Classify intent
    ai_client = get_ai_client()
    classification_result = await ai_client.classify_intent(
        subject=request.subject,
        body_text=request.body_text,
        from_email=request.from_email
    )
    
    # Store classification
    intent_classification = IntentClassification(
        intake_event_id=intake_event.id,
        intent=classification_result["intent"],
        urgency=classification_result["urgency"],
        confidence=classification_result["confidence"],
        compliance_flag=classification_result["compliance_flag"],
        recommended_action=classification_result["recommended_action"],
        model_used=classification_result["model_used"]
    )
    db.add(intent_classification)
    db.commit()
    
    # Log audit
    log_audit_event(
        db,
        event_type="intake_email_received",
        intake_event_id=intake_event.id,
        payload={"from_email": request.from_email, "intent": classification_result["intent"].value}
    )
    
    # Route based on intent and tier
    tier = get_tenant_tier(db, str(tenant.id))
    intent = classification_result["intent"]
    action = classification_result["recommended_action"]
    
    response_payload = {
        "intake_event_id": str(intake_event.id),
        "intent": intent.value,
        "confidence": classification_result["confidence"],
        "compliance_flag": classification_result["compliance_flag"],
        "action_taken": None,
        "case_id": None,
        "email_response": None
    }
    
    # Sales routing
    if intent == Intent.SALES:
        # Create CRM event
        crm_event = CRMEvent(
            tenant_id=tenant.id if tenant.name != "Prospect" else None,
            event_type=CRMEventType.LEAD_CREATED.value,
            payload={
                "email": request.from_email,
                "subject": request.subject,
                "body": request.body_text[:500]
            }
        )
        db.add(crm_event)
        db.commit()
        
        response_payload["action_taken"] = "crm_event_created"
        response_payload["email_response"] = {
            "to": request.from_email,
            "subject": f"Re: {request.subject or 'Your inquiry'}",
            "body": "Thank you for your interest in Sapphire Legal AI. Our sales team will reach out to you shortly."
        }
    
    # Support routing - Tier 0 self-service
    elif intent == Intent.SUPPORT and tier == PlanTier.TIER0:
        # Generate KB answer
        from app.services.outline_client import get_outline_client
        outline_client = get_outline_client()
        kb_results = await outline_client.search(request.body_text[:200], limit=3)
        
        kb_answer = await ai_client.kb_answer_with_citations(
            question=request.body_text,
            kb_context=kb_results
        )
        
        # Store AI artifact
        ai_artifact = AIArtifact(
            intake_event_id=intake_event.id,
            artifact_type=ArtifactType.KB_ANSWER,
            content=kb_answer["answer"],
            citations=kb_answer["citations"],
            confidence=kb_answer["confidence"],
            model_used=kb_answer["model_used"]
        )
        db.add(ai_artifact)
        db.commit()
        
        # Build response with citations
        citations_text = "\n\nRelevant resources:\n"
        for citation in kb_answer["citations"]:
            citations_text += f"- {citation.get('title', 'Resource')}: {citation.get('url', '')}\n"
        
        response_payload["action_taken"] = "self_service_response"
        response_payload["email_response"] = {
            "to": request.from_email,
            "subject": f"Re: {request.subject or 'Your question'}",
            "body": f"{kb_answer['answer']}\n\n{citations_text}\n\nFor more help, visit our portal: http://portal.sapphire.ai"
        }
    
    # Support routing - Tier 1/2 create case
    elif intent == Intent.SUPPORT and tier in [PlanTier.TIER1, PlanTier.TIER2]:
        # Get or create identity
        identity = get_or_create_identity(db, str(tenant.id), request.from_email)
        
        # Determine priority
        priority_map = {
            Urgency.LOW: CasePriority.LOW,
            Urgency.NORMAL: CasePriority.NORMAL,
            Urgency.HIGH: CasePriority.HIGH,
            Urgency.CRITICAL: CasePriority.CRITICAL
        }
        priority = priority_map.get(classification_result["urgency"], CasePriority.NORMAL)
        
        # Determine status
        status = CaseStatus.ESCALATED if classification_result["compliance_flag"] or classification_result["urgency"] == Urgency.CRITICAL else CaseStatus.NEW
        
        # Create case
        case = Case(
            tenant_id=tenant.id,
            title=request.subject or f"Support request from {request.from_email}",
            status=status,
            priority=priority,
            category=CaseCategory.SUPPORT,
            created_by_identity_id=identity.id
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        # Create initial message
        case_message = CaseMessage(
            case_id=case.id,
            sender_type=SenderType.CUSTOMER,
            sender_email=request.from_email,
            body_text=request.body_text
        )
        db.add(case_message)
        db.commit()
        
        # Generate AI summary and draft
        ai_response = await ai_client.generate_response(
            case_id=str(case.id),
            case_title=case.title,
            case_messages=[{"sender": request.from_email, "body": request.body_text}]
        )
        
        # Store AI artifacts
        summary_artifact = AIArtifact(
            case_id=case.id,
            artifact_type=ArtifactType.SUMMARY,
            content=ai_response["summary"],
            confidence=ai_response["confidence"],
            model_used=ai_response["model_used"]
        )
        db.add(summary_artifact)
        
        draft_artifact = AIArtifact(
            case_id=case.id,
            artifact_type=ArtifactType.DRAFT_REPLY,
            content=ai_response["draft_response"],
            confidence=ai_response["confidence"],
            model_used=ai_response["model_used"]
        )
        db.add(draft_artifact)
        db.commit()
        
        # Start SLA tracking
        start_sla_tracking(db, case.id)
        
        # Log audit
        log_audit_event(
            db,
            event_type="case_created_from_intake",
            case_id=case.id,
            intake_event_id=intake_event.id
        )
        
        response_payload["action_taken"] = "case_created"
        response_payload["case_id"] = str(case.id)
        response_payload["email_response"] = {
            "to": request.from_email,
            "subject": f"Case #{case.id.hex[:8]} - {case.title}",
            "body": f"Your support case has been created. Case ID: {case.id.hex[:8]}\n\nView status: http://portal.sapphire.ai/cases/{case.id}"
        }
    
    # Compliance/needs review
    elif classification_result["compliance_flag"] or action == RecommendedAction.NEEDS_REVIEW:
        response_payload["action_taken"] = "flagged_for_review"
        response_payload["email_response"] = {
            "to": request.from_email,
            "subject": f"Re: {request.subject or 'Your inquiry'}",
            "body": "Thank you for contacting us. We've received your message and will review it shortly."
        }
    
    return response_payload


@router.post("/portal")
async def intake_portal(
    request: PortalIntakeRequest,
    db: Session = Depends(get_db)
):
    """
    Process structured portal intake
    """
    # Resolve tenant - either from tenant_id or from email domain
    if request.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == request.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
    else:
        # Try to resolve tenant from email domain
        tenant = resolve_tenant_by_domain(db, request.from_email)
        if not tenant:
            # Create a prospect tenant if none exists
            tenant = get_or_create_prospect_tenant(db)
    
    tier = get_tenant_tier(db, str(tenant.id))
    if tier == PlanTier.TIER0:
        raise HTTPException(status_code=403, detail="Tier 0 customers cannot create cases via portal")
    
    # Get or create identity
    identity = get_or_create_identity(db, str(tenant.id), request.from_email)
    
    # Map priority
    priority_map = {
        "low": CasePriority.LOW,
        "normal": CasePriority.NORMAL,
        "high": CasePriority.HIGH,
        "critical": CasePriority.CRITICAL
    }
    priority = priority_map.get(request.priority.lower(), CasePriority.NORMAL)
    
    # Map category
    category_map = {
        "support": CaseCategory.SUPPORT,
        "onboarding": CaseCategory.ONBOARDING,
        "billing": CaseCategory.BILLING,
        "compliance": CaseCategory.COMPLIANCE,
        "outage": CaseCategory.OUTAGE
    }
    category = category_map.get(request.category.lower(), CaseCategory.SUPPORT)
    
    # Create case
    case = Case(
        tenant_id=tenant.id,
        title=request.title,
        status=CaseStatus.NEW,
        priority=priority,
        category=category,
        created_by_identity_id=identity.id
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Create initial message
    case_message = CaseMessage(
        case_id=case.id,
        sender_type=SenderType.CUSTOMER,
        sender_email=request.from_email,
        body_text=request.description,
        attachments=request.attachments
    )
    db.add(case_message)
    db.commit()
    
    # Generate AI summary
    ai_client = get_ai_client()
    ai_response = await ai_client.generate_response(
        case_id=str(case.id),
        case_title=case.title,
        case_messages=[{"sender": request.from_email, "body": request.description}]
    )
    
    # Store AI artifacts
    summary_artifact = AIArtifact(
        case_id=case.id,
        artifact_type=ArtifactType.SUMMARY,
        content=ai_response["summary"],
        confidence=ai_response["confidence"],
        model_used=ai_response["model_used"]
    )
    db.add(summary_artifact)
    db.commit()
    
    # Start SLA tracking
    start_sla_tracking(db, case.id)
    
    # Log audit
    log_audit_event(
        db,
        event_type="case_created_from_portal",
        case_id=case.id
    )
    
    return {
        "case_id": str(case.id),
        "status": case.status.value,
        "title": case.title
    }


@router.post("/{intake_event_id}/classify")
async def classify_intake(
    intake_event_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Re-classify an intake event (for manual review/retry)
    """
    intake_event = db.query(IntakeEvent).filter(IntakeEvent.id == intake_event_id).first()
    if not intake_event:
        raise HTTPException(status_code=404, detail="Intake event not found")
    
    ai_client = get_ai_client()
    classification_result = await ai_client.classify_intent(
        subject=intake_event.subject,
        body_text=intake_event.body_text,
        from_email=intake_event.from_email
    )
    
    # Store new classification
    intent_classification = IntentClassification(
        intake_event_id=intake_event.id,
        intent=classification_result["intent"],
        urgency=classification_result["urgency"],
        confidence=classification_result["confidence"],
        compliance_flag=classification_result["compliance_flag"],
        recommended_action=classification_result["recommended_action"],
        model_used=classification_result["model_used"]
    )
    db.add(intent_classification)
    db.commit()
    
    return {
        "intent": classification_result["intent"].value,
        "urgency": classification_result["urgency"].value,
        "confidence": classification_result["confidence"],
        "compliance_flag": classification_result["compliance_flag"],
        "recommended_action": classification_result["recommended_action"].value
    }

