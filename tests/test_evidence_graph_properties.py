from hypothesis import given
from hypothesis import strategies as st

from ayorai_attractor.evidence.graph import EvidenceGraph
from ayorai_attractor.verification.models import Claim, Evidence, Stance, StanceEdge


@given(
    node_ids=st.lists(
        st.text(min_size=1, max_size=12),
        min_size=2,
        max_size=8,
        unique=True,
    )
)
def test_graph_neighbors_are_exactly_linked_targets(node_ids: list[str]) -> None:
    graph = EvidenceGraph()
    for node_id in node_ids:
        graph.add_node(node_id, "source", node_id)

    for source, target in zip(node_ids, node_ids[1:], strict=False):
        graph.link(source, "supports", target)

    for index, source in enumerate(node_ids[:-1]):
        assert [node.id for node in graph.neighbors(source, "supports")] == [node_ids[index + 1]]
    assert graph.neighbors(node_ids[-1], "supports") == []


@given(
    claim_id=st.text(min_size=1, max_size=12),
    evidence_id=st.text(min_size=1, max_size=12),
    origin_id=st.text(min_size=1, max_size=12),
)
def test_evidence_and_stance_preserve_claim_and_evidence_identity(
    claim_id: str,
    evidence_id: str,
    origin_id: str,
) -> None:
    claim = Claim(id=claim_id, text="claim")
    evidence = Evidence(
        id=evidence_id,
        claim_id=claim.id,
        source_id="source",
        source_location="document:1",
        retrieved_at="2026-10-01T00:00:00Z",
        start_offset=0,
        end_offset=5,
        excerpt="claim",
        origin_id=origin_id,
    )
    stance = StanceEdge(
        id="stance",
        claim_id=claim.id,
        evidence_id=evidence.id,
        stance=Stance.SUPPORTS,
    )

    assert evidence.claim_id == claim.id
    assert stance.claim_id == claim.id
    assert stance.evidence_id == evidence.id
