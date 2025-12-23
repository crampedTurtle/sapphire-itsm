"""
CRM event model
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class CRMEventType(str, enum.Enum):
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    ACCOUNT_CREATED = "account_created"


class CRMEvent(Base):
    __tablename__ = "crm_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

