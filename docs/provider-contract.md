# Provider Contract

Providers must expose capabilities independently from agent roles.

Minimum metadata:

- id
- category
- capabilities
- enabled state
- health
- latency measurements
- cost hint
- evaluation history

A provider adapter must fail explicitly. Missing credentials or unavailable APIs must never be represented as a successful verified result.
