"""
Onboarding service - state machine and lifecycle management
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from app.models.onboarding import (
    OnboardingSession, OnboardingStep, TenantEntitlement,
    OnboardingPhase, OnboardingStatus, OnboardingTrigger
)
from app.models.tenant import Tenant, PlanTier
from app.models.sla import SLAPolicy
from app.services.audit_service import log_audit_event


# Onboarding step definitions by phase
ONBOARDING_STEPS = {
    OnboardingPhase.PHASE_0_PROVISIONED: [
        {"step_key": "aws_provisioned", "step_label": "AWS Environment Provisioned"},
        {"step_key": "supabase_ready", "step_label": "Supabase Database Ready"},
    ],
    OnboardingPhase.PHASE_1_FIRST_VALUE: [
        {"step_key": "portal_login", "step_label": "Portal Login"},
        {"step_key": "first_ai_question", "step_label": "First AI Question Asked"},
        {"step_key": "kb_search", "step_label": "Knowledge Base Search"},
    ],
    OnboardingPhase.PHASE_2_CORE_WORKFLOWS: [
        {"step_key": "first_case_created", "step_label": "First Support Case Created"},
        {"step_key": "case_resolved", "step_label": "First Case Resolved"},
        {"step_key": "email_intake", "step_label": "Email Intake Received"},
    ],
    OnboardingPhase.PHASE_3_INDEPENDENT: [
        {"step_key": "multiple_cases", "step_label": "Multiple Cases Handled"},
        {"step_key": "self_service_success", "step_label": "Self-Service Success"},
        {"step_key": "team_adoption", "step_label": "Team Adoption"},
    ],
}


def get_or_create_tenant(
    db: Session,
    tenant_id: uuid.UUID,
    tenant_name: str,
    primary_domain: Optional[str] = None,
    plan_tier: PlanTier = PlanTier.TIER1
) -> Tenant:
    """Get or create tenant (idempotent)"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        tenant = Tenant(
            id=tenant_id,
            name=tenant_name,
            primary_domain=primary_domain,
            plan_tier=plan_tier
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant


def initialize_onboarding_steps(
    db: Session,
    session_id: uuid.UUID,
    phase: OnboardingPhase
) -> List[OnboardingStep]:
    """Initialize onboarding steps for a phase"""
    steps = ONBOARDING_STEPS.get(phase, [])
    created_steps = []
    
    for step_def in steps:
        # Check if step already exists
        existing = db.query(OnboardingStep).filter(
            OnboardingStep.onboarding_session_id == session_id,
            OnboardingStep.step_key == step_def["step_key"]
        ).first()
        
        if not existing:
            step = OnboardingStep(
                onboarding_session_id=session_id,
                phase=phase,
                step_key=step_def["step_key"],
                step_label=step_def["step_label"],
                completed=False
            )
            db.add(step)
            created_steps.append(step)
    
    db.commit()
    return created_steps


def get_or_create_sla_policy(
    db: Session,
    tenant_id: uuid.UUID,
    plan_tier: PlanTier
) -> Optional[SLAPolicy]:
    """Get or create SLA policy for tenant and tier"""
    policy = db.query(SLAPolicy).filter(
        SLAPolicy.tenant_id == tenant_id,
        SLAPolicy.tier == plan_tier
    ).first()
    
    if not policy:
        # Use default SLA times
        from app.services.sla_service import get_default_sla_policy
        defaults = get_default_sla_policy(plan_tier)
        
        policy = SLAPolicy(
            tenant_id=tenant_id,
            tier=plan_tier,
            first_response_minutes=defaults["first_response"],
            resolution_minutes=defaults["resolution"]
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
    
    return policy


def create_tenant_entitlements(
    db: Session,
    tenant_id: uuid.UUID,
    plan_tier: PlanTier,
    sla_policy_id: Optional[uuid.UUID] = None
) -> TenantEntitlement:
    """Create or update tenant entitlements"""
    entitlement = db.query(TenantEntitlement).filter(
        TenantEntitlement.tenant_id == tenant_id
    ).first()
    
    # Determine features based on tier
    ai_features = {
        "intent_classification": True,
        "kb_rag": plan_tier != PlanTier.TIER0,
        "draft_replies": plan_tier in [PlanTier.TIER1, PlanTier.TIER2],
    }
    
    portal_enabled = True
    freescout_enabled = plan_tier in [PlanTier.TIER1, PlanTier.TIER2]
    
    if entitlement:
        entitlement.plan_tier = plan_tier.value
        entitlement.sla_policy_id = sla_policy_id
        entitlement.portal_enabled = portal_enabled
        entitlement.freescout_enabled = freescout_enabled
        entitlement.ai_features = ai_features
        entitlement.updated_at = datetime.utcnow()
    else:
        entitlement = TenantEntitlement(
            tenant_id=tenant_id,
            plan_tier=plan_tier.value,
            sla_policy_id=sla_policy_id,
            portal_enabled=portal_enabled,
            freescout_enabled=freescout_enabled,
            ai_features=ai_features
        )
        db.add(entitlement)
    
    db.commit()
    db.refresh(entitlement)
    return entitlement


def start_onboarding(
    db: Session,
    tenant_id: uuid.UUID,
    tenant_name: str,
    primary_domain: Optional[str],
    plan_tier: PlanTier,
    trigger_source: OnboardingTrigger
) -> OnboardingSession:
    """Start onboarding session (idempotent)"""
    # Check if session already exists
    existing_session = db.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == tenant_id
    ).first()
    
    if existing_session:
        return existing_session  # Idempotent return
    
    # Get or create tenant
    tenant = get_or_create_tenant(db, tenant_id, tenant_name, primary_domain, plan_tier)
    
    # Create onboarding session
    session = OnboardingSession(
        tenant_id=tenant_id,
        current_phase=OnboardingPhase.PHASE_0_PROVISIONED,
        status=OnboardingStatus.ACTIVE,
        trigger_source=trigger_source,
        started_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Initialize steps for Phase 0
    initialize_onboarding_steps(db, session.id, OnboardingPhase.PHASE_0_PROVISIONED)
    
    # Create SLA policy
    sla_policy = get_or_create_sla_policy(db, tenant_id, plan_tier)
    
    # Create entitlements
    create_tenant_entitlements(db, tenant_id, plan_tier, sla_policy.id if sla_policy else None)
    
    # Log audit event
    log_audit_event(
        db,
        event_type="onboarding_started",
        payload={
            "tenant_id": str(tenant_id),
            "plan_tier": plan_tier.value,
            "trigger_source": trigger_source.value,
            "onboarding_session_id": str(session.id)
        }
    )
    
    return session


def advance_onboarding_step(
    db: Session,
    tenant_id: uuid.UUID,
    step_key: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Advance onboarding step (idempotent)"""
    session = db.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == tenant_id,
        OnboardingSession.status == OnboardingStatus.ACTIVE
    ).first()
    
    if not session:
        return False
    
    # Find the step
    step = db.query(OnboardingStep).filter(
        OnboardingStep.onboarding_session_id == session.id,
        OnboardingStep.step_key == step_key
    ).first()
    
    if not step:
        return False
    
    # Mark step complete (idempotent)
    if not step.completed:
        step.completed = True
        step.completed_at = datetime.utcnow()
        if metadata:
            step.metadata = metadata
        db.commit()
        
        # Log audit event
        log_audit_event(
            db,
            event_type="onboarding_step_completed",
            payload={
                "tenant_id": str(tenant_id),
                "step_key": step_key,
                "phase": session.current_phase.value
            }
        )
        
        # Check if all steps in current phase are complete
        phase_steps = db.query(OnboardingStep).filter(
            OnboardingStep.onboarding_session_id == session.id,
            OnboardingStep.phase == session.current_phase
        ).all()
        
        all_complete = all(s.completed for s in phase_steps)
        
        if all_complete:
            # Advance to next phase
            phase_order = [
                OnboardingPhase.PHASE_0_PROVISIONED,
                OnboardingPhase.PHASE_1_FIRST_VALUE,
                OnboardingPhase.PHASE_2_CORE_WORKFLOWS,
                OnboardingPhase.PHASE_3_INDEPENDENT,
                OnboardingPhase.COMPLETED,
            ]
            
            current_index = phase_order.index(session.current_phase)
            if current_index < len(phase_order) - 1:
                next_phase = phase_order[current_index + 1]
                session.current_phase = next_phase
                session.last_updated_at = datetime.utcnow()
                
                # Initialize steps for new phase
                initialize_onboarding_steps(db, session.id, next_phase)
                
                db.commit()
                
                # Log audit event
                log_audit_event(
                    db,
                    event_type="onboarding_phase_advanced",
                    payload={
                        "tenant_id": str(tenant_id),
                        "from_phase": phase_order[current_index].value,
                        "to_phase": next_phase.value
                    }
                )
                
                # Auto-complete if reached final phase
                if next_phase == OnboardingPhase.COMPLETED:
                    complete_onboarding(db, tenant_id)
    
    return True


def pause_onboarding(
    db: Session,
    tenant_id: uuid.UUID,
    reason: str
) -> bool:
    """Pause onboarding session"""
    session = db.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == tenant_id
    ).first()
    
    if not session:
        return False
    
    session.status = OnboardingStatus.PAUSED
    session.current_phase = OnboardingPhase.PAUSED
    session.last_updated_at = datetime.utcnow()
    db.commit()
    
    log_audit_event(
        db,
        event_type="onboarding_paused",
        payload={
            "tenant_id": str(tenant_id),
            "reason": reason
        }
    )
    
    return True


def resume_onboarding(
    db: Session,
    tenant_id: uuid.UUID
) -> bool:
    """Resume onboarding session"""
    session = db.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == tenant_id,
        OnboardingSession.status == OnboardingStatus.PAUSED
    ).first()
    
    if not session:
        return False
    
    # Resume to last active phase (or Phase 0 if paused before starting)
    if session.current_phase == OnboardingPhase.PAUSED:
        session.current_phase = OnboardingPhase.PHASE_0_PROVISIONED
    
    session.status = OnboardingStatus.ACTIVE
    session.last_updated_at = datetime.utcnow()
    db.commit()
    
    log_audit_event(
        db,
        event_type="onboarding_resumed",
        payload={
            "tenant_id": str(tenant_id)
        }
    )
    
    return True


def complete_onboarding(
    db: Session,
    tenant_id: uuid.UUID
) -> bool:
    """Complete onboarding session"""
    session = db.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == tenant_id
    ).first()
    
    if not session:
        return False
    
    session.status = OnboardingStatus.COMPLETED
    session.current_phase = OnboardingPhase.COMPLETED
    session.completed_at = datetime.utcnow()
    session.last_updated_at = datetime.utcnow()
    db.commit()
    
    log_audit_event(
        db,
        event_type="onboarding_completed",
        payload={
            "tenant_id": str(tenant_id),
            "completed_at": session.completed_at.isoformat()
        }
    )
    
    return True


def upgrade_tier(
    db: Session,
    tenant_id: uuid.UUID,
    previous_tier: PlanTier,
    new_tier: PlanTier,
    trigger_source: OnboardingTrigger
) -> bool:
    """Upgrade or downgrade tenant tier"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return False
    
    tenant.plan_tier = new_tier
    
    # Update entitlements
    sla_policy = get_or_create_sla_policy(db, tenant_id, new_tier)
    create_tenant_entitlements(db, tenant_id, new_tier, sla_policy.id if sla_policy else None)
    
    db.commit()
    
    log_audit_event(
        db,
        event_type="tier_changed",
        payload={
            "tenant_id": str(tenant_id),
            "previous_tier": previous_tier.value,
            "new_tier": new_tier.value,
            "trigger_source": trigger_source.value
        }
    )
    
    return True

