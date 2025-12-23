"""
Tenant resolution and entitlement service
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.tenant import Tenant, PlanTier, Identity, IdentityRole
from app.models.intake import IntakeEvent


def resolve_tenant_by_domain(db: Session, email: str) -> Optional[Tenant]:
    """
    Resolve tenant by email domain
    
    If domain is unknown, returns None (will be treated as prospect/tier0)
    """
    domain = email.split("@")[-1].lower() if "@" in email else None
    if not domain:
        return None
    
    tenant = db.query(Tenant).filter(Tenant.primary_domain == domain).first()
    return tenant


def get_or_create_prospect_tenant(db: Session) -> Tenant:
    """
    Get or create the default "prospect" tenant for unknown domains
    """
    tenant = db.query(Tenant).filter(Tenant.name == "Prospect").first()
    if not tenant:
        tenant = Tenant(
            name="Prospect",
            primary_domain=None,
            plan_tier=PlanTier.TIER0
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant


def get_tenant_tier(db: Session, tenant_id: Optional[str]) -> PlanTier:
    """Get tenant plan tier, defaulting to TIER0"""
    if not tenant_id:
        return PlanTier.TIER0
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant:
        return tenant.plan_tier
    return PlanTier.TIER0


def get_or_create_identity(
    db: Session,
    tenant_id: str,
    email: str,
    display_name: Optional[str] = None,
    role: IdentityRole = IdentityRole.CUSTOMER
) -> Identity:
    """Get or create an identity"""
    identity = db.query(Identity).filter(
        Identity.tenant_id == tenant_id,
        Identity.email == email.lower()
    ).first()
    
    if not identity:
        identity = Identity(
            tenant_id=tenant_id,
            email=email.lower(),
            display_name=display_name or email.split("@")[0],
            role=role
        )
        db.add(identity)
        db.commit()
        db.refresh(identity)
    
    return identity

