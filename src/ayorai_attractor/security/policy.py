"""Capability allow-list for tool calls.

Status: experimental — fora do escopo verificado. Ver docs/TRACEABILITY-MASTER.md.
Not used by the verification pipeline, the Judge or the public API; the interface may
change without a deprecation period. See docs/EXPERIMENTAL-MODULES.md.

Deny by default: an unknown capability is not authorized. ``requires_approval``
is recorded but NOT enforced by ``authorize()``; callers must check it
themselves before running a capability that requires approval.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPolicy:
    capability: str
    allowed: bool
    requires_approval: bool = False


class SecurityPolicy:
    def __init__(self) -> None:
        self._policies: dict[str, ToolPolicy] = {}

    def set(self, policy: ToolPolicy) -> None:
        self._policies[policy.capability] = policy

    def authorize(self, capability: str) -> bool:
        policy = self._policies.get(capability)
        return bool(policy and policy.allowed)
