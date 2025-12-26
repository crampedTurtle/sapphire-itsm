"""
Model Training Dataset Builder
Builds training datasets from resolved support logs for model improvement
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid

from app.models.support_ai_log import SupportAILog
from app.models.kb_article import KBQualityScore, KBArticleIndex


class TrainingExample(BaseModel):
    """Training example schema"""
    tenant_id: str
    issue_title: str
    problem_description: str
    final_answer: str
    citations: List[str]
    kb_document_id: Optional[str]
    category: Optional[str]
    confidence: float
    helpful: Optional[bool]
    quality_score: Optional[int]


class ModelTrainingDataset:
    """Builds training datasets from support logs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def build_training_batch(
        self,
        limit: int = 500,
        min_confidence: float = 0.75,
        min_quality_score: int = 7
    ) -> List[TrainingExample]:
        """
        Selects resolved support logs for training
        
        Criteria:
        - helpful is true OR quality score >= threshold
        - used_in_training is false
        - resolved is true
        - confidence >= min_confidence
        - If kb_document_id exists, article quality >= min_quality_score
        """
        # Build query
        query = self.db.query(SupportAILog).filter(
            and_(
                SupportAILog.resolved == True,
                SupportAILog.used_in_training == False,
                SupportAILog.confidence >= min_confidence,
                or_(
                    SupportAILog.helpful == True,
                    # Include if no helpful feedback but high confidence
                    and_(
                        SupportAILog.helpful.is_(None),
                        SupportAILog.confidence >= 0.85
                    )
                )
            )
        ).limit(limit)
        
        logs = query.all()
        examples = []
        
        for log in logs:
            # Check KB article quality if document exists
            if log.kb_document_id:
                quality_score = self.db.query(KBQualityScore).filter(
                    and_(
                        KBQualityScore.outline_document_id == log.kb_document_id,
                        KBQualityScore.needs_review == False,
                        KBQualityScore.reviewed == True
                    )
                ).order_by(KBQualityScore.created_at.desc()).first()
                
                if quality_score and quality_score.overall_score < min_quality_score:
                    continue  # Skip if quality too low
            
            # Build training example
            citations = []
            if log.citations:
                if isinstance(log.citations, list):
                    citations = [str(c) for c in log.citations]
                elif isinstance(log.citations, dict):
                    citations = [str(v) for v in log.citations.values()]
            
            example = TrainingExample(
                tenant_id=str(log.tenant_id),
                issue_title=log.subject or "Support Request",
                problem_description=log.message,
                final_answer=log.ai_answer,
                citations=citations,
                kb_document_id=log.kb_document_id,
                category=None,  # Could be extracted from case if available
                confidence=log.confidence,
                helpful=log.helpful,
                quality_score=quality_score.overall_score if quality_score else None
            )
            examples.append(example)
        
        return examples
    
    async def mark_used_for_training(self, log_ids: List[uuid.UUID]) -> None:
        """Mark support logs as used in training"""
        self.db.query(SupportAILog).filter(
            SupportAILog.id.in_(log_ids)
        ).update({
            SupportAILog.used_in_training: True
        }, synchronize_session=False)
        self.db.commit()
    
    def export_training_dataset(
        self,
        limit: int = 500,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export training dataset in specified format
        
        Returns:
            {
                "format": "json",
                "count": int,
                "examples": List[TrainingExample],
                "exported_at": datetime
            }
        """
        examples = await self.build_training_batch(limit=limit)
        
        # Convert to dict for JSON serialization
        examples_dict = [ex.dict() for ex in examples]
        
        return {
            "format": format,
            "count": len(examples_dict),
            "examples": examples_dict,
            "exported_at": datetime.utcnow().isoformat()
        }

