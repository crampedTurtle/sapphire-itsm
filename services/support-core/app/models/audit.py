"""
Audit event model
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True, index=True)
    intake_event_id = Column(UUID(as_uuid=True), ForeignKey("intake_events.id"), nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # e.g., "case_created", "status_changed", "priority_changed"
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    case = relationship("Case", back_populates="audit_events")

