import json
from pathlib import Path

from ayorai_attractor.api.app import app


def test_openapi_snapshot_matches_generated_contract() -> None:
    snapshot_path = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi.json"
    expected = snapshot_path.read_text(encoding="utf-8")
    actual = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert actual == expected
