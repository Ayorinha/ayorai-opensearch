"""Tenant isolation context for multi-tenant runtime boundaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """Immutable identity propagated across request, job, audit and search layers."""

    tenant_id: str
    subject_id: str | None = None
    authorization_scope: str = "default"

    def __post_init__(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("subject_id", self.subject_id),
            ("authorization_scope", self.authorization_scope),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"{name} must not be blank")

    def metadata(self) -> dict[str, str]:
        """Return safe routing metadata; never include credentials or prompts."""
        result = {
            "tenant_id": self.tenant_id,
            "authorization_scope": self.authorization_scope,
        }
        if self.subject_id is not None:
            result["subject_id"] = self.subject_id
        return result
