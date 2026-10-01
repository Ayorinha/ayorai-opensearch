"""Static governance checks for R13."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceConfig:
    endpoint: str
    audit_enabled: bool
    authorization_enabled: bool
    rate_limit_enabled: bool
    data_minimization_enabled: bool


@dataclass(frozen=True)
class GovernanceCheck:
    passed: bool
    findings: tuple[str, ...]


def validate_governance(config: GovernanceConfig) -> GovernanceCheck:
    findings: list[str] = []
    if not config.endpoint.startswith("https://"):
        findings.append("endpoint must use HTTPS")
    if not config.audit_enabled:
        findings.append("audit logging must be enabled")
    if not config.authorization_enabled:
        findings.append("authorization must be enabled")
    if not config.rate_limit_enabled:
        findings.append("rate limiting must be enabled")
    if not config.data_minimization_enabled:
        findings.append("data minimization must be enabled")
    return GovernanceCheck(not findings, tuple(findings))
