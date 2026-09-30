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
