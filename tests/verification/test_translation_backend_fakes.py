from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from ayorai_attractor.verification.translation import MarianTranslationBackend


class FakeTokenizer:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, list[int]]:
        self.calls.append((args, kwargs))
        return {"input_ids": [1, 2, 3]}

    def decode(self, generated: list[int], *, skip_special_tokens: bool) -> str:
        assert skip_special_tokens is True
        return "texto traduzido"


class FakeModel:
    def __init__(self) -> None:
        self.evaluated = False
        self.generated_with: list[dict[str, Any]] = []

    def eval(self) -> None:
        self.evaluated = True

    def generate(self, **kwargs: Any) -> list[list[int]]:
        self.generated_with.append(kwargs)
        return [[4, 5, 6]]


def backend() -> MarianTranslationBackend:
    return MarianTranslationBackend(
        "fixture-model",
        "immutable-revision",
        license_level="COMMERCIAL_DEFAULT",
    )


def test_translation_rejects_blank_model_id_and_revision() -> None:
    with pytest.raises(ValueError, match="model_id and model_revision are required"):
        MarianTranslationBackend("  ", "revision", license_level="COMMERCIAL_DEFAULT")
    with pytest.raises(ValueError, match="model_id and model_revision are required"):
        MarianTranslationBackend("model", "  ", license_level="COMMERCIAL_DEFAULT")


def test_translation_loads_fake_model_and_translates_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel()
    tokenizer_loader_calls: list[dict[str, Any]] = []
    model_loader_calls: list[dict[str, Any]] = []

    def load_tokenizer(*args: Any, **kwargs: Any) -> FakeTokenizer:
        tokenizer_loader_calls.append({"args": args, **kwargs})
        return tokenizer

    def load_model(*args: Any, **kwargs: Any) -> FakeModel:
        model_loader_calls.append({"args": args, **kwargs})
        return model

    fake_transformers = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=load_tokenizer),
        AutoModelForSeq2SeqLM=SimpleNamespace(from_pretrained=load_model),
    )
    monkeypatch.setattr(
        "ayorai_attractor.verification.translation.importlib.import_module",
        lambda name: fake_transformers if name == "transformers" else pytest.fail(name),
    )

    item = backend()
    assert item.translate("texto original") == "texto traduzido"
    assert model.evaluated
    assert tokenizer_loader_calls == [
        {"args": ("fixture-model",), "revision": "immutable-revision", "use_fast": False}
    ]
    assert model_loader_calls == [{"args": ("fixture-model",), "revision": "immutable-revision"}]
    assert tokenizer.calls[0][0] == ("texto original",)
    assert tokenizer.calls[0][1] == {"return_tensors": "pt", "truncation": True}
    assert model.generated_with == [{"input_ids": [1, 2, 3]}]


def test_translation_model_is_loaded_only_once(monkeypatch: pytest.MonkeyPatch) -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel()
    imports: list[str] = []
    fake_transformers = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer),
        AutoModelForSeq2SeqLM=SimpleNamespace(from_pretrained=lambda *args, **kwargs: model),
    )

    def fake_import(name: str) -> Any:
        imports.append(name)
        return fake_transformers

    monkeypatch.setattr(
        "ayorai_attractor.verification.translation.importlib.import_module", fake_import
    )
    item = backend()
    assert item.translate("um") == "texto traduzido"
    assert item.translate("dois") == "texto traduzido"
    assert imports == ["transformers"]


def test_translation_missing_optional_dependency_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_import(name: str) -> Any:
        raise ImportError(name)

    monkeypatch.setattr(
        "ayorai_attractor.verification.translation.importlib.import_module", missing_import
    )
    with pytest.raises(RuntimeError, match="optional 'nli' extra"):
        backend().translate("texto")


def test_translation_provenance_hash_is_stable_and_content_sensitive() -> None:
    item = backend()
    first = item.provenance_hash("original", "traduzido")
    assert len(first) == 64
    assert first == item.provenance_hash("original", "traduzido")
    assert first != item.provenance_hash("original diferente", "traduzido")
    assert first != item.provenance_hash("original", "outra tradução")


def test_translation_license_guard_runs_before_model_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_import(name: str) -> Any:
        pytest.fail(f"unexpected model import: {name}")

    monkeypatch.setattr(
        "ayorai_attractor.verification.translation.importlib.import_module", forbidden_import
    )
    restricted = MarianTranslationBackend(
        "fixture-model",
        "immutable-revision",
        license_level="EVAL_ONLY",
    )
    with pytest.raises(PermissionError, match="EVAL_ONLY model rejected"):
        restricted.translate("não deve carregar")
