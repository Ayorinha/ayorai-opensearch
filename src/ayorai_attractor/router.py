from dataclasses import dataclass

from ayorai_attractor.agents.roles import INITIAL_ROLES, AgentRole


@dataclass(frozen=True)
class RoutingDecision:
    roles: list[AgentRole]
    reason: str


class AdaptiveRouter:
    def select(self, query: str, mode: str, max_agents: int) -> RoutingDecision:
        del query
        limit = max(1, min(max_agents, len(INITIAL_ROLES)))
        if mode == "fast":
            ids = {"planner", "researcher", "chief_judge"}
            roles = [role for role in INITIAL_ROLES if role.id in ids]
        elif mode == "deep":
            roles = list(INITIAL_ROLES)
        else:
            ids = {
                "planner",
                "researcher",
                "open_search",
                "critic",
                "fact_checker",
                "chief_judge",
            }
            roles = [role for role in INITIAL_ROLES if role.id in ids]
        selected_count = min(limit, len(roles))
        reason = (
            f"mode={mode}; selected={selected_count} "
            f"of {len(INITIAL_ROLES)} initial roles"
        )
        return RoutingDecision(roles=roles[:limit], reason=reason)
