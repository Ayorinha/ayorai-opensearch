# R12 — Governed MCP gateway

ATTRACTOR already contains an MCP-style gateway and plugin registry. The gateway is the control boundary for tool capabilities; it is not itself the verification Judge.

## Dispatch contract

1. Plugins declare capabilities, enabled state, health, trust level, latency, and optional cost.
2. Discovery filters disabled/unhealthy plugins and, by default, requires `trusted` plugins.
3. Candidates are ordered deterministically by latency and cost metadata.
4. The gateway executes only a registered handler for the selected plugin.
5. Handler failures are converted into a structured unsuccessful `ToolResult` rather than being silently ignored.

## Security boundary

Untrusted plugins are not executed by default. Tool selection does not grant permission to bypass evidence validation, persistence controls, or the deterministic Judge.

Future MCP transport integration should preserve this registry and policy layer instead of allowing arbitrary remote tool execution.
