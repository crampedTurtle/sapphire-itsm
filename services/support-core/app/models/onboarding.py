"""
Onboarding and tier lifecycle models
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class OnboardingPhase(str, enum.Enum):
    NOT_STARTED = "not_started"
    PHASE_0_PROVISIONED = "phase_0_provisioned"
    PHASE_1_FIRST_VALUE = "phase_1_first_value"
    PHASE_2_CORE_WORKFLOWS = "phase_2_core_workflows"
    PHASE_3_INDEPENDENT = "phase_3_independent"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class OnboardingStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class OnboardingTrigger(str, enum.Enum):
    SUPABASE_REGISTRATION = "supabase_registration"
    TIER_UPGRADE = "tier_upgrade"
    MANUAL_RESTART = "manual_restart"


class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    current_phase = Column(SQLEnum(OnboardingPhase), nullable=False, default=OnboardingPhase.NOT_STARTED)
    status = Column(SQLEnum(OnboardingStatus), nullable=False, default=OnboardingStatus.ACTIVE)
    trigger_source = Column(SQLEnum(OnboardingTrigger), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    steps = relationship("OnboardingStep", back_populates="session", cascade="all, delete-orphan")


class OnboardingStep(Base):
    __tablename__ = "onboarding_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    onboarding_session_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_sessions.id"), nullable=False, index=True)
    phase = Column(SQLEnum(OnboardingPhase), nullable=False)
    step_key = Column(String, nullable=False)
    step_label = Column(String, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    metadata = Column(JSONB, nullable=True)
    
    # Relationships
    session = relationship("OnboardingSession", back_populates="steps")


class TenantEntitlement(Base):
    __tablename__ = "tenant_entitlements"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True)
    plan_tier = Column(String, nullable=False)  # tier0, tier1, tier2
    sla_policy_id = Column(UUID(as_uuid=True), ForeignKey("sla_policies.id"), nullable=True)
    portal_enabled = Column(Boolean, nullable=False, default=True)
    freescout_enabled = Column(Boolean, nullable=False, default=False)
    ai_features = Column(JSONB, nullable=True)  # e.g., {"intent_classification": true, "kb_rag": true, "draft_replies": true}
    effective_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    sla_policy = relationship("SLAPolicy", foreign_keys=[sla_policy_id])

