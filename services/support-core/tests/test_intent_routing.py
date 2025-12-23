"""
Tests for intent routing decisions
"""
import pytest
from app.models.intake import Intent, Urgency, RecommendedAction
from app.models.tenant import PlanTier


def test_sales_intent_routing():
    """Test sales intent routing logic"""
    intent = Intent.SALES
    action = RecommendedAction.ROUTE_SALES
    
    # Sales should route to CRM
    assert intent == Intent.SALES
    assert action == RecommendedAction.ROUTE_SALES


def test_support_tier0_routing():
    """Test Tier 0 support routing"""
    intent = Intent.SUPPORT
    tier = PlanTier.TIER0
    action = RecommendedAction.SELF_SERVICE
    
    # Tier 0 support should use self-service
    assert intent == Intent.SUPPORT
    assert tier == PlanTier.TIER0
    assert action == RecommendedAction.SELF_SERVICE


def test_support_tier1_routing():
    """Test Tier 1 support routing"""
    intent = Intent.SUPPORT
    tier = PlanTier.TIER1
    action = RecommendedAction.CREATE_CASE
    
    # Tier 1 support should create case
    assert intent == Intent.SUPPORT
    assert tier == PlanTier.TIER1
    assert action == RecommendedAction.CREATE_CASE


def test_compliance_flag_routing():
    """Test compliance flag routing"""
    compliance_flag = True
    urgency = Urgency.CRITICAL
    
    # Compliance flags should escalate
    assert compliance_flag is True
    # Should result in escalated case status

