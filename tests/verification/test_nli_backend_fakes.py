from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any

import pytest

from ayorai_attractor.verification.nli import TransformersNLIBackend


class FakeScalar:
    def __init__(self, value: float | int) -> None:
        self.value = value

    def item(self) -> float | int:
        return self.value


class FakeTorch:
    @staticmethod
    def inference_mode() -> Any:
        return nullcontext()

    @staticmethod
    def softmax(logits: list[float], *, dim: int) -> list[FakeScalar]:
        assert dim == -1
        assert logits == [0.1, 0.7, 0.2]
        return [FakeScalar(0.1), FakeScalar(0.7), FakeScalar(0.2)]

    @staticmethod
    def argmax(probabilities: list[FakeScalar]) -> FakeScalar:
        return FakeScalar(max(range(len(probabilities)), key=lambda index: probabilities[index].item()))


class FakeTokenizer:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, list[int]]:
        self.calls.append((args, kwargs))
        return {"input_ids": [1, 2]}


class FakeModel:
    def __init__(self, labels: dict[int, str] | None = None) -> None:
        self.config = SimpleNamespace(
            id2label=labels or {0: "entailment", 1: "neutral", 2: "contradiction"}
        )
        self.evaluated = False
        self.calls: list[dict[str, Any]] = []

    def eval(self) -> None:
        self.evaluated = True

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(logits=[[0.1, 0.7, 0.2]])


def make_backend() -> TransformersNLIBackend:
    return TransformersNLIBackend(
        "fixture-model",
        "immutable-revision",
        license_level="COMMERCIAL_DEFAULT",
    )


def test_nli_rejects_blank_model_id_and_revision() -> None:
    with pytest.raises(ValueError, match="model_id and model_revision are required"):
        TransformersNLIBackend(" ", "revision", license_level="COMMERCIAL_DEFAULT")
    with pytest.raises(ValueError, match="model_id and model_revision are required"):
        TransformersNLIBackend("model", " ", license_level="COMMERCIAL_DEFAULT")


def test_nli_classifies_with_fake_model_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel()
    imports: list[str] = []
    fake_transformers = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer),
        AutoModelForSequenceClassification=SimpleNamespace(
            from_pretrained=lambda *args, **kwargs: model
        ),
    )

    def fake_import(name: str) -> Any:
        imports.append(name)
        return {"torch": FakeTorch, "transformers": fake_transformers}[name]

    monkeypatch.setattr("ayorai_attractor.verification.nli.importlib.import_module", fake_import)
    result = make_backend().classify("afirmação", "trecho de evidência")
    assert result == {"stance": "neutral", "confidence": 0.7}
    assert model.evaluated
    assert imports == ["torch", "transformers"]
    assert tokenizer.calls[0][0] == ("trecho de evidência", "afirmação")
    assert tokenizer.calls[0][1] == {
        "return_tensors": "pt",
        "truncation": True,
    }
    assert model.calls == [{"input_ids": [1, 2]}]


def test_nli_loads_fake_model_once(monkeypatch: pytest.MonkeyPatch) -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel()
    imports: list[str] = []
    fake_transformers = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer),
        AutoModelForSequenceClassification=SimpleNamespace(
            from_pretrained=lambda *args, **kwargs: model
        ),
    )

    def fake_import(name: str) -> Any:
        imports.append(name)
        return {"torch": FakeTorch, "transformers": fake_transformers}[name]

    monkeypatch.setattr("ayorai_attractor.verification.nli.importlib.import_module", fake_import)
    item = make_backend()
    item.classify("uma", "evidência")
    item.classify("duas", "evidência")
    assert imports == ["torch", "transformers"]
    assert len(tokenizer.calls) == 2


def test_nli_missing_optional_dependency_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_import(name: str) -> Any:
        raise ImportError(name)

    monkeypatch.setattr("ayorai_attractor.verification.nli.importlib.import_module", missing_import)
    with pytest.raises(RuntimeError, match="optional 'nli' extra"):
        make_backend().classify("afirmação", "evidência")


def test_nli_rejects_model_with_invalid_label_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeModel({0: "entailment", 1: "neutral", 2: "unknown"})
    fake_transformers = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=lambda *args, **kwargs: FakeTokenizer()),
        AutoModelForSequenceClassification=SimpleNamespace(
            from_pretrained=lambda *args, **kwargs: model
        ),
    )
    monkeypatch.setattr(
        "ayorai_attractor.verification.nli.importlib.import_module",
        lambda name: FakeTorch if name == "torch" else fake_transformers,
    )
    with pytest.raises(ValueError, match="exactly entailment, contradiction and neutral"):
        make_backend().classify("claim", "evidence")


def test_nli_license_guard_rejects_eval_only_before_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ayorai_attractor.verification.nli.importlib.import_module",
        lambda name: pytest.fail(f"unexpected import: {name}"),
    )
    restricted = TransformersNLIBackend(
        "fixture-model",
        "immutable-revision",
        license_level="EVAL_ONLY",
    )
    with pytest.raises(PermissionError, match="EVAL_ONLY model rejected"):
        restricted.classify("afirmação", "evidência")
