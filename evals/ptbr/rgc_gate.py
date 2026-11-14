"""Pre-annotation component-resolution gate for RGC (DEC-027 D7).

The gate reads only case_id and cited_article_ids. It does not inspect annotation
labels, predictions, benchmark results, or legacy bootstrap_cluster_id metadata.
The public record is deliberately limited to K and component-size information.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import NamedTuple

from evals.ptbr.rgc_components import build_connected_article_components

MINIMUM_COMPONENTS = 6


class PreannotationGateResult(NamedTuple):
    """D7 decision and the only component-inventory fields allowed in its record."""

    component_count: int
    component_sizes: tuple[int, ...]
    largest_component_size: int

    @property
    def can_proceed(self) -> bool:
        """Whether the inventory meets D7's minimum-resolution condition."""

        return self.component_count >= MINIMUM_COMPONENTS

    def public_record(self) -> dict[str, object]:
        """Return only the fields permitted by DEC-027 D7."""

        return {
            "K": self.component_count,
            "component_sizes": list(self.component_sizes),
            "largest_component_size": self.largest_component_size,
        }


def evaluate_preannotation_gate(
    cases: Iterable[Mapping[str, object]],
) -> PreannotationGateResult:
    """Evaluate D7 from the complete case/article inventory, before annotation.

    Component construction is delegated to the canonical DEC-023 implementation.
    The result contains no case IDs, article IDs, labels, predictions, or scores.
    Missing, duplicate, malformed, or incomplete inventory data fails closed.
    """

    components = build_connected_article_components(cases)
    sizes = tuple(sorted((len(component.case_ids) for component in components), reverse=True))
    return PreannotationGateResult(
        component_count=len(components),
        component_sizes=sizes,
        largest_component_size=sizes[0] if sizes else 0,
    )
