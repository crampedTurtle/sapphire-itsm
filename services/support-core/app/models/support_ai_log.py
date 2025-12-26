"""
Support AI Engine logging model
Tracks AI resolution attempts for feedback loop and improvement
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class SupportAILog(Base):
    __tablename__ = "support_ai_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True, index=True)
    message = Column(String, nullable=False)  # Original user message
    subject = Column(String, nullable=True)
    ai_answer = Column(String, nullable=False)  # AI-generated response
    confidence = Column(Float, nullable=False)  # Confidence score
    resolved = Column(Boolean, nullable=False, default=False)  # Was issue resolved?
    follow_up_flag = Column(Boolean, nullable=False, default=False)  # Did AI ask for clarification?
    escalation_triggered = Column(Boolean, nullable=False, default=False)  # Was case escalated?
    attempt_number = Column(Integer, nullable=False, default=1)  # Which attempt (1, 2, 3...)
    citations = Column(JSONB, nullable=True)  # Citations used
    context_docs = Column(JSONB, nullable=True)  # Context documents retrieved
    user_feedback = Column(String, nullable=True)  # User feedback (helpful/not helpful)
    model_used = Column(String, nullable=False)
    tier = Column(Integer, nullable=True)  # Tier level (0, 1, 2)
    kb_document_id = Column(String, nullable=True)  # Outline document ID if KB article was created
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    tenant = relationship("Tenant")
    case = relationship("Case")

