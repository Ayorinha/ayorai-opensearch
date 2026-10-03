"""Explicit tenant scoping primitives for R13.

Tenant identifiers are carried by control-plane operations and are never inferred
from prompts, evidence, or model output.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str

    def __post_init__(self) -> None:
        if not self.tenant_id.strip():
            raise ValueError("tenant_id must not be empty")

    def scope_key(self, resource_id: str) -> str:
        if not resource_id.strip():
            raise ValueError("resource_id must not be empty")
        return f"{self.tenant_id}:{resource_id}"


def require_same_tenant(owner: TenantContext, requested: TenantContext) -> None:
    """Reject cross-tenant access before a resource operation is attempted."""
    if owner.tenant_id != requested.tenant_id:
        raise PermissionError("cross-tenant access denied")
