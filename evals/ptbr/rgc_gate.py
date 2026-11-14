"""Pre-annotation component-resolution gate for RGC (DEC-027 D7).

The gate reads only case_id and cited_article_ids. It does not inspect annotation
labels, predictions, benchmark results, or legacy bootstrap_cluster_id metadata.
The public record is deliberately limited to K and component-size information.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
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


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    row: dict[str, object] = {}
    for key, value in pairs:
        if key in row:
            raise ValueError(f"duplicate JSON key {key!r}")
        row[key] = value
    return row


def load_preannotation_inventory(path: Path) -> list[dict[str, object]]:
    """Load JSONL containing exactly case_id and cited_article_ids per record.

    This narrow input contract prevents annotation labels, predictions, results,
    and legacy cluster metadata from entering the D7 gate.
    """

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{path}:{line_number}: blank lines are not allowed")
        try:
            row = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{path}:{line_number}: invalid inventory JSON: {exc}") from exc
        if not isinstance(row, dict) or set(row) != {"case_id", "cited_article_ids"}:
            raise ValueError(
                f"{path}:{line_number}: expected exactly case_id and cited_article_ids"
            )
        records.append(row)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        required=True,
        help="JSONL with exactly case_id and cited_article_ids in each record",
    )
    parser.add_argument("--out", type=Path, required=True, help="path for the minimal D7 JSON record")
    args = parser.parse_args(argv)
    if args.inventory.resolve() == args.out.resolve():
        parser.error("--out must not overwrite --inventory")

    result = evaluate_preannotation_gate(load_preannotation_inventory(args.inventory))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result.public_record(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sys.stdout.write(json.dumps(result.public_record(), ensure_ascii=False) + "\n")
    return 0 if result.can_proceed else 1


if __name__ == "__main__":
    raise SystemExit(main())
