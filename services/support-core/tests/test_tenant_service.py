"""
Tests for tenant resolution service
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.tenant import Tenant, PlanTier
from app.services.tenant_service import resolve_tenant_by_domain, get_or_create_prospect_tenant, get_tenant_tier


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_resolve_tenant_by_domain(db_session):
    """Test tenant resolution by email domain"""
    # Create a tenant
    tenant = Tenant(
        name="Test Company",
        primary_domain="testcompany.com",
        plan_tier=PlanTier.TIER1
    )
    db_session.add(tenant)
    db_session.commit()
    
    # Resolve by domain
    resolved = resolve_tenant_by_domain(db_session, "user@testcompany.com")
    assert resolved is not None
    assert resolved.id == tenant.id
    assert resolved.primary_domain == "testcompany.com"
    
    # Unknown domain returns None
    unknown = resolve_tenant_by_domain(db_session, "user@unknown.com")
    assert unknown is None


def test_get_or_create_prospect_tenant(db_session):
    """Test prospect tenant creation"""
    tenant1 = get_or_create_prospect_tenant(db_session)
    assert tenant1.name == "Prospect"
    assert tenant1.plan_tier == PlanTier.TIER0
    
    # Should return same tenant on second call
    tenant2 = get_or_create_prospect_tenant(db_session)
    assert tenant1.id == tenant2.id


def test_get_tenant_tier(db_session):
    """Test getting tenant tier"""
    tenant = Tenant(
        name="Test",
        primary_domain="test.com",
        plan_tier=PlanTier.TIER2
    )
    db_session.add(tenant)
    db_session.commit()
    
    tier = get_tenant_tier(db_session, str(tenant.id))
    assert tier == PlanTier.TIER2
    
    # Unknown tenant defaults to TIER0
    unknown_tier = get_tenant_tier(db_session, "00000000-0000-0000-0000-000000000000")
    assert unknown_tier == PlanTier.TIER0

