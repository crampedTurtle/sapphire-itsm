"""
AI Training Dataset Export API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.services.model_training_dataset import ModelTrainingDataset

router = APIRouter()


@router.get("/training-dataset")
async def get_training_dataset(
    limit: int = Query(500, ge=1, le=1000),
    min_confidence: float = Query(0.75, ge=0.0, le=1.0),
    min_quality_score: int = Query(7, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Export training dataset for model fine-tuning
    
    Returns JSON list of TrainingExample objects
    """
    dataset_builder = ModelTrainingDataset(db)
    
    # Build training batch
    examples = await dataset_builder.build_training_batch(
        limit=limit,
        min_confidence=min_confidence,
        min_quality_score=min_quality_score
    )
    
    # Convert to dict for JSON serialization
    examples_dict = [ex.dict() for ex in examples]
    
    return {
        "format": "json",
        "count": len(examples_dict),
        "examples": examples_dict,
        "exported_at": dataset_builder.export_training_dataset(limit=limit)["exported_at"]
    }


@router.post("/training-dataset/mark-used")
async def mark_training_examples_used(
    log_ids: List[uuid.UUID],
    db: Session = Depends(get_db)
):
    """
    Mark support logs as used in training dataset
    """
    dataset_builder = ModelTrainingDataset(db)
    await dataset_builder.mark_used_for_training(log_ids)
    
    return {
        "marked_count": len(log_ids),
        "status": "success"
    }

