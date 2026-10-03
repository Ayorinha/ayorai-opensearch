import pytest

from ayorai_attractor.tenancy import TenantContext, require_same_tenant


def test_scope_key_is_explicit_and_deterministic() -> None:
    tenant = TenantContext("tenant-a")
    assert tenant.scope_key("trace-1") == "tenant-a:trace-1"


def test_empty_identifiers_are_rejected() -> None:
    with pytest.raises(ValueError):
        TenantContext(" ")
    with pytest.raises(ValueError):
        TenantContext("tenant-a").scope_key(" ")


def test_cross_tenant_access_is_denied() -> None:
    with pytest.raises(PermissionError, match="cross-tenant"):
        require_same_tenant(TenantContext("tenant-a"), TenantContext("tenant-b"))
