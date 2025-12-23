"""
Cases API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.case import Case, CaseStatus, CasePriority, CaseCategory, CaseMessage, SenderType
from app.models.ai import AIArtifact, ArtifactType
from app.models.audit import AuditEvent
from app.services.ai_client import get_ai_client
from app.services.audit_service import log_audit_event
from sqlalchemy import func

router = APIRouter()


class CaseCreateRequest(BaseModel):
    tenant_id: uuid.UUID
    title: str
    category: str
    priority: Optional[str] = "normal"
    created_by_email: EmailStr
    description: str
    attachments: Optional[List[Dict[str, str]]] = None


class CaseMessageCreateRequest(BaseModel):
    sender_email: EmailStr
    body_text: str
    attachments: Optional[List[Dict[str, str]]] = None


class CaseResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    status: str
    priority: str
    category: str
    created_at: datetime
    updated_at: datetime
    messages_count: int
    
    class Config:
        from_attributes = True


class CaseMessageResponse(BaseModel):
    id: uuid.UUID
    sender_type: str
    sender_email: str
    body_text: str
    attachments: Optional[List[Dict[str, str]]]
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=CaseResponse)
async def create_case(
    request: CaseCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new case"""
    # Map priority and category
    priority_map = {
        "low": CasePriority.LOW,
        "normal": CasePriority.NORMAL,
        "high": CasePriority.HIGH,
        "critical": CasePriority.CRITICAL
    }
    priority = priority_map.get(request.priority.lower(), CasePriority.NORMAL)
    
    category_map = {
        "support": CaseCategory.SUPPORT,
        "onboarding": CaseCategory.ONBOARDING,
        "billing": CaseCategory.BILLING,
        "compliance": CaseCategory.COMPLIANCE,
        "outage": CaseCategory.OUTAGE
    }
    category = category_map.get(request.category.lower(), CaseCategory.SUPPORT)
    
    case = Case(
        tenant_id=request.tenant_id,
        title=request.title,
        status=CaseStatus.NEW,
        priority=priority,
        category=category
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Create initial message
    case_message = CaseMessage(
        case_id=case.id,
        sender_type=SenderType.CUSTOMER,
        sender_email=request.created_by_email,
        body_text=request.description,
        attachments=request.attachments
    )
    db.add(case_message)
    db.commit()
    
    # Log audit
    log_audit_event(
        db,
        event_type="case_created",
        case_id=case.id,
        payload={"title": request.title, "category": request.category}
    )
    
    return CaseResponse(
        id=case.id,
        tenant_id=case.tenant_id,
        title=case.title,
        status=case.status.value,
        priority=case.priority.value,
        category=case.category.value,
        created_at=case.created_at,
        updated_at=case.updated_at,
        messages_count=1
    )


@router.get("/{case_id}", response_model=Dict[str, Any])
async def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get case details"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    messages = db.query(CaseMessage).filter(CaseMessage.case_id == case_id).order_by(CaseMessage.created_at).all()
    ai_artifacts = db.query(AIArtifact).filter(AIArtifact.case_id == case_id).all()
    
    return {
        "id": str(case.id),
        "tenant_id": str(case.tenant_id),
        "title": case.title,
        "status": case.status.value,
        "priority": case.priority.value,
        "category": case.category.value,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat(),
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
                "created_at": artifact.created_at.isoformat()
            }
            for artifact in ai_artifacts
        ]
    }


@router.post("/{case_id}/messages", response_model=CaseMessageResponse)
async def create_case_message(
    case_id: uuid.UUID,
    request: CaseMessageCreateRequest,
    db: Session = Depends(get_db)
):
    """Add a message to a case thread"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Determine sender type (simplified - in production, use auth)
    sender_type = SenderType.CUSTOMER  # Default, should be determined from auth context
    
    case_message = CaseMessage(
        case_id=case_id,
        sender_type=sender_type,
        sender_email=request.sender_email,
        body_text=request.body_text,
        attachments=request.attachments
    )
    db.add(case_message)
    
    # Update case status if needed
    if case.status == CaseStatus.PENDING_CUSTOMER:
        case.status = CaseStatus.OPEN
    case.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(case_message)
    
    # Log audit
    log_audit_event(
        db,
        event_type="case_message_added",
        case_id=case_id,
        payload={"message_id": str(case_message.id)}
    )
    
    return CaseMessageResponse(
        id=case_message.id,
        sender_type=case_message.sender_type.value,
        sender_email=case_message.sender_email,
        body_text=case_message.body_text,
        attachments=case_message.attachments,
        created_at=case_message.created_at
    )


@router.get("/{case_id}/audit")
async def get_case_audit(
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
    
    return {
        "case_id": str(case_id),
        "audit_events": [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "payload": event.payload,
                "created_at": event.created_at.isoformat()
            }
            for event in audit_events
        ]
    }


@router.post("/{case_id}/ai/summary")
async def generate_case_summary(
    case_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Generate AI summary for a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    messages = db.query(CaseMessage).filter(CaseMessage.case_id == case_id).order_by(CaseMessage.created_at).all()
    
    case_messages = [
        {
            "sender": msg.sender_email,
            "body": msg.body_text,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]
    
    ai_client = get_ai_client()
    ai_response = await ai_client.generate_response(
        case_id=str(case.id),
        case_title=case.title,
        case_messages=case_messages
    )
    
    # Store AI artifact
    ai_artifact = AIArtifact(
        case_id=case.id,
        artifact_type=ArtifactType.SUMMARY,
        content=ai_response["summary"],
        confidence=ai_response["confidence"],
        model_used=ai_response["model_used"]
    )
    db.add(ai_artifact)
    db.commit()
    
    return {
        "summary": ai_response["summary"],
        "suggested_next_steps": ai_response["suggested_next_steps"],
        "confidence": ai_response["confidence"],
        "artifact_id": str(ai_artifact.id)
    }


@router.post("/{case_id}/ai/draft-reply")
async def generate_draft_reply(
    case_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Generate draft reply for a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    messages = db.query(CaseMessage).filter(CaseMessage.case_id == case_id).order_by(CaseMessage.created_at).all()
    
    case_messages = [
        {
            "sender": msg.sender_email,
            "body": msg.body_text,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]
    
    ai_client = get_ai_client()
    ai_response = await ai_client.generate_response(
        case_id=str(case.id),
        case_title=case.title,
        case_messages=case_messages
    )
    
    # Store AI artifact
    ai_artifact = AIArtifact(
        case_id=case.id,
        artifact_type=ArtifactType.DRAFT_REPLY,
        content=ai_response["draft_response"],
        confidence=ai_response["confidence"],
        model_used=ai_response["model_used"]
    )
    db.add(ai_artifact)
    db.commit()
    
    return {
        "draft_response": ai_response["draft_response"],
        "confidence": ai_response["confidence"],
        "artifact_id": str(ai_artifact.id)
    }

