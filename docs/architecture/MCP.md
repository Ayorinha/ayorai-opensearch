# R12 — Governed MCP gateway

ATTRACTOR contains an MCP-style gateway and plugin registry. The gateway is the control boundary for tool capabilities; it is not the verification Judge.

**Status: experimental and not wired into any production path.** `mcp_gateway` and `plugins` are outside the import paths of the API and the CLI ([manual, chapter 02](../manual/02-arquitetura.md)). As implemented, `MCPGateway.execute` does not consult `security.policy.SecurityPolicy`; trust filtering is the `trusted_only` argument, which defaults to `True` but a caller can set to `False`; and no audit event is recorded. The sections below describe the intended contract, not an enforced control. Executing tools on behalf of the system requires an authorization layer that does not exist yet (see [Experimental modules](../EXPERIMENTAL-MODULES.md)).

## Dispatch contract

1. Plugins declare capabilities, enabled state, health, trust level, latency, and optional cost.
2. Discovery filters disabled/unhealthy plugins and, by default, requires `trusted` plugins.
3. Candidates are ordered deterministically by latency and cost metadata.
4. The gateway executes only a registered handler for the selected plugin.
5. Handler failures are converted into a structured unsuccessful `ToolResult` rather than being silently ignored.

## Security boundary

Untrusted plugins are not executed by default. Tool selection does not grant permission to bypass evidence validation, persistence controls, or the deterministic Judge.

## Audit boundary

Gateway execution should be represented in the request trace with plugin id, capability, success/failure, and latency metadata. Raw tool payloads and secrets should remain outside durable audit records unless a deployment-specific policy explicitly permits them.

Future MCP transport integration should preserve this registry and policy layer instead of allowing arbitrary remote tool execution.
