"""
Tenant and Identity models
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class PlanTier(str, enum.Enum):
    TIER0 = "tier0"
    TIER1 = "tier1"
    TIER2 = "tier2"


class IdentityRole(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    OPS = "ops"


class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    primary_domain = Column(String, nullable=True, unique=True, index=True)
    plan_tier = Column(SQLEnum(PlanTier), nullable=False, default=PlanTier.TIER0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    identities = relationship("Identity", back_populates="tenant")
    cases = relationship("Case", back_populates="tenant")
    sla_policies = relationship("SLAPolicy", back_populates="tenant")


class Identity(Base):
    __tablename__ = "identities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    role = Column(SQLEnum(IdentityRole), nullable=False, default=IdentityRole.CUSTOMER)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="identities")
    created_cases = relationship("Case", foreign_keys="Case.created_by_identity_id", back_populates="created_by")
    owned_cases = relationship("Case", foreign_keys="Case.owner_identity_id", back_populates="owner")

