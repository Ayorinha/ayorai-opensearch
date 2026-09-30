from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceNode:
    id: str
    kind: str
    value: str


@dataclass(frozen=True)
class EvidenceEdge:
    source: str
    relation: str
    target: str


@dataclass
class EvidenceGraph:
    nodes: dict[str, EvidenceNode] = field(default_factory=dict)
    edges: list[EvidenceEdge] = field(default_factory=list)

    def add_node(self, node_id: str, kind: str, value: str) -> EvidenceNode:
        node = EvidenceNode(id=node_id, kind=kind, value=value)
        self.nodes[node_id] = node
        return node

    def link(self, source: str, relation: str, target: str) -> EvidenceEdge:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("Both graph endpoints must exist")
        edge = EvidenceEdge(source=source, relation=relation, target=target)
        self.edges.append(edge)
        return edge

    def neighbors(self, node_id: str, relation: str | None = None) -> list[EvidenceNode]:
        targets = [
            edge.target
            for edge in self.edges
            if edge.source == node_id and (relation is None or edge.relation == relation)
        ]
        return [self.nodes[target] for target in targets]
