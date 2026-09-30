from uuid import uuid4

from attractor.models import Evidence, VerificationStatus


class EvidenceStore:
    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    def add(
        self, claim: str, source: str, excerpt: str, verified: bool = False
    ) -> Evidence:
        item = Evidence(
            id=f"ev_{uuid4().hex[:12]}",
            claim=claim,
            source=source,
            excerpt=excerpt,
            verified=verified,
        )
        self._items[item.id] = item
        return item

    def all(self) -> list[Evidence]:
        return list(self._items.values())

    def status(self) -> VerificationStatus:
        items = self.all()
        if not items:
            return VerificationStatus.INSUFFICIENT_EVIDENCE
        independent = [item for item in items if item.independent]
        if all(item.verified for item in items):
            return VerificationStatus.VERIFIED
        if len(independent) >= 2:
            return VerificationStatus.SUPPORTED
        if independent:
            return VerificationStatus.PARTIALLY_SUPPORTED
        return VerificationStatus.UNVERIFIED
