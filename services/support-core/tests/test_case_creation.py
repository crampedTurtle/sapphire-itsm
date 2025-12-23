"""
Tests for case creation
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.core.database import Base
from app.models.tenant import Tenant, PlanTier
from app.models.case import Case, CaseStatus, CasePriority, CaseCategory
from app.services.audit_service import log_audit_event
from app.models.audit import AuditEvent


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_tenant(db_session):
    """Create test tenant"""
    tenant = Tenant(
        name="Test Company",
        primary_domain="test.com",
        plan_tier=PlanTier.TIER1
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


def test_create_case(db_session, test_tenant):
    """Test case creation"""
    case = Case(
        tenant_id=test_tenant.id,
        title="Test Case",
        status=CaseStatus.NEW,
        priority=CasePriority.NORMAL,
        category=CaseCategory.SUPPORT
    )
    db_session.add(case)
    db_session.commit()
    
    assert case.id is not None
    assert case.status == CaseStatus.NEW
    assert case.tenant_id == test_tenant.id


def test_audit_logging(db_session, test_tenant):
    """Test audit event logging"""
    case = Case(
        tenant_id=test_tenant.id,
        title="Test Case",
        status=CaseStatus.NEW,
        priority=CasePriority.NORMAL,
        category=CaseCategory.SUPPORT
    )
    db_session.add(case)
    db_session.commit()
    
    log_audit_event(
        db_session,
        event_type="case_created",
        case_id=case.id,
        payload={"test": "data"}
    )
    
    audit_events = db_session.query(AuditEvent).filter(
        AuditEvent.case_id == case.id
    ).all()
    
    assert len(audit_events) == 1
    assert audit_events[0].event_type == "case_created"
    assert audit_events[0].payload == {"test": "data"}

