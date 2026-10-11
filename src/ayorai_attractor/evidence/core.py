from uuid import uuid4

from ayorai_attractor.models import Evidence


class EvidenceStore:
    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    def add(
        self,
        claim: str,
        source: str,
        excerpt: str,
        verified: bool = False,
        independent: bool = False,
    ) -> Evidence:
        item = Evidence(
            id=f"ev_{uuid4().hex[:12]}",
            claim=claim,
            source=source,
            excerpt=excerpt,
            verified=verified,
            independent=independent,
        )
        self._items[item.id] = item
        return item

    def all(self) -> list[Evidence]:
        return list(self._items.values())
