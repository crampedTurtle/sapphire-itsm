"""
SLA policy and event models
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base
from app.models.tenant import PlanTier


class SLAEventType(str, enum.Enum):
    STARTED = "started"
    FIRST_RESPONSE = "first_response"
    BREACHED_FIRST_RESPONSE = "breached_first_response"
    BREACHED_RESOLUTION = "breached_resolution"
    PAUSED = "paused"
    RESUMED = "resumed"


class SLAPolicy(Base):
    __tablename__ = "sla_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    tier = Column(SQLEnum(PlanTier), nullable=False)
    first_response_minutes = Column(Integer, nullable=False)  # SLA in minutes
    resolution_minutes = Column(Integer, nullable=False)  # SLA in minutes
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="sla_policies")


class SLAEvent(Base):
    __tablename__ = "sla_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(SQLEnum(SLAEventType), nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    case = relationship("Case", back_populates="sla_events")

