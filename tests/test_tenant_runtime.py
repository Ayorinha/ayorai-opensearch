from ayorai_attractor.agents.core import AgentContext
from ayorai_attractor.failure_engine.core import FailureEngine
from ayorai_attractor.evidence.core import EvidenceStore
from ayorai_attractor.tenant import TenantContext


def test_agent_context_carries_trusted_tenant_context() -> None:
    tenant = TenantContext(
        tenant_id="tenant-a",
        subject_id="user-1",
        authorization_scope="verify:read",
    )
    context = AgentContext(
        query="test",
        provider=None,  # type: ignore[arg-type]
        search_provider=None,
        evidence=EvidenceStore(),
        failures=FailureEngine(),
        tenant_context=tenant,
    )

    assert context.tenant_context is tenant
    assert context.tenant_context.metadata()["tenant_id"] == "tenant-a"
