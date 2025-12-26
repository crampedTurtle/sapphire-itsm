"""
KB Article models for indexing, revisions, and quality tracking
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class KBArticleIndex(Base):
    """Index of KB articles for similarity search and deduplication"""
    __tablename__ = "kb_articles_index"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outline_document_id = Column(String, nullable=False, unique=True, index=True)
    title = Column(Text, nullable=False)
    tags = Column(ARRAY(String), nullable=True)  # Array of tag strings
    tenant_level = Column(String, nullable=False, default="global")  # global | tenant-specific
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    embedding = Column(JSONB, nullable=True)  # Vector embedding (stored as JSON array)
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)  # Can be disabled if rejected
    
    # Relationships
    tenant = relationship("Tenant")
    revisions = relationship("KBArticleRevision", back_populates="article", order_by="KBArticleRevision.revision_number")
    quality_scores = relationship("KBQualityScore", back_populates="article")


class KBArticleRevision(Base):
    """Revision history for KB articles"""
    __tablename__ = "kb_article_revisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outline_document_id = Column(String, nullable=False, index=True)
    article_id = Column(UUID(as_uuid=True), ForeignKey("kb_articles_index.id"), nullable=False)
    revision_number = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)  # Full markdown content
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_by = Column(String, nullable=False, default="ai")  # 'ai' or user id
    
    # Relationships
    article = relationship("KBArticleIndex", back_populates="revisions")


class KBDecisionLog(Base):
    """Log of decisions made by KB Update Agent"""
    __tablename__ = "kb_decision_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    support_log_id = Column(UUID(as_uuid=True), ForeignKey("support_ai_logs.id"), nullable=True, index=True)
    decision = Column(String, nullable=False)  # "create", "update", "skip"
    reason = Column(Text, nullable=True)
    similarity_score = Column(String, nullable=True)  # JSON with similarity details
    outline_document_id = Column(String, nullable=True)  # Created/updated document
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    support_log = relationship("SupportAILog")


class KBQualityScore(Base):
    """Quality scores for KB articles"""
    __tablename__ = "kb_quality_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outline_document_id = Column(String, nullable=False, index=True)
    article_id = Column(UUID(as_uuid=True), ForeignKey("kb_articles_index.id"), nullable=True)
    version_revision_id = Column(UUID(as_uuid=True), ForeignKey("kb_article_revisions.id"), nullable=True)
    clarity_score = Column(Integer, nullable=False)  # 1-10
    completeness_score = Column(Integer, nullable=False)  # 1-10
    technical_accuracy_score = Column(Integer, nullable=False)  # 1-10
    structure_score = Column(Integer, nullable=False)  # 1-10
    overall_score = Column(Integer, nullable=False)  # 1-10
    needs_review = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=True)  # Why review is needed
    reviewed = Column(Boolean, nullable=False, default=False)  # Has been reviewed by human
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)  # User ID who reviewed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    article = relationship("KBArticleIndex", back_populates="quality_scores")
    revision = relationship("KBArticleRevision")

