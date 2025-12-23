"""
AI artifact model
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class ArtifactType(str, enum.Enum):
    SUMMARY = "summary"
    DRAFT_REPLY = "draft_reply"
    KB_ANSWER = "kb_answer"


class AIArtifact(Base):
    __tablename__ = "ai_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True, index=True)
    intake_event_id = Column(UUID(as_uuid=True), ForeignKey("intake_events.id"), nullable=True, index=True)
    artifact_type = Column(SQLEnum(ArtifactType), nullable=False)
    content = Column(String, nullable=False)
    citations = Column(JSONB, nullable=True)  # Array of {title, url, snippet}
    confidence = Column(Float, nullable=True)
    model_used = Column(String, nullable=False)
    prompt_metadata = Column(JSONB, nullable=True)  # Store prompt details for audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="ai_artifacts")
    intake_event = relationship("IntakeEvent", back_populates="ai_artifacts")

