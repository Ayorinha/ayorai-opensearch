# R13 — Tenant isolation foundation

R13 introduces an explicit `TenantContext` for control-plane scoping.

Tenant identifiers are required inputs; they are never derived from prompts, evidence, citations, or model output. Resource keys are namespaced as `tenant_id:resource_id` and cross-tenant access is rejected before resource operations.

This is an isolation primitive, not an authentication system. Production deployment must bind the context to authenticated identity and enforce authorization at every persistence, queue, search, and API boundary.

The invariant is simple: a trace, job, replay, or other tenant-owned resource must never be addressable through another tenant's context.
