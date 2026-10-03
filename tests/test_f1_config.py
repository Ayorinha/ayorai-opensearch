import json
from pathlib import Path


def test_f1_thresholds_are_frozen_and_untuned() -> None:
    path = Path(__file__).parents[1] / "configs" / "f1-thresholds.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["seed"] == 20261003
    assert data["bootstrap_iterations"] == 10000
    assert data["nli"]["decision"] == "argmax"
    assert data["nli"]["confidence_threshold"] is None
    assert data["nli"]["tuning_allowed"] is False
