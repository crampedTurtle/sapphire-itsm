"""
Tests for onboarding and tier lifecycle API
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

from app.core.database import Base
from app.models.tenant import Tenant, PlanTier
from app.models.onboarding import OnboardingSession, OnboardingStep, TenantEntitlement, OnboardingPhase, OnboardingStatus, OnboardingTrigger
from app.services.onboarding_service import (
    start_onboarding,
    advance_onboarding_step,
    pause_onboarding,
    resume_onboarding,
    complete_onboarding,
    upgrade_tier,
)
from app.services.audit_service import log_audit_event
from app.models.audit import AuditEvent


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_tenant_id():
    return uuid.uuid4()


def test_idempotent_onboarding_start(db_session, test_tenant_id):
    """Test that starting onboarding twice returns the same session"""
    session1 = start_onboarding(
        db_session,
        test_tenant_id,
        "Test Company",
        "test.com",
        PlanTier.TIER1,
        OnboardingTrigger.SUPABASE_REGISTRATION
    )
    
    session2 = start_onboarding(
        db_session,
        test_tenant_id,
        "Test Company",
        "test.com",
        PlanTier.TIER1,
        OnboardingTrigger.SUPABASE_REGISTRATION
    )
    
    assert session1.id == session2.id
    assert session1.tenant_id == test_tenant_id
    assert session1.status == OnboardingStatus.ACTIVE
    assert session1.current_phase == OnboardingPhase.PHASE_0_PROVISIONED


def test_onboarding_step_advancement(db_session, test_tenant_id):
    """Test advancing onboarding steps"""
    session = start_onboarding(
        db_session,
        test_tenant_id,
        "Test Company",
        "test.com",
        PlanTier.TIER1,
        OnboardingTrigger.SUPABASE_REGISTRATION
    )
    
    # Advance a step
    success = advance_onboarding_step(
        db_session,
        test_tenant_id,
        "aws_provisioned",
        {"region": "us-east-1"}
    )
    
    assert success is True
    
    # Check step is marked complete
    step = db_session.query(OnboardingStep).filter(
        OnboardingStep.onboarding_session_id == session.id,
        OnboardingStep.step_key == "aws_provisioned"
    ).first()
    
    assert step.completed is True
    assert step.step_metadata == {"region": "us-east-1"}


def test_onboarding_step_idempotent(db_session, test_tenant_id):
    """Test that advancing the same step twice is idempotent"""
    start_onboarding(
        db_session,
        test_tenant_id,
        "Test Company",
        "test.com",
        PlanTier.TIER1,
        OnboardingTrigger.SUPABASE_REGISTRATION
    )
    
    # Advance step twice
    advance_onboarding_step(db_session, test_tenant_id, "aws_provisioned")
    advance_onboarding_step(db_session, test_tenant_id, "aws_provisioned")
    
    # Should only have one audit event
    audit_events = db_session.query(AuditEvent).filter(
        AuditEvent.event_type == "onboarding_step_completed"
    ).all()
    
    assert len(audit_events) == 1


def test_tier_upgrade(db_session, test_tenant_id):
    """Test tier upgrade"""
    # Start with Tier 1
    start_onboarding(
        db_session,
        test_tenant_id,
        "Test Company",
        "test.com",
        PlanTier.TIER1,
        OnboardingTrigger.SUPABASE_REGISTRATION
    )
    
    # Upgrade to Tier 2
    success = upgrade_tier(
        db_session,
        test_tenant_id,
        PlanTier.TIER1,
        PlanTier.TIER2,
        OnboardingTrigger.TIER_UPGRADE
    )
    
    assert success is True
    
    # Check tenant tier updated
    tenant = db_session.query(Tenant).filter(Tenant.id == test_tenant_id).first()
    assert tenant.plan_tier == PlanTier.TIER2
    
    # Check entitlements updated
    entitlement = db_session.query(TenantEntitlement).filter(
        TenantEntitlement.tenant_id == test_tenant_id
    ).first()
    assert entitlement.plan_tier == "tier2"


def test_pause_resume_onboarding(db_session, test_tenant_id):
    """Test pausing and resuming onboarding"""
    start_onboarding(
        db_session,
        test_tenant_id,
        "Test Company",
        "test.com",
        PlanTier.TIER1,
        OnboardingTrigger.SUPABASE_REGISTRATION
    )
    
    # Pause
    success = pause_onboarding(db_session, test_tenant_id, "Customer requested delay")
    assert success is True
    
    session = db_session.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == test_tenant_id
    ).first()
    assert session.status == OnboardingStatus.PAUSED
    
    # Resume
    success = resume_onboarding(db_session, test_tenant_id)
    assert success is True
    
    session = db_session.query(OnboardingSession).filter(
        OnboardingSession.tenant_id == test_tenant_id
    ).first()
    assert session.status == OnboardingStatus.ACTIVE


def test_audit_event_creation(db_session, test_tenant_id):
    """Test that onboarding actions create audit events"""
    start_onboarding(
        db_session,
        test_tenant_id,
        "Test Company",
        "test.com",
        PlanTier.TIER1,
        OnboardingTrigger.SUPABASE_REGISTRATION
    )
    
    # Check audit event created
    audit_events = db_session.query(AuditEvent).filter(
        AuditEvent.event_type == "onboarding_started"
    ).all()
    
    assert len(audit_events) == 1
    assert audit_events[0].payload["tenant_id"] == str(test_tenant_id)

