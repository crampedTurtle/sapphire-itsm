"""
Intake event and intent classification models
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Float, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class IntakeSource(str, enum.Enum):
    EMAIL = "email"
    PORTAL = "portal"


class Intent(str, enum.Enum):
    SALES = "sales"
    SUPPORT = "support"
    ONBOARDING = "onboarding"
    BILLING = "billing"
    COMPLIANCE = "compliance"
    OUTAGE = "outage"
    UNKNOWN = "unknown"


class Urgency(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedAction(str, enum.Enum):
    SELF_SERVICE = "self_service"
    CREATE_CASE = "create_case"
    ROUTE_SALES = "route_sales"
    ESCALATE_OPS = "escalate_ops"
    NEEDS_REVIEW = "needs_review"


class IntakeEvent(Base):
    __tablename__ = "intake_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(SQLEnum(IntakeSource), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    from_email = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=True)
    body_text = Column(String, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    intent_classifications = relationship("IntentClassification", back_populates="intake_event")
    ai_artifacts = relationship("AIArtifact", back_populates="intake_event")


class IntentClassification(Base):
    __tablename__ = "intent_classifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_event_id = Column(UUID(as_uuid=True), ForeignKey("intake_events.id"), nullable=False, index=True)
    intent = Column(SQLEnum(Intent), nullable=False)
    urgency = Column(SQLEnum(Urgency), nullable=False, default=Urgency.NORMAL)
    confidence = Column(Float, nullable=False)
    compliance_flag = Column(Boolean, nullable=False, default=False)
    recommended_action = Column(SQLEnum(RecommendedAction), nullable=False)
    model_used = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    intake_event = relationship("IntakeEvent", back_populates="intent_classifications")

