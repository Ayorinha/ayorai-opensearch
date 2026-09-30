# MCP Gateway

The MCP Gateway now treats external tools as capabilities, not implicit permissions. Tool execution is deny-by-default for untrusted plugins.

Every tool should have:

- declared capability
- provider identity
- health state
- authorization policy
- input validation
- timeout
- audit event
- failure and rollback behavior

Existing AYORAI MCP security work can be integrated through adapters rather than hard-coded coupling.
