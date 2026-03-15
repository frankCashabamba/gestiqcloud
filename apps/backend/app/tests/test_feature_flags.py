"""Tests for feature flag resolution."""
from app.modules.feature_flags.service import resolve_flags


def test_default_flags():
    flags = resolve_flags()
    assert flags.is_enabled("pos_enabled") is True
    assert flags.is_enabled("einvoicing_enabled") is False
    assert flags.is_enabled("copilot_enabled") is True


def test_country_override_ecuador():
    flags = resolve_flags(country_code="EC")
    assert flags.is_enabled("einvoicing_enabled") is True
    assert flags.source["einvoicing_enabled"] == "country:EC"


def test_country_override_chile():
    flags = resolve_flags(country_code="CL")
    assert flags.is_enabled("einvoicing_enabled") is True


def test_plan_override_free():
    flags = resolve_flags(plan="free")
    assert flags.is_enabled("copilot_write_actions") is False
    assert flags.is_enabled("hr_enabled") is False


def test_plan_override_professional():
    flags = resolve_flags(plan="professional")
    assert flags.is_enabled("copilot_write_actions") is True
    assert flags.is_enabled("hr_enabled") is True
    assert flags.is_enabled("advanced_reports") is True


def test_tenant_override():
    flags = resolve_flags(
        tenant_id="test-123",
        tenant_features={"crm_enabled": True, "production_enabled": True},
    )
    assert flags.is_enabled("crm_enabled") is True
    assert flags.is_enabled("production_enabled") is True
    assert flags.source["crm_enabled"] == "tenant:test-123"


def test_beta_user():
    flags = resolve_flags(
        user_id="user-42",
        beta_users={"user-42"},
    )
    assert flags.is_enabled("copilot_write_actions") is True
    assert flags.source["copilot_write_actions"] == "beta_user:user-42"


def test_unknown_flag_returns_false():
    flags = resolve_flags()
    assert flags.is_enabled("nonexistent_flag") is False


def test_resolution_order():
    flags = resolve_flags(
        country_code="EC",
        tenant_features={"einvoicing_enabled": False},
        tenant_id="t-1",
    )
    assert flags.is_enabled("einvoicing_enabled") is False
    assert flags.source["einvoicing_enabled"] == "tenant:t-1"
