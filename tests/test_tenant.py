import pytest

from ayorai_attractor.tenant import TenantContext


def test_tenant_context_is_immutable_and_safe_metadata() -> None:
    context = TenantContext(
        tenant_id="tenant-a",
        subject_id="user-1",
        authorization_scope="verify:read",
    )
    assert context.metadata() == {
        "tenant_id": "tenant-a",
        "subject_id": "user-1",
        "authorization_scope": "verify:read",
    }
    with pytest.raises((AttributeError, TypeError)):
        context.tenant_id = "tenant-b"  # type: ignore[misc]


def test_tenant_context_rejects_blank_identity() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        TenantContext(tenant_id=" ")


def test_tenant_context_does_not_require_subject_identity() -> None:
    context = TenantContext(tenant_id="tenant-a")
    assert context.metadata() == {
        "tenant_id": "tenant-a",
        "authorization_scope": "default",
    }
