"""Synthetic tests for the RGC pre-annotation resolution gate (DEC-027 D7)."""

from __future__ import annotations

import json
import runpy
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE: dict[str, Any] = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_gate.py"))


def _cases(component_count: int) -> list[dict[str, object]]:
    return [
        {"case_id": f"case-{index:02d}", "cited_article_ids": [f"article-{index:02d}"]}
        for index in range(component_count)
    ]


def test_gate_fails_below_six_components() -> None:
    result = MODULE["evaluate_preannotation_gate"](_cases(5))

    assert result.component_count == 5
    assert result.component_sizes == (1, 1, 1, 1, 1)
    assert result.largest_component_size == 1
    assert result.can_proceed is False


def test_gate_passes_at_exactly_six_components() -> None:
    result = MODULE["evaluate_preannotation_gate"](_cases(6))

    assert result.component_count == 6
    assert result.component_sizes == (1, 1, 1, 1, 1, 1)
    assert result.largest_component_size == 1
    assert result.can_proceed is True


def test_gate_reports_only_the_d7_public_fields() -> None:
    result = MODULE["evaluate_preannotation_gate"](
        [
            {"case_id": "a", "cited_article_ids": ["article-a"]},
            {"case_id": "b", "cited_article_ids": ["article-a", "article-b"]},
            {"case_id": "c", "cited_article_ids": ["article-c"]},
            {"case_id": "d", "cited_article_ids": ["article-d"]},
            {"case_id": "e", "cited_article_ids": ["article-e"]},
            {"case_id": "f", "cited_article_ids": ["article-f"]},
            {"case_id": "g", "cited_article_ids": ["article-g"]},
        ]
    )

    assert result.component_count == 6
    assert result.component_sizes == (2, 1, 1, 1, 1, 1)
    assert result.largest_component_size == 2
    assert result.public_record() == {
        "K": 6,
        "component_sizes": [2, 1, 1, 1, 1, 1],
        "largest_component_size": 2,
    }


def test_gate_is_independent_of_input_order() -> None:
    cases = _cases(8)

    forward = MODULE["evaluate_preannotation_gate"](cases)
    reverse = MODULE["evaluate_preannotation_gate"](reversed(cases))

    assert forward == reverse


def test_gate_does_not_read_labels_predictions_results_or_legacy_clusters() -> None:
    class InventoryOnlyCase(Mapping[str, object]):
        def __init__(self, case_id: str, article_id: str) -> None:
            self._data = {
                "case_id": case_id,
                "cited_article_ids": [article_id],
                "labels": object(),
                "predictions": object(),
                "results": object(),
                "bootstrap_cluster_id": object(),
            }

        def __getitem__(self, key: str) -> object:
            if key not in {"case_id", "cited_article_ids"}:
                raise AssertionError(f"forbidden field was read: {key}")
            return self._data[key]

        def __iter__(self) -> Iterator[str]:
            return iter(self._data)

        def __len__(self) -> int:
            return len(self._data)

    result = MODULE["evaluate_preannotation_gate"](
        InventoryOnlyCase(f"case-{index}", f"article-{index}") for index in range(6)
    )

    assert result.can_proceed is True
    assert result.component_count == 6


@pytest.mark.parametrize(
    "cases",
    [
        [{"case_id": "a", "cited_article_ids": []}],
        [{"case_id": "a", "cited_article_ids": ["article-a", "article-a"]}],
        [{"case_id": "a", "cited_article_ids": ["article+a"]}],
        [
            {"case_id": "a", "cited_article_ids": ["article-a"]},
            {"case_id": "a", "cited_article_ids": ["article-b"]},
        ],
        [{"case_id": "a", "cited_article_ids": [" article-a"]}],
    ],
)
def test_incomplete_or_noncanonical_inventory_fails_closed(
    cases: list[dict[str, object]],
) -> None:
    with pytest.raises(ValueError):
        MODULE["evaluate_preannotation_gate"](cases)


def test_empty_inventory_is_invalid_not_k_zero() -> None:
    with pytest.raises(ValueError, match="empty inventory"):
        MODULE["evaluate_preannotation_gate"]([])


def test_inventory_loader_accepts_only_the_two_d7_fields(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.jsonl"
    inventory.write_text(
        json.dumps({"case_id": "a", "cited_article_ids": ["article-a"]}) + "\n",
        encoding="utf-8",
    )

    records = MODULE["load_preannotation_inventory"](inventory)

    assert records == [{"case_id": "a", "cited_article_ids": ["article-a"]}]


def test_inventory_loader_rejects_annotation_or_result_fields(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.jsonl"
    inventory.write_text(
        json.dumps(
            {
                "case_id": "a",
                "cited_article_ids": ["article-a"],
                "label": "SUPPORTED",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected exactly"):
        MODULE["load_preannotation_inventory"](inventory)


def test_inventory_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.jsonl"
    inventory.write_text(
        '{"case_id":"a","case_id":"b","cited_article_ids":["article-a"]}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON key"):
        MODULE["load_preannotation_inventory"](inventory)


def test_gate_cli_refuses_to_overwrite_inventory(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.jsonl"
    original = json.dumps({"case_id": "a", "cited_article_ids": ["article-a"]}) + "\n"
    inventory.write_text(original, encoding="utf-8")

    with pytest.raises(SystemExit, match="2"):
        MODULE["main"](["--inventory", str(inventory), "--out", str(inventory)])

    assert inventory.read_text(encoding="utf-8") == original


def test_gate_cli_writes_minimal_record_and_returns_success_at_k_six(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory = tmp_path / "inventory.jsonl"
    output = tmp_path / "gate.json"
    inventory.write_text(
        "".join(
            json.dumps({"case_id": f"case-{index}", "cited_article_ids": [f"article-{index}"]})
            + "\n"
            for index in range(6)
        ),
        encoding="utf-8",
    )

    exit_code = MODULE["main"](["--inventory", str(inventory), "--out", str(output)])

    expected = {"K": 6, "component_sizes": [1, 1, 1, 1, 1, 1], "largest_component_size": 1}
    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8")) == expected
    assert json.loads(capsys.readouterr().out) == expected


def test_gate_cli_writes_blocked_record_and_returns_nonzero_below_k_six(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory = tmp_path / "inventory.jsonl"
    output = tmp_path / "gate.json"
    inventory.write_text(
        "".join(
            json.dumps({"case_id": f"case-{index}", "cited_article_ids": [f"article-{index}"]})
            + "\n"
            for index in range(5)
        ),
        encoding="utf-8",
    )

    exit_code = MODULE["main"](["--inventory", str(inventory), "--out", str(output)])

    expected = {"K": 5, "component_sizes": [1, 1, 1, 1, 1], "largest_component_size": 1}
    assert exit_code == 3
    assert json.loads(output.read_text(encoding="utf-8")) == expected
    assert json.loads(capsys.readouterr().out) == expected


@pytest.mark.parametrize(
    "content",
    [
        "",
        "\n",
        "{not json}\n",
        '{"case_id": "c1", "cited_article_ids": ["Article-A"]}\n',
        '{"case_id": "c1", "cited_article_ids": ["article-a"], "label": "SUPPORTED"}\n',
    ],
)
def test_gate_cli_invalid_inventory_exits_2_and_writes_nothing(
    tmp_path: Path, content: str, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory = tmp_path / "inventory.jsonl"
    output = tmp_path / "gate.json"
    inventory.write_text(content, encoding="utf-8")

    exit_code = MODULE["main"](["--inventory", str(inventory), "--out", str(output)])

    assert exit_code == 2
    assert not output.exists()
    assert "invalid D7 inventory" in capsys.readouterr().err


def test_gate_cli_missing_inventory_exits_2(tmp_path: Path) -> None:
    output = tmp_path / "gate.json"
    exit_code = MODULE["main"](
        ["--inventory", str(tmp_path / "absent.jsonl"), "--out", str(output)]
    )
    assert exit_code == 2
    assert not output.exists()


@pytest.mark.parametrize(("count", "expected_code"), [(6, 0), (5, 3)])
def test_gate_runs_as_a_script_from_any_directory(
    tmp_path: Path, count: int, expected_code: int
) -> None:
    import subprocess
    import sys

    inventory = tmp_path / "inventory.jsonl"
    output = tmp_path / "gate.json"
    inventory.write_text(
        "".join(
            json.dumps({"case_id": f"case-{index}", "cited_article_ids": [f"article-{index}"]})
            + "\n"
            for index in range(count)
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "evals" / "ptbr" / "rgc_gate.py"),
            "--inventory",
            str(inventory),
            "--out",
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == expected_code, completed.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["K"] == count
