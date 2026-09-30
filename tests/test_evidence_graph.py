import pytest

from ayorai_attractor.evidence.graph import EvidenceGraph


def test_evidence_graph_links_claim_to_source() -> None:
    graph = EvidenceGraph()
    graph.add_node("q1", "question", "What is RAG?")
    graph.add_node("s1", "source", "https://example.com")
    graph.link("q1", "supported_by", "s1")

    assert graph.neighbors("q1", "supported_by")[0].value == "https://example.com"


def test_evidence_graph_rejects_missing_endpoint() -> None:
    graph = EvidenceGraph()
    graph.add_node("q1", "question", "test")

    with pytest.raises(KeyError):
        graph.link("q1", "supported_by", "missing")
