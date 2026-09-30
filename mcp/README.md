# MCP Gateway

The future MCP layer will treat external tools as capabilities, not implicit permissions.

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
