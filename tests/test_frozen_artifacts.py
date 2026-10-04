import hashlib
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "evals/golden/v0.jsonl",
            "2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75",
        ),
        (
            "evals/golden/v0.1.jsonl",
            "a7076512196c1ee9670478f036f7a3996fe89a483efad140ec7b985a54846fb9",
        ),
        (
            "evals/golden/judge-smoke.jsonl",
            "4012c75a3e667b1ca0bd0714fc299626d9e4cffb89f5d0dc0b5010e4fbc98f68",
        ),
        (
            "evals/corpus/documents.jsonl",
            "ce2333ccfe4003ebfc90819400beaf6a245620754deb8572c7611bd8bbb7dea3",
        ),
        (
            "configs/f1-thresholds.json",
            "d64d233a3c31f83d09cfb59504ca8c580008fa8262dbe1d52dd6550afc6020cb",
        ),
    ],
)
def test_frozen_artifact_hash(path: str, expected: str) -> None:
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert actual == expected, f"frozen artifact changed: {path}"
