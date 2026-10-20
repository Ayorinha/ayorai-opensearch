"""Selection helpers for reproducible Golden-suite evaluation."""

from __future__ import annotations

GOLDEN_SUITES = ("golden-v0", "golden-v0.1")
SUITE_CHOICES = (*GOLDEN_SUITES, "both")


def select_golden_suites(selection: str) -> tuple[str, ...]:
    """Return the exact suites requested by the CLI.

    The "both" option preserves the historical comparative report. A
    single-suite selection must not trigger inference on the other suite.
    """
    if selection == "both":
        return GOLDEN_SUITES
    if selection in GOLDEN_SUITES:
        return (selection,)
    raise ValueError(f"unsupported Golden suite selection: {selection!r}")
