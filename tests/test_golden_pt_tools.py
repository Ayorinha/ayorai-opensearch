from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_golden_pt.py"
validate = runpy.run_path(str(SCRIPT))["validate"]

VALID_CASE = {
    "id": "pt-001",
    "claim": "A taxa foi de 10%.",
    "source_id": "src-001",
    "source_url": "https://example.com/source",
    "source_excerpt": "A taxa foi de 10%.",
    "justification": "O trecho sustenta a afirmação.",
    "annotator": "annotator-a",
    "source_license": "CC-BY-4.0",
    "label": "SUPPORTED",
    "difficulty": ["numero"],
}


def write_jsonl(path: Path, cases: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )


def run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_validator_accepts_valid_case(tmp_path: Path) -> None:
    path = tmp_path / "valid.jsonl"
    write_jsonl(path, [VALID_CASE])
    result = run_validator(path)
    assert result.returncode == 0
    assert result.stdout == ""


def test_validator_rejects_unknown_license(tmp_path: Path) -> None:
    case = {**VALID_CASE, "source_license": "unknown"}
    path = tmp_path / "invalid-license.jsonl"
    write_jsonl(path, [case])
    result = run_validator(path)
    assert result.returncode == 1
    assert "source_license" in result.stdout


def test_validator_rejects_invalid_label(tmp_path: Path) -> None:
    case = {**VALID_CASE, "label": "INVALID"}
    path = tmp_path / "invalid-label.jsonl"
    write_jsonl(path, [case])
    result = run_validator(path)
    assert result.returncode == 1
    assert "label" in result.stdout


def test_validator_rejects_extra_field(tmp_path: Path) -> None:
    case = {**VALID_CASE, "extra": "nope"}
    path = tmp_path / "extra.jsonl"
    write_jsonl(path, [case])
    result = run_validator(path)
    assert result.returncode == 1
    assert "campo extra: extra" in result.stdout


def test_validator_rejects_duplicate_id(tmp_path: Path) -> None:
    case = {**VALID_CASE}
    second = {**VALID_CASE, "claim": "Outra afirmação."}
    path = tmp_path / "duplicate.jsonl"
    write_jsonl(path, [case, second])
    result = run_validator(path)
    assert result.returncode == 1
    assert "linha 2" in result.stdout
    assert "id repetido" in result.stdout


SPLIT_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "split_golden_pt.py"


def run_split(
    input_path: Path, output_dir: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SPLIT_SCRIPT), str(input_path), str(output_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_split_is_deterministic_and_hides_three_of_ten(tmp_path: Path) -> None:
    cases = [{**VALID_CASE, "id": f"pt-{index:03d}"} for index in range(10)]
    input_path = tmp_path / "cases.jsonl"
    write_jsonl(input_path, cases)
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_result = run_split(input_path, first)
    second_result = run_split(input_path, second)

    assert first_result.returncode == 0
    assert second_result.returncode == 0
    assert first_result.stdout.strip() == second_result.stdout.strip()
    assert (first / "hidden.jsonl").read_bytes() == (second / "hidden.jsonl").read_bytes()
    assert (first / "visible.jsonl").read_bytes() == (second / "visible.jsonl").read_bytes()
    assert len((first / "hidden.jsonl").read_text(encoding="utf-8").splitlines()) == 3
    assert len((first / "visible.jsonl").read_text(encoding="utf-8").splitlines()) == 7


def test_split_rejects_output_inside_repository(tmp_path: Path) -> None:
    input_path = tmp_path / "cases.jsonl"
    write_jsonl(input_path, [VALID_CASE])
    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "golden-pt-test-output"

    result = run_split(input_path, output_path)

    assert result.returncode == 1
    assert "dentro do repositório" in result.stderr


KAPPA_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "kappa_golden_pt.py"


def write_annotations(path: Path, labels: list[str]) -> None:
    path.write_text(
        "".join(
            json.dumps({"id": f"pt-{index + 1:03d}", "label": label}) + "\n"
            for index, label in enumerate(labels)
        ),
        encoding="utf-8",
    )


def run_kappa(
    annotator_a: Path, annotator_b: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(KAPPA_SCRIPT), str(annotator_a), str(annotator_b)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_kappa_matches_expected_value_and_single_divergence(tmp_path: Path) -> None:
    annotator_a = tmp_path / "a.jsonl"
    annotator_b = tmp_path / "b.jsonl"
    write_annotations(annotator_a, ["VERIFIED", "VERIFIED", "REFUTED", "REFUTED"])
    write_annotations(annotator_b, ["VERIFIED", "REFUTED", "REFUTED", "REFUTED"])

    result = run_kappa(annotator_a, annotator_b)

    assert result.returncode == 0
    assert "n: 4" in result.stdout
    assert "kappa: 0.500" in result.stdout
    assert "pt-002" in result.stdout
    assert "pt-001" not in result.stdout.split("divergências:", 1)[1]
    assert "pt-003" not in result.stdout.split("divergências:", 1)[1]
    assert "pt-004" not in result.stdout.split("divergências:", 1)[1]


def test_kappa_rejects_different_id_sets(tmp_path: Path) -> None:
    annotator_a = tmp_path / "a.jsonl"
    annotator_b = tmp_path / "b.jsonl"
    write_annotations(annotator_a, ["VERIFIED"])
    annotator_b.write_text(
        json.dumps({"id": "other-id", "label": "VERIFIED"}) + "\n",
        encoding="utf-8",
    )

    result = run_kappa(annotator_a, annotator_b)

    assert result.returncode == 1
    assert "conjuntos de ids são diferentes" in result.stderr



def test_validator_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    assert validate(path)


def test_validator_rejects_list_label_without_exception(tmp_path: Path) -> None:
    path = tmp_path / "list-label.jsonl"
    write_jsonl(path, [{**VALID_CASE, "label": ["VERIFIED"]}])
    from scripts.check_golden_pt import validate
    assert validate(path)


def test_validator_rejects_non_text_difficulty_without_exception(tmp_path: Path) -> None:
    path = tmp_path / "object-difficulty.jsonl"
    write_jsonl(path, [{**VALID_CASE, "difficulty": [{}]}])
    from scripts.check_golden_pt import validate
    assert validate(path)
