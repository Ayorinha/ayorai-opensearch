"""P3-1: historical pins with known advisories stay out of automatic workflows."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PINS = "requirements-benchmark-pilot.txt"


def _triggers(document: dict[object, object]) -> set[str]:
    events = document.get("on", document.get(True))
    if isinstance(events, str):
        return {events}
    if isinstance(events, list):
        return {str(event) for event in events}
    if isinstance(events, dict):
        return {str(event) for event in events}
    return set()


def test_historical_pins_are_installed_only_by_manual_workflows() -> None:
    users = []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        if PINS not in text:
            continue
        users.append(path.name)
        triggers = _triggers(yaml.safe_load(text))
        assert triggers == {"workflow_dispatch"}, f"{path.name} installs {PINS} on {triggers}"
    assert users, f"{PINS} is no longer used; update docs/security/HISTORICAL-PINS.md"


def test_historical_pins_are_not_in_the_product_lock() -> None:
    lock = (ROOT / "docker" / "requirements.lock").read_text(encoding="utf-8").lower()
    for package in ("transformers==", "pyarrow==", "accelerate=="):
        assert package not in lock
