"""
Webhooks for n8n integration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.case import Case
from app.models.crm import CRMEvent, CRMEventType
import httpx

router = APIRouter()


class FreeScoutSyncRequest(BaseModel):
    case_id: uuid.UUID
    action: str  # "create" or "update"
    conversation_data: Optional[Dict[str, Any]] = None


class CRMEmitRequest(BaseModel):
    tenant_id: Optional[uuid.UUID] = None
    event_type: str
    payload: Dict[str, Any]


@router.post("/freescout/sync")
async def freescout_sync(
    request: FreeScoutSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Optional FreeScout sync webhook (called by n8n)
    """
    if not settings.FREESCOUT_ENABLED:
        return {"status": "disabled", "message": "FreeScout integration is disabled"}
    
    case = db.query(Case).filter(Case.id == request.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update case with external reference
    if request.action == "create" and request.conversation_data:
        case.external_source = "freescout"
        case.external_case_id = request.conversation_data.get("conversation_id")
        db.commit()
    
    return {
        "status": "synced",
        "case_id": str(case.id),
        "external_case_id": case.external_case_id
    }


@router.post("/crm/emit")
async def crm_emit(
    request: CRMEmitRequest,
    db: Session = Depends(get_db)
):
    """
    Emit CRM event (called by n8n or internally)
    """
    # Store CRM event
    crm_event = CRMEvent(
        tenant_id=request.tenant_id,
        event_type=request.event_type,
        payload=request.payload
    )
    db.add(crm_event)
    db.commit()
    
    # Optionally forward to external CRM webhook
    if settings.CRM_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    settings.CRM_WEBHOOK_URL,
                    json={
                        "event_type": request.event_type,
                        "tenant_id": str(request.tenant_id) if request.tenant_id else None,
                        "payload": request.payload
                    },
                    timeout=10.0
                )
        except Exception:
            pass  # Don't fail if webhook fails
    
    return {
        "status": "emitted",
        "event_id": str(crm_event.id),
        "event_type": request.event_type
    }

