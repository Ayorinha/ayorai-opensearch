from ayorai_attractor.agents.roles import INITIAL_ROLES
from ayorai_attractor.evaluation.bench import benchmark_dimensions
from ayorai_attractor.models import SearchRequest
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.plugins.registry import Plugin, PluginRegistry
from ayorai_attractor.router import AdaptiveRouter


def test_initial_swarm_has_26_roles() -> None:
    assert len(INITIAL_ROLES) == 26


def test_router_is_adaptive() -> None:
    router = AdaptiveRouter()
    fast = router.select("x" * 3, "fast", 3)
    deep = router.select("x" * 3, "deep", 26)
    assert len(fast.roles) == 3
    assert len(deep.roles) == 26


def test_plugin_registry_filters_capability() -> None:
    registry = PluginRegistry()
    registry.register(Plugin(id="search", capabilities={"search"}))
    registry.register(Plugin(id="other", capabilities={"audio"}))
    assert [item.id for item in registry.discover("search")] == ["search"]


def test_benchmark_is_multidimensional() -> None:
    dimensions = benchmark_dimensions()
    assert "accuracy" in dimensions
    assert "safety" in dimensions
    assert "cost" in dimensions


def test_deep_request_never_claims_unverified_evidence() -> None:
    result = Attractor().run(SearchRequest(query="deep test", mode="deep", max_agents=26))
    assert result.verification.value == "insufficient_evidence"
