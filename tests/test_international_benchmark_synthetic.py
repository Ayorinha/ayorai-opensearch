"""Synthetic-only fixtures; contains no dataset text or copied examples."""
import pytest
from ayorai_attractor.evaluation.international import DatasetError, adapt_records

MAPPING = {"schema_version":"1.0.0", "mapping_id":"llm-aggrefact-label-map-v1",
           "native_binary_labels":{"1":"SUPPORTED","0":"NOT_SUPPORTED"}}

def test_synthetic_fixture_preserves_native_binary_negative() -> None:
    fixture = [
        {"doc":"SYNTHETIC document A.", "claim":"SYNTHETIC claim A.", "label":1, "dataset":"SYNTHETIC-A"},
        {"doc":"SYNTHETIC document B.", "claim":"SYNTHETIC claim B.", "label":0, "dataset":"SYNTHETIC-B"},
    ]
    adapted = adapt_records(fixture, MAPPING)
    assert [x["label"] for x in adapted] == ["SUPPORTED", "NOT_SUPPORTED"]
    assert all("SYNTHETIC" in x["doc"] for x in adapted)

@pytest.mark.parametrize("record", [
    {"doc":"SYNTHETIC doc", "claim":"SYNTHETIC claim", "label":2, "dataset":"SYNTHETIC"},
    {"doc":"", "claim":"SYNTHETIC claim", "label":1, "dataset":"SYNTHETIC"},
    {"doc":"SYNTHETIC doc", "claim":"SYNTHETIC claim", "label":1},
])
def test_invalid_synthetic_rows_fail_not_silently_drop(record) -> None:
    with pytest.raises(DatasetError):
        adapt_records([record], MAPPING)
