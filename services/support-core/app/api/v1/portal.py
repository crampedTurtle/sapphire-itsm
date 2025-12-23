"""
Portal API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.services.ai_client import get_ai_client
from app.services.outline_client import get_outline_client
from app.models.ai import AIArtifact, ArtifactType

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    tenant_id: Optional[str] = None


@router.post("/ask")
async def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db)
):
    """
    Tier 0 self-service: Ask a question and get KB answer with citations
    """
    outline_client = get_outline_client()
    ai_client = get_ai_client()
    
    # Search Outline KB
    kb_results = await outline_client.search(request.question, limit=5)
    
    # Generate RAG answer with citations
    kb_answer = await ai_client.kb_answer_with_citations(
        question=request.question,
        kb_context=kb_results
    )
    
    # Store AI artifact (optional, for analytics)
    if request.tenant_id:
        try:
            from uuid import UUID
            tenant_uuid = UUID(request.tenant_id)
            ai_artifact = AIArtifact(
                artifact_type=ArtifactType.KB_ANSWER,
                content=kb_answer["answer"],
                citations=kb_answer["citations"],
                confidence=kb_answer["confidence"],
                model_used=kb_answer["model_used"]
            )
            db.add(ai_artifact)
            db.commit()
        except Exception:
            pass  # Don't fail if artifact storage fails
    
    return {
        "answer": kb_answer["answer"],
        "citations": kb_answer["citations"],
        "confidence": kb_answer["confidence"],
        "suggested_actions": [
            "Visit our knowledge base for more information",
            "Open a support case if you need further assistance"
        ] if kb_answer["confidence"] < 0.7 else []
    }

