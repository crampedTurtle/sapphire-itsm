"""
Case and case message models
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class CaseStatus(str, enum.Enum):
    NEW = "new"
    OPEN = "open"
    PENDING_CUSTOMER = "pending_customer"
    PENDING_INTERNAL = "pending_internal"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CaseCategory(str, enum.Enum):
    SUPPORT = "support"
    ONBOARDING = "onboarding"
    BILLING = "billing"
    COMPLIANCE = "compliance"
    OUTAGE = "outage"


class SenderType(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    external_source = Column(String, nullable=True)  # e.g., "freescout"
    external_case_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    status = Column(SQLEnum(CaseStatus), nullable=False, default=CaseStatus.NEW, index=True)
    priority = Column(SQLEnum(CasePriority), nullable=False, default=CasePriority.NORMAL, index=True)
    category = Column(SQLEnum(CaseCategory), nullable=False, default=CaseCategory.SUPPORT)
    created_by_identity_id = Column(UUID(as_uuid=True), ForeignKey("identities.id"), nullable=True)
    owner_identity_id = Column(UUID(as_uuid=True), ForeignKey("identities.id"), nullable=True, index=True)
    ai_confidence = Column(Float, nullable=True)  # AI confidence score (0.0-1.0) from initial resolution attempt
    tier_route = Column(Integer, nullable=True)  # Tier routing: 0, 1, 2, 3
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="cases")
    created_by = relationship("Identity", foreign_keys=[created_by_identity_id], back_populates="created_cases")
    owner = relationship("Identity", foreign_keys=[owner_identity_id], back_populates="owned_cases")
    messages = relationship("CaseMessage", back_populates="case", order_by="CaseMessage.created_at")
    ai_artifacts = relationship("AIArtifact", back_populates="case")
    sla_events = relationship("SLAEvent", back_populates="case")
    audit_events = relationship("AuditEvent", back_populates="case")


class CaseMessage(Base):
    __tablename__ = "case_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    sender_type = Column(SQLEnum(SenderType), nullable=False)
    sender_email = Column(String, nullable=False)
    body_text = Column(String, nullable=False)
    attachments = Column(JSONB, nullable=True)  # Array of {filename, url}
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    case = relationship("Case", back_populates="messages")

