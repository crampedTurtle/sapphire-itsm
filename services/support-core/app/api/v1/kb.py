"""
KB Review Queue and Management API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.kb_article import KBQualityScore, KBArticleIndex, KBArticleRevision
from app.services.kb_quality_evaluator import KBQualityEvaluator

router = APIRouter()


class ReviewQueueItem(BaseModel):
    outline_document_id: str
    title: str
    overall_score: int
    clarity_score: int
    completeness_score: int
    technical_accuracy_score: int
    structure_score: int
    needs_review: bool
    reason: Optional[str]
    created_at: str
    quality_score_id: str


class ApproveRequest(BaseModel):
    reviewed_by: str
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    reviewed_by: str
    reason: str
    disable_article: bool = True


@router.get("/review-queue")
async def get_review_queue(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get list of articles needing review, sorted by overall_score ascending
    """
    scores = db.query(KBQualityScore).filter(
        and_(
            KBQualityScore.needs_review == True,
            KBQualityScore.reviewed == False
        )
    ).order_by(KBQualityScore.overall_score.asc()).limit(limit).all()
    
    items = []
    for score in scores:
        # Get article info
        article = db.query(KBArticleIndex).filter(
            KBArticleIndex.outline_document_id == score.outline_document_id
        ).first()
        
        items.append(ReviewQueueItem(
            outline_document_id=score.outline_document_id,
            title=article.title if article else "Unknown",
            overall_score=score.overall_score,
            clarity_score=score.clarity_score,
            completeness_score=score.completeness_score,
            technical_accuracy_score=score.technical_accuracy_score,
            structure_score=score.structure_score,
            needs_review=score.needs_review,
            reason=score.reason,
            created_at=score.created_at.isoformat(),
            quality_score_id=str(score.id)
        ))
    
    return {
        "count": len(items),
        "items": items
    }


@router.post("/review/{outline_document_id}/approve")
async def approve_article(
    outline_document_id: str,
    request: ApproveRequest,
    db: Session = Depends(get_db)
):
    """
    Approve an article - marks latest score as reviewed, needs_review = false
    """
    # Get latest quality score
    score = db.query(KBQualityScore).filter(
        KBQualityScore.outline_document_id == outline_document_id
    ).order_by(KBQualityScore.created_at.desc()).first()
    
    if not score:
        raise HTTPException(status_code=404, detail="Quality score not found")
    
    # Update score
    score.reviewed = True
    score.needs_review = False
    score.reviewed_at = datetime.utcnow()
    score.reviewed_by = request.reviewed_by
    
    # Update article status if needed
    article = db.query(KBArticleIndex).filter(
        KBArticleIndex.outline_document_id == outline_document_id
    ).first()
    
    if article:
        article.is_active = True
    
    db.commit()
    
    return {
        "outline_document_id": outline_document_id,
        "status": "approved",
        "reviewed_by": request.reviewed_by,
        "reviewed_at": score.reviewed_at.isoformat()
    }


@router.post("/review/{outline_document_id}/reject")
async def reject_article(
    outline_document_id: str,
    request: RejectRequest,
    db: Session = Depends(get_db)
):
    """
    Reject an article - logs rejection and optionally disables from RAG
    """
    # Get latest quality score
    score = db.query(KBQualityScore).filter(
        KBQualityScore.outline_document_id == outline_document_id
    ).order_by(KBQualityScore.created_at.desc()).first()
    
    if not score:
        raise HTTPException(status_code=404, detail="Quality score not found")
    
    # Update score
    score.reviewed = True
    score.needs_review = False
    score.reviewed_at = datetime.utcnow()
    score.reviewed_by = request.reviewed_by
    score.reason = f"Rejected: {request.reason}"
    
    # Disable article if requested
    if request.disable_article:
        article = db.query(KBArticleIndex).filter(
            KBArticleIndex.outline_document_id == outline_document_id
        ).first()
        if article:
            article.is_active = False
    
    db.commit()
    
    return {
        "outline_document_id": outline_document_id,
        "status": "rejected",
        "reviewed_by": request.reviewed_by,
        "reviewed_at": score.reviewed_at.isoformat(),
        "disabled": request.disable_article
    }

