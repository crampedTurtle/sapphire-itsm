"""
AI-First Support Intake API
Replaces traditional manual ticketing with AI-first resolution
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models.case import Case, CaseStatus, CasePriority, CaseCategory, CaseMessage, SenderType
from app.models.ai import AIArtifact, ArtifactType
from app.models.tenant import Tenant, PlanTier
from app.models.support_ai_log import SupportAILog
from app.services.ai_client import get_ai_client
from app.services.tenant_service import get_tenant_tier, get_or_create_identity
from app.services.audit_service import log_audit_event
from app.services.sla_service import start_sla_tracking
from app.services.support_ai_engine import SupportAIEngine, SupportResponse
from app.services.outline_kb_writer import get_outline_kb_writer
from app.services.kb_update_agent import KBUpdateAgent
from app.services.kb_quality_evaluator import KBQualityEvaluator

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
    tier_level = 0 if tier == PlanTier.TIER0 else (1 if tier == PlanTier.TIER1 else 2)
    
    # Get or create identity
    identity = get_or_create_identity(db, str(tenant.id), request.user_id)
    
    # Initialize AI Engine
    engine = SupportAIEngine(db)
    
    # Step 1: AI Classification
    classification = await engine.classify_intent(
        message=request.message,
        subject=request.subject
    )
    
    # Step 2: Retrieve Context (RAG)
    context = await engine.retrieve_context(
        tenant_id=tenant.id,
        query=f"{request.subject} {request.message}"[:500],
        limit=6
    )
    
    # Step 3: Generate Resolution
    resolution = await engine.generate_resolution(
        context=context,
        message=request.message,
        subject=request.subject,
        tier=tier_level
    )
    
    # Score confidence with heuristics
    final_confidence = engine.score_confidence(resolution)
    resolution.confidence = final_confidence
    
    # Check for previous attempts (for escalation logic)
    previous_attempts = db.query(SupportAILog).filter(
        and_(
            SupportAILog.tenant_id == tenant.id,
            SupportAILog.message.like(f"%{request.message[:50]}%"),  # Similar messages
            SupportAILog.created_at >= datetime.utcnow() - timedelta(hours=24)
        )
    ).count()
    attempt_number = previous_attempts + 1
    
    # Log AI attempt
    ai_log = SupportAILog(
        tenant_id=tenant.id,
        message=request.message,
        subject=request.subject,
        ai_answer=resolution.answer,
        confidence=final_confidence,
        resolved=False,  # Will be updated if auto-resolved
        follow_up_flag=resolution.follow_up_needed,
        escalation_triggered=False,  # Will be updated if escalated
        attempt_number=attempt_number,
        citations=resolution.citations,
        context_docs=[{"type": doc.get("type"), "title": doc.get("title")} for doc in context],
        model_used=classification.get("model_used", "unknown"),
        tier=tier_level
    )
    db.add(ai_log)
    
    # Step 4: Decision Logic
    # Decision thresholds:
    # - confidence >= 0.78 → auto resolve
    # - 0.45 <= confidence < 0.78 → ask follow-up
    # - confidence < 0.45 OR attempts > 2 → escalate/create case
    
    if final_confidence >= 0.78 and not engine.should_escalate(final_confidence, attempt_number):
        # Auto-resolve: Return AI answer without creating case
        ai_log.resolved = True
        
        # KB Update Agent workflow: Find similar, decide, create/update, evaluate quality
        kb_result = None
        kb_document_id = None
        try:
            kb_agent = KBUpdateAgent(db)
            quality_evaluator = KBQualityEvaluator(db)
            
            # Step 1: Find similar articles
            similar_articles = await kb_agent.find_similar_articles(
                tenant_id=tenant.id,
                issue_title=request.subject,
                problem_description=request.message
            )
            
            # Step 2: Decide update vs create
            decision = await kb_agent.decide_update_or_create(
                candidates=similar_articles,
                ai_confidence=final_confidence
            )
            
            # Log decision
            kb_agent.log_decision(
                support_log_id=ai_log.id,
                decision=decision,
                reason=f"Confidence: {final_confidence}, Similarity: {similar_articles[0].get('similarity', 0) if similar_articles else 0}",
                similarity_score={"candidates": similar_articles[:3]} if similar_articles else None
            )
            
            if decision == "create":
                # Generate article content
                kb_writer = get_outline_kb_writer()
                article_content = await kb_writer.generate_article_content(
                    issue_title=request.subject,
                    problem_description=request.message,
                    resolution_steps=resolution.steps,
                    notes=None,
                    related_articles=[a.get("title") for a in similar_articles[:3]] if similar_articles else None
                )
                
                # Create article
                create_result = await kb_agent.create_article(
                    title=request.subject,
                    content=article_content,
                    tenant_level="global",
                    tenant_id=None,
                    tags=["ai-generated", "support-resolution"]
                )
                
                if create_result.success:
                    kb_document_id = create_result.outline_document_id
                    ai_log.kb_document_id = kb_document_id
                    
                    # Evaluate quality
                    quality_result = await quality_evaluator.evaluate_article(
                        markdown_content=article_content,
                        context={"confidence": final_confidence, "decision": "create"}
                    )
                    
                    # Store quality score
                    quality_evaluator.store_quality_score(
                        outline_document_id=kb_document_id,
                        article_id=create_result.article_id,
                        revision_id=None,  # Will be set after revision is created
                        quality_result=quality_result
                    )
                    
                    kb_result = {
                        "kb_created": True,
                        "document_id": kb_document_id,
                        "action": "created",
                        "needs_review": quality_result.needs_review
                    }
            
            elif decision == "update":
                # Get best matching article
                best_match = similar_articles[0] if similar_articles else None
                if best_match:
                    # Generate updated content
                    kb_writer = get_outline_kb_writer()
                    article_content = await kb_writer.generate_article_content(
                        issue_title=request.subject,
                        problem_description=request.message,
                        resolution_steps=resolution.steps,
                        notes=None,
                        related_articles=None
                    )
                    
                    # Update article
                    update_result = await kb_agent.update_article(
                        existing_doc_id=best_match["outline_document_id"],
                        new_content=article_content,
                        new_title=request.subject,
                        merge_strategy="append_variant"
                    )
                    
                    if update_result.success:
                        kb_document_id = update_result.outline_document_id
                        ai_log.kb_document_id = kb_document_id
                        
                        # Evaluate quality of updated article
                        quality_result = await quality_evaluator.evaluate_article(
                            markdown_content=article_content,
                            context={"confidence": final_confidence, "decision": "update"}
                        )
                        
                        # Store quality score
                        article = db.query(KBArticleIndex).filter(
                            KBArticleIndex.outline_document_id == kb_document_id
                        ).first()
                        
                        quality_evaluator.store_quality_score(
                            outline_document_id=kb_document_id,
                            article_id=article.id if article else None,
                            revision_id=None,
                            quality_result=quality_result
                        )
                        
                        kb_result = {
                            "kb_created": True,
                            "document_id": kb_document_id,
                            "action": "updated",
                            "revision_number": update_result.revision_number,
                            "needs_review": quality_result.needs_review
                        }
            
            elif decision == "skip":
                kb_result = {
                    "kb_created": False,
                    "action": "skipped",
                    "reason": "Low confidence or similar article exists"
                }
        except Exception as e:
            # Don't fail the response if KB workflow fails
            import traceback
            print(f"KB workflow error: {traceback.format_exc()}")
            pass
        
        db.commit()
        
        # Log audit
        log_audit_event(
            db,
            event_type="support_ai_auto_resolved",
            tenant_id=tenant.id,
            payload={
                "subject": request.subject,
                "confidence": final_confidence,
                "user_id": request.user_id,
                "attempt_number": attempt_number,
                "kb_created": kb_result.get("kb_created", False) if kb_result else False,
                "kb_document_id": kb_result.get("document_id") if kb_result else None,
                "kb_action": kb_result.get("action") if kb_result else None,
                "kb_needs_review": kb_result.get("needs_review", False) if kb_result else False
            }
        )
        
        response_data = {
            "status": "ai_response",
            "confidence": final_confidence,
            "answer": engine.format_resolution(resolution),
            "citations": resolution.citations,
            "steps": resolution.steps,
            "suggest_escalation": False,
            "remediation_steps": resolution.recommended_fix_attempts or []
        }
        
        # Add KB creation info if available
        if kb_result:
            response_data["kb_created"] = kb_result.get("kb_created", False)
            response_data["kb_document_id"] = kb_result.get("document_id")
            response_data["kb_url"] = kb_result.get("url")
        
        return response_data
    
    elif final_confidence >= 0.45 and final_confidence < 0.78:
        # Ask follow-up question
        ai_log.follow_up_flag = True
        db.commit()
        
        return {
            "status": "ai_response",
            "confidence": final_confidence,
            "answer": resolution.answer,
            "citations": resolution.citations,
            "steps": resolution.steps,
            "follow_up_needed": True,
            "clarifying_question": resolution.clarifying_question or "Can you provide more details about this issue?",
            "suggest_escalation": False
        }
    
    else:
        # Low confidence or too many attempts → create case
        ai_log.escalation_triggered = True
        
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
            status=CaseStatus.NEW if final_confidence >= 0.45 else CaseStatus.ESCALATED,
            priority=priority,
            category=category,
            created_by_identity_id=identity.id,
            ai_confidence=final_confidence,
            tier_route=tier_route
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        # Update log with case_id
        ai_log.case_id = case.id
        db.commit()
        
        # Create initial message
        case_message = CaseMessage(
            case_id=case.id,
            sender_type=SenderType.CUSTOMER,
            sender_email=request.user_id,
            body_text=request.message,
            attachments=request.attachments
        )
        db.add(case_message)
        
        # Store AI summary using engine's summarize method
        summary_text = engine.summarize_for_case(resolution)
        summary_artifact = AIArtifact(
            case_id=case.id,
            artifact_type=ArtifactType.SUMMARY,
            content=summary_text,
            citations=resolution.citations,
            confidence=final_confidence,
            model_used=classification.get("model_used", "unknown")
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
                "ai_confidence": final_confidence,
                "tier_route": tier_route,
                "classification": classification["intent"].value,
                "attempt_number": attempt_number
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
            "ai_confidence": final_confidence,
            "ai_attempted_answer": resolution.answer,  # Include for user reference
            "suggest_escalation": final_confidence < 0.45
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

