"""
Onboarding and Tier Lifecycle API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid

from app.core.database import get_db
from app.models.onboarding import OnboardingSession, OnboardingStep, TenantEntitlement, OnboardingPhase, OnboardingStatus, OnboardingTrigger
from app.models.tenant import PlanTier
from app.services.onboarding_service import (
    start_onboarding,
    advance_onboarding_step,
    pause_onboarding,
    resume_onboarding,
    complete_onboarding,
    upgrade_tier,
)

router = APIRouter()


class StartOnboardingRequest(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    primary_domain: Optional[str] = None
    plan_tier: str  # tier0, tier1, tier2
    aws_environment: Optional[Dict[str, Any]] = None
    trigger_source: str  # supabase_registration, tier_upgrade, manual_restart


class AdvanceStepRequest(BaseModel):
    tenant_id: uuid.UUID
    step_key: str
    metadata: Optional[Dict[str, Any]] = None


class PauseResumeRequest(BaseModel):
    tenant_id: uuid.UUID
    reason: Optional[str] = None


class CompleteOnboardingRequest(BaseModel):
    tenant_id: uuid.UUID


class UpgradeTierRequest(BaseModel):
    tenant_id: uuid.UUID
    previous_tier: str
    new_tier: str
    trigger_source: str


@router.post("/start")
async def start_onboarding_endpoint(
    request: StartOnboardingRequest,
    db: Session = Depends(get_db)
):
    """
    Start onboarding session (idempotent)
    Called by n8n after Supabase detects a new tenant
    """
    try:
        plan_tier = PlanTier(request.plan_tier.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan_tier: {request.plan_tier}")
    
    try:
        trigger = OnboardingTrigger(request.trigger_source.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trigger_source: {request.trigger_source}")
    
    session = start_onboarding(
        db,
        request.tenant_id,
        request.tenant_name,
        request.primary_domain,
        plan_tier,
        trigger
    )
    
    return {
        "onboarding_session_id": str(session.id),
        "status": session.status.value,
        "current_phase": session.current_phase.value
    }


@router.get("/status/{tenant_id}")
async def get_onboarding_status(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get onboarding status for a tenant
    Used by Ops Center and Portal
    """
    session = db.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == tenant_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get all steps for current phase
    steps = db.query(OnboardingStep).filter(
        OnboardingStep.onboarding_session_id == session.id,
        OnboardingStep.phase == session.current_phase
    ).all()
    
    return {
        "tenant_id": str(tenant_id),
        "plan_tier": tenant.plan_tier.value,
        "status": session.status.value,
        "current_phase": session.current_phase.value,
        "steps": [
            {
                "phase": step.phase.value,
                "step_key": step.step_key,
                "step_label": step.step_label,
                "completed": step.completed,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "metadata": step.step_metadata
            }
            for step in steps
        ],
        "started_at": session.started_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None
    }


@router.post("/advance-step")
async def advance_step_endpoint(
    request: AdvanceStepRequest,
    db: Session = Depends(get_db)
):
    """
    Advance onboarding step (idempotent)
    Called automatically by Portal or n8n
    """
    success = advance_onboarding_step(
        db,
        request.tenant_id,
        request.step_key,
        request.metadata
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Onboarding session or step not found")
    
    return {"status": "success", "step_key": request.step_key}


@router.post("/pause")
async def pause_onboarding_endpoint(
    request: PauseResumeRequest,
    db: Session = Depends(get_db)
):
    """
    Pause onboarding session
    Ops-only control
    """
    success = pause_onboarding(
        db,
        request.tenant_id,
        request.reason or "No reason provided"
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    
    return {"status": "paused"}


@router.post("/resume")
async def resume_onboarding_endpoint(
    request: PauseResumeRequest,
    db: Session = Depends(get_db)
):
    """
    Resume onboarding session
    Ops-only control
    """
    success = resume_onboarding(
        db,
        request.tenant_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Onboarding session not found or not paused")
    
    return {"status": "resumed"}


@router.post("/complete")
async def complete_onboarding_endpoint(
    request: CompleteOnboardingRequest,
    db: Session = Depends(get_db)
):
    """
    Complete onboarding session
    Called automatically when Phase 3 completes
    """
    success = complete_onboarding(
        db,
        request.tenant_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    
    return {"status": "completed"}


@router.post("/upgrade")
async def upgrade_tier_endpoint(
    request: UpgradeTierRequest,
    db: Session = Depends(get_db)
):
    """
    Upgrade or downgrade tenant tier
    Triggered by Supabase record change
    """
    try:
        previous_tier = PlanTier(request.previous_tier.lower())
        new_tier = PlanTier(request.new_tier.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {str(e)}")
    
    try:
        trigger = OnboardingTrigger(request.trigger_source.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trigger_source: {request.trigger_source}")
    
    success = upgrade_tier(
        db,
        request.tenant_id,
        previous_tier,
        new_tier,
        trigger
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {
        "status": "success",
        "previous_tier": previous_tier.value,
        "new_tier": new_tier.value
    }

