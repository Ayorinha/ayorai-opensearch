"""AYORAI-PT-NLI inference integration (ADR-008): fail-closed loading, no remote code.

transformers and torch are replaced by in-memory fakes: nothing is downloaded,
installed or trained by these tests.
"""

from __future__ import annotations

import math
import re
import sys
import types
from typing import Any

import pytest

from ayorai_attractor.verification.document_check import (
    CheckDocumentInput,
    ConservativeStanceDetector,
    check_documents,
)
from ayorai_attractor.verification.pt_nli import (
    BASE_MODEL_ID,
    BASE_MODEL_REVISION,
    COMMERCIAL_AUDITED_LEVEL,
    MAX_SEQUENCE_TOKENS,
    UNAUDITED_LEVEL,
    EuroBertNLIBackend,
    PtNliCheckpoint,
    build_pt_nli_detector,
)

REVISION = "a" * 40
NLI_LABELS = {0: "entailment", 1: "neutral", 2: "contradiction"}


class _Scalar:
    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> float:
        return self.value


class _Vector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def __getitem__(self, index: int) -> Any:
        return _Scalar(self.values[index])


class _FakeTorch(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("torch")

    class inference_mode:  # noqa: N801 - mirrors torch.inference_mode
        def __enter__(self) -> None:
            return None

        def __exit__(self, *args: object) -> None:
            return None

    @staticmethod
    def softmax(logits: _Vector, dim: int) -> _Vector:
        exps = [math.exp(value) for value in logits.values]
        return _Vector([value / sum(exps) for value in exps])

    @staticmethod
    def argmax(probabilities: _Vector) -> _Scalar:
        values = probabilities.values
        return _Scalar(values.index(max(values)))


def _fake_transformers(
    *, version: str = "5.24.0", model_type: str = "eurobert", labels: dict[int, str] | None = None
) -> tuple[types.ModuleType, dict[str, Any]]:
    calls: dict[str, Any] = {"config": [], "tokenizer": [], "model": [], "encode": []}
    module = types.ModuleType("transformers")
    module.__version__ = version  # type: ignore[attr-defined]
    id2label = NLI_LABELS if labels is None else labels

    class AutoConfig:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs: Any) -> Any:
            calls["config"].append((model_id, kwargs))
            return types.SimpleNamespace(model_type=model_type, id2label=id2label)

    class _Tokenizer:
        def __call__(self, first: str, second: str, **kwargs: Any) -> dict[str, Any]:
            calls["encode"].append((first, second, kwargs))
            return {"pair": (first, second)}

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs: Any) -> Any:
            calls["tokenizer"].append((model_id, kwargs))
            return _Tokenizer()

    class _Model:
        def eval(self) -> None:
            return None

        def __call__(self, **encoded: Any) -> Any:
            evidence, claim = encoded["pair"]
            # Entailment when the claim's percentage is in the evidence, contradiction
            # when the evidence states another percentage, neutral otherwise.
            claimed = re.findall(r"\d+%", claim)
            stated = re.findall(r"\d+%", evidence)
            if claimed and set(claimed) <= set(stated):
                logits = [4.0, 0.0, 0.0]
            elif claimed and stated:
                logits = [0.0, 0.0, 4.0]
            else:
                logits = [0.0, 4.0, 0.0]
            return types.SimpleNamespace(logits=[_Vector(logits)])

    class AutoModelForSequenceClassification:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs: Any) -> Any:
            calls["model"].append((model_id, kwargs))
            return _Model()

    module.AutoConfig = AutoConfig  # type: ignore[attr-defined]
    module.AutoTokenizer = AutoTokenizer  # type: ignore[attr-defined]
    module.AutoModelForSequenceClassification = AutoModelForSequenceClassification  # type: ignore[attr-defined]
    return module, calls


@pytest.fixture
def fake_stack(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    transformers, calls = _fake_transformers()
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    return calls


def _checkpoint(level: str = COMMERCIAL_AUDITED_LEVEL) -> PtNliCheckpoint:
    return PtNliCheckpoint("ayorai/pt-nli-test", REVISION, level)


def test_base_model_reference_is_pinned_to_a_commit() -> None:
    assert BASE_MODEL_ID == "EuroBERT/EuroBERT-210m"
    assert len(BASE_MODEL_REVISION) == 40


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model_id": " ", "revision": REVISION, "license_level": UNAUDITED_LEVEL}, "model_id"),
        ({"model_id": "m", "revision": "main", "license_level": UNAUDITED_LEVEL}, "commit SHA"),
        ({"model_id": "m", "revision": REVISION, "license_level": "MIT"}, "license_level"),
        (
            {
                "model_id": "m",
                "revision": REVISION,
                "license_level": UNAUDITED_LEVEL,
                "base_model_revision": "v1",
            },
            "commit SHA",
        ),
    ],
)
def test_checkpoint_reference_is_validated(kwargs: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PtNliCheckpoint(**kwargs)


def test_unaudited_weights_are_refused_before_any_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "transformers", raising=False)
    backend = EuroBertNLIBackend(_checkpoint(UNAUDITED_LEVEL))
    with pytest.raises(PermissionError, match="EVAL_ONLY"):
        backend.classify("claim", "evidence")


def test_unaudited_weights_load_in_evaluation_mode(fake_stack: dict[str, Any]) -> None:
    backend = EuroBertNLIBackend(_checkpoint(UNAUDITED_LEVEL), evaluation_mode=True)
    assert backend.classify("A taxa foi de 12%.", "A taxa foi de 12%.")["stance"] == "supports"
    assert "ckpt_license=UNAUDITED" in backend.provenance_version
    assert "remote_code=false" in backend.provenance_version


def test_remote_code_is_never_enabled(fake_stack: dict[str, Any]) -> None:
    EuroBertNLIBackend(_checkpoint()).classify("claim", "evidence")
    for kind in ("config", "tokenizer", "model"):
        assert fake_stack[kind], kind
        for model_id, kwargs in fake_stack[kind]:
            assert model_id == "ayorai/pt-nli-test"
            assert kwargs["revision"] == REVISION
            assert kwargs["trust_remote_code"] is False


def test_transformers_without_native_eurobert_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transformers, calls = _fake_transformers(version="4.57.6")
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    with pytest.raises(RuntimeError, match="transformers>=5.3.0"):
        EuroBertNLIBackend(_checkpoint()).classify("claim", "evidence")
    assert calls["config"] == []


def test_non_eurobert_checkpoint_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    transformers, calls = _fake_transformers(model_type="deberta-v2")
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    with pytest.raises(ValueError, match="model_type 'eurobert'"):
        EuroBertNLIBackend(_checkpoint()).classify("claim", "evidence")
    assert calls["model"] == []


def test_base_model_without_nli_head_is_refused_before_loading_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The public base model has generic labels: it cannot classify stance.
    transformers, calls = _fake_transformers(labels={0: "LABEL_0", 1: "LABEL_1"})
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    with pytest.raises(ValueError, match="no trained NLI head"):
        EuroBertNLIBackend(_checkpoint()).classify("claim", "evidence")
    assert calls["tokenizer"] == [] and calls["model"] == []


def test_only_the_evidence_is_truncated_and_the_claim_is_read_in_full(
    fake_stack: dict[str, Any],
) -> None:
    EuroBertNLIBackend(_checkpoint()).classify("a afirmação", "o trecho")
    first, second, kwargs = fake_stack["encode"][0]
    assert (first, second) == ("o trecho", "a afirmação")
    assert kwargs["truncation"] == "only_first"
    assert kwargs["max_length"] == MAX_SEQUENCE_TOKENS


def test_detector_feeds_the_deterministic_judge_through_check_documents(
    fake_stack: dict[str, Any],
) -> None:
    detector = build_pt_nli_detector(_checkpoint())
    assert isinstance(detector, ConservativeStanceDetector)
    documents = [
        CheckDocumentInput(
            id="relatorio",
            text="A inadimplência da carteira foi de 12% em 2025.",
            url="https://example.test/relatorio",
        )
    ]
    supported = check_documents(
        documents,
        claims=["A inadimplência da carteira foi de 12% em 2025."],
        stance_detector=detector,
    )
    refuted = check_documents(
        documents,
        claims=["A inadimplência da carteira foi de 9% em 2025."],
        stance_detector=detector,
    )
    supported_result = supported.results[0]
    refuted_result = refuted.results[0]
    # One source: ADR-002 caps support at partially_supported.
    assert supported_result.verdict == "partially_supported"
    assert refuted_result.verdict == "refuted"
    assert "inner=stance_detector.nli/" in supported.engine["stance_detector"]


def test_conservative_wrapper_still_demands_lexical_support(fake_stack: dict[str, Any]) -> None:
    # The fake model says "supports" whenever the passage has "12%"; the wrapper
    # downgrades it because the claim's content words are not in the passage.
    detector = build_pt_nli_detector(_checkpoint())
    result = check_documents(
        [
            CheckDocumentInput(
                id="d", text="Outro assunto: 12% de algo diferente.", url="https://e.test/d"
            )
        ],
        claims=["A inadimplência da carteira foi de 12% em 2025."],
        stance_detector=detector,
    )
    assert result.results[0].verdict != "supported"
